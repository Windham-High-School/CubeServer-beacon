"""A test program that simply prints beacon packets
"""

from time import sleep
import servercom
from beacon_client import BeaconClient

with open('cert.pem', 'r') as fp:
    server_cert=fp.read()

servercom.CUBESERVER_DEFAULT_CONFIG.API_HOST = '192.168.252.1'
servercom.CUBESERVER_DEFAULT_CONFIG.API_PORT = 8889

c = servercom.Connection(server_cert=server_cert, _force=True, verbose=True)
bc = None
while bc is None:
    try:
        bc = BeaconClient(c)
    except:
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
