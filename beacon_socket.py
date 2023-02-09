"""Handles the encrypted socket connection between CubeServer and the beacon"""

import servercom

with open('cert.pem', 'r') as fp:
    server_cert=fp.read()

servercom.CUBESERVER_DEFAULT_CONFIG.API_HOST = 'localhost'
servercom.CUBESERVER_DEFAULT_CONFIG.API_PORT = 8889

c = servercom.Connection(server_cert=server_cert, verbose=True, _force=True)
c.context.load_cert_chain("beacon.pem", "beacon.key")

c.connect_socket()

c.wrapped_socket.send(b"Hello World!")
buf = c.wrapped_socket.recv(256)
print(buf)

c.close_socket()

#c.radio.stop_dhcp()
#c.radio.set_ipv4_address(
#    ipv4=IPv4Address("192.168.252.123"),
#    netmask=IPv4Address("255.255.255.0"),
#    gateway=IPv4Address("192.168.252.1")
#)
