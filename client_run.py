"""Connects to the server & awaits/processes commands"""

from time import sleep
import servercom
from beacon_client import BeaconClient

with open('cert.pem', 'r') as fp:
    server_cert=fp.read()

servercom.CUBESERVER_DEFAULT_CONFIG.API_HOST = 'localhost'
servercom.CUBESERVER_DEFAULT_CONFIG.API_PORT = 8889

c = servercom.Connection(server_cert=server_cert, _force=True)
bc = None
while bc is None:
    try:
        bc = BeaconClient(c)
    except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError):
        sleep(1)
        continue

print("Connected!")

@bc.commandhook
def tx_message(dest, intensity, message) -> int:
    print("Dest:", dest)
    print("Intensity:", intensity)
    print("Message:", message)
    return len(message)

bc.run_client_listener()
