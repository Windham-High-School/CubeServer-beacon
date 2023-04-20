"""Handles the encrypted socket connection between CubeServer and the beacon"""

from errno import EAGAIN
from time import sleep

from microcontroller import watchdog as w

import servercom

BEACONCOM_VERSION = b'\x01'

ACK = b'\x06'
NAK = b'\x15'
NUL = b'\x00'


# Partially stolen from kwarunek's solution here: https://stackoverflow.com/questions/34252273/what-is-the-difference-between-socket-send-and-socket-sendall
def _sendall(sock, data):
    ret = sock.send(data)
    if ret > 0:
        w.feed()
        return _sendall(sock, data[ret:])
    else:
        return None

class BeaconClient:
    """Handles the client-side of the connection to the server"""
    
    def __init__(
        self,
        connection: servercom.Connection,
        certpath="beacon.pem", keypath="beacon.key",
        verbose=False
    ):
        self.v = verbose
        self.connection = connection
        self.connection.context.load_cert_chain(certfile=certpath, keyfile=keypath)
        self.connection.connect_socket()
        self.exe = None

    def commandhook(self, func):
        """Decorator for t method to process commands

        Method signature should look like so:
        @client.commandhook
        myfunc(dest, intensity, message) -> int
        (returns number bytes successfully transmitted)
        """
        if self.exe is not None:
            raise ValueError("You cannot register multiple command hooks!")
        self.exe = func

    def run_client_listener(self):
        """Never returns; executes commands received

        Format of commands:
        <Version Byte> <Destination Byte> <Intensity Byte> <Message Length MSB> <Message Length LSB> <8 Reserved Bytes> <Message Bytes> <NULL>
        """
        if self.exe is None:
            raise ValueError("Please specify a command hook with the @this.commandhook decorator")
        if self.v:
            print("Connecting socket")
        while True:
            try:
                if self.v:
                    print("Receiving header")
                header_bytes = self.rx_bytes(13)
                if header_bytes is None:
                    continue
                if header_bytes == b'Keep-Alive\x00\x00\x00':
                    self.tx_bytes(ACK)
                    continue
                # Check version byte:
                if header_bytes[0] != BEACONCOM_VERSION[0]:
                    print("Possible BEACONCOM version incompatibility. Please update.")
                # Get message length:       (+1 is to account for NULL terminator)
                msg_len = int.from_bytes(header_bytes[3:5], 'big') + 1
                if self.v:
                    print(f"Receiving message (length {msg_len})...")
                # Get message:
                msg = self.rx_bytes(msg_len)
                if msg[-1] != NUL[0] or len(msg) < msg_len:  # Weird problem; restart the socket:
                    if self.v:
                        print("Sending NAK")
                    # Send NAK:
                    self.tx_bytes(NAK)
                    #self.reconnect()
                    continue
                if self.v:
                    print("Sending ACK")
                # Send ACK:
                self.tx_bytes(ACK)
                # Trasnmit message:
                if self.v:
                    print("Running command hook")
                bytes_txd = self.exe(header_bytes[1], header_bytes[2], msg[:-1])
                # Check stuff out:
                if not bytes_txd:
                    self.tx_bytes(NAK)
                    #self.reconnect()
                    continue
                if self.v:
                    print("Sending OK to server")
                # Send okay to server:
                self.tx_bytes(int(bytes_txd % 255).to_bytes(1, 'big') + NUL)
            except BrokenPipeError:
                sleep(1)
                self.reconnect()
#            except ConnectionRefusedError:
#                sleep(5)
#                self.reconnect()

    def close(self):
        self.connection.close_socket()

    def reconnect(self):
        self.connection.close_socket()
        self.connection.connect_socket()

    def tx_bytes(self, stuff: bytes) -> int:
        """Sends some stuff to the beacon and returns an int return code"""
        if self.connection.wrapped_socket is None:
            return ConnectionError("Connection from the beacon not established")
        if self.v:
            print(f"Writing {stuff}")
        # sent = 0
        # while sent < len(stuff):
        #     sent += self.connection.wrapped_socket.send(stuff[sent:])
        #     if self.v:
        #         print(f"Sent {sent}/{len(stuff)} bytes")
        #self.sock.flush()
        w.feed()
        _sendall(self.connection.wrapped_socket, stuff)

    def rx_bytes(self, size: int, chunkby: int = 256) -> bytes:
        """Receives a given number of bytes from the beacon"""
        if self.v:
            print(f"Blocking read for {size} bytes...")
        if self.connection.wrapped_socket is None:
            return ConnectionError("Connection from the beacon not established")
        self.connection.wrapped_socket.setblocking(True)
        response = b""
        while True:
            buf = bytearray(min(size-len(response), chunkby))
            w.feed()
            try:
                recvd = self.connection.wrapped_socket.recv_into(buf, min(size-len(response), chunkby))
            except OSError as e:
                if e.errno == EAGAIN:
                    recvd = -1
                else:
                    raise
            response += buf
            del buf
            if self.v:
                print(f"Received {recvd} bytes")
            if recvd == 0:
                del recvd
                break
        if self.v:
            print(f"Received: {response}")
        return response
