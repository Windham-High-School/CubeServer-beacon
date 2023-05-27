# Beacon Software
# Made in collaboration with Mr. Douglas Chin

import board
import adafruit_irremote
import pulseio
import digitalio
import time
import servercom
import json
from ucontextlib import contextmanager
import traceback


CHECK_INTERVAL = 15
    
class MessageStatus:
    SCHEDULED    = "Scheduled"
    TRANSMITTED  = "Transmitted"
    TRANSMITTING = "Transmitting..."
    FAILED       = "Failed"


class Destination:
    INFRARED = "Infrared"
    VISIBLE = "Visible"


class Connection(servercom.Connection):
    def get_next_message(self):
        resp = self.request('GET', '/beacon/message/next_queued',
            headers=['User-Agent: CircuitPythonDude']
        )
        # {
        #     "id": <hex string representing the object id>,
        #     "timestamp": <epoch timestamp as a decimal>,
        #     "offset": <seconds from request until instant>,
        #     "destination": <"Infrared"|"Visible">,
        #     "intensity": <8-bit integer>,
        #     "message": <the message as a UTF-8 str>
        # }
        return json.loads(resp[1])
        

    def update_message_status(self, object_id:str, status:str):
        return self.request(
            'PUT',
            f'/beacon/message/{object_id}',
            json.dumps({"status": status}),
            content_type = 'application/json',
            headers=['User-Agent: CircuitPythonDude']
        ).code == 201


@contextmanager
def connection():
	c = Connection()
	try:
		yield c
	finally:
		c.close()


def handle_error(error):
    try:
        message = "".join(traceback.format_exception(error))
        print(message)

        with connection() as c:
            c.post(servercom.Text(message))
    except Exception as e:
        print('[Error] Exception', error, e)


def set_intensity(intensity: int):
    i2c = board.I2C()
    i2c.try_lock()
    i2c.writeto(0x28, chr(intensity).encode())
    i2c.unlock()


def tx_packet(status_callback, encoder, packet: bytes, output):
    if len(packet) < 1:
        return
    print(packet)
    status_callback(MessageStatus.TRANSMITTING)
    time.sleep(0.15)
    encoder.transmit(output, [byte for byte in packet])
    time.sleep(0.15)


def tx_chunk(status_callback, encoder, message: bytes, output):
    i = 0
    chunk_size = 6
    while i <= len(message):
        chunk = message[i : ((i + chunk_size) if len(message) - i > chunk_size else len(message))]
        if len(chunk) == 0:
            break
        print(chunk)
        time.sleep(0.15)
        encoder.transmit(output, chunk)
        time.sleep(0.15)
        status_callback(MessageStatus.TRANSMITTING)
        i += chunk_size


def tx_message(status_callback, encoder, output, intensity: int, message: bytes):
    set_intensity(intensity)
    #while message[0] == b'\x07':
    #    tx_packet(status_callback, b'\x07', output=output)
    #    message = message[1:]
    for _ in range(4):
        tx_packet(status_callback, encoder, b'\x07', output=output)
    tx_packet(status_callback, encoder, len(message).to_bytes(2, 'big'), output=output)
    for line in message.split(b'\r\n'):
        tx_chunk(status_callback, encoder, line + b'\r\n', output=output)


def main():
    frequency = 32768

    print("Initializing hardware...")

    highPower = digitalio.DigitalInOut(board.D10)
    highPower.direction = digitalio.Direction.OUTPUT
    highPower.value = True

    # Init PulseIO:
    pulse_ir = pulseio.PulseOut(board.D5, frequency=frequency, duty_cycle=2 ** 15)
    pulse_red = pulseio.PulseOut(board.D6, frequency=frequency, duty_cycle=2 ** 15)
    encoder = adafruit_irremote.GenericTransmit(header=[3000, 3800], one=[550, 550], zero=[550, 1700], trail=3800)

    # Init I2C:
    i2c = board.I2C()

    #set the potentiometer to volitile and simple log attenuation
    i2c.try_lock()
    i2c.writeto(0x28, bytes([0x84, 0x30]))
    i2c.unlock()
    
    set_intensity(0x00)
    
    with connection() as c:
        while True:
            next_message = c.get_next_message()
            if next_message and 'id' in next_message:
                object_id = next_message['id']
                offset = next_message['offset']
                destination = next_message['destination']
                intensity = next_message['intensity']
                message = next_message['message']
                
                if offset < 2*CHECK_INTERVAL:
                    try:
                        c.update_message_status(object_id, MessageStatus.SCHEDULED)
                        if offset > 0:
                            time.sleep(offset)
                        
                        output = pulse_red if destination == Destination.VISIBLE else pulse_ir
                        tx_message(lambda msg, obj_id=object_id: c.update_message_status(obj_id, msg), encoder, output, intensity, message.encode())
                        c.update_message_status(object_id, MessageStatus.TRANSMITTED)
                    except Exception as e:
                        c.update_message_status(object_id, MessageStatus.FAILED)
                        raise
                        
            time.sleep(CHECK_INTERVAL)
                
while True:
    try:
        main()
    except Exception as e:
        handle_error(e)
        time.sleep(15)

