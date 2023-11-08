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
import supervisor


CHECK_INTERVAL = 15
DEMO_MODE = False
DEMO_DESTINATION = 'Infrared'
DEMO_INTENSITY = 10

class MessageStatus:
    SCHEDULED    = "Scheduled"
    TRANSMITTED  = "Transmitted"
    TRANSMITTING = "Transmitting..."
    FAILED       = "Failed"
    MISSED       = "Missed"


class Destination:
    INFRARED = "Infrared"
    VISIBLE = "Visible"

class Connection(servercom.Connection):
    def get_next_message(self):
        try:
            resp = self.request('GET', '/beacon/message/next_queued',
                headers=['User-Agent: CircuitPythonDude']
            )
        except ConnectionError as e:
            return None

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
	c = Connection(verbose=False)
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


def set_intensity(intensity: int, reg: Destination):
    i2c = board.I2C()
    i2c.try_lock()
    val = (intensity | 0b1000000) if reg == Destination.VISIBLE else (intensity & 0b0111111)
    i2c.writeto(0x28, chr(val).encode())
    i2c.unlock()


def tx_packet(encoder, packet: bytes, output):
    if len(packet) < 1:
        return
    print(packet)
    time.sleep(0.15)
    encoder.transmit(output, [byte for byte in packet])
    time.sleep(0.15)


def tx_chunk(encoder, message: bytes, output):
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
        i += chunk_size


def tx_message(status_callback, encoder, destination, output, intensity: int, message: bytes):
    set_intensity(intensity, destination)
    #while message[0] == b'\x07':
    #    tx_packet(b'\x07', output=output)
    #    message = message[1:]
    status_callback(MessageStatus.TRANSMITTING)
    for _ in range(4):
        tx_packet(encoder, b'\x07', output=output)
    tx_packet(encoder, len(message).to_bytes(2, 'big'), output=output)
    messages = message.split(b'\r\n')
    for i, line in enumerate(messages):
        if i != len(messages)-1:
            line += b'\r\n'
        tx_chunk(encoder, line, output=output)


def setup():
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

    set_intensity(0x00, Destination.INFRARED)
    set_intensity(0x00, Destination.VISIBLE)

    return encoder, pulse_ir, pulse_red

def main(encoder, pulse_ir, pulse_red):
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
                        # TODO: need to account for time of update_message_status
                        if offset > 0:
                            time.sleep(offset)

                        output = pulse_red if destination == Destination.VISIBLE else pulse_ir
                        tx_message(lambda msg, obj_id=object_id: c.update_message_status(obj_id, msg), encoder, destination, output, intensity, message.encode())
                        c.update_message_status(object_id, MessageStatus.TRANSMITTED)
                    except Exception as e:
                        c.update_message_status(object_id, MessageStatus.FAILED)
                        raise
                else:
                    c.update_message_status(object_id, MessageStatus.MISSED)

            time.sleep(CHECK_INTERVAL)

def demo(encoder, pulse_ir, pulse_red):
    message = 'CSMSG/1.1\r\nDivision: Nanometer\r\nServer: CubeServer/1.7.2-dev\r\nContent-Length: 13\r\nChecksum: 182\r\n\r\nTest Message.'
    while True:
        output = pulse_red if DEMO_DESTINATION == Destination.VISIBLE else pulse_ir
        tx_message(lambda msg: print(msg), encoder, DEMO_DESTINATION, output, DEMO_INTENSITY, message.encode())
        time.sleep(5)

try:
    (encoder, pulse_ir, pulse_red) = setup()
    if DEMO_MODE:
        demo(encoder, pulse_ir, pulse_red)
    else:
        main(encoder, pulse_ir, pulse_red)
except Exception as e:
    handle_error(e)
    time.sleep(15)
    supervisor.reload()

