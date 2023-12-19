# echo-client.py

import socket
import sys

HOST = "172.17.0.2" # The server's hostname or IP address
PORT = 8080  # The port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    print("connected")
    s.sendall(b"Hello, world")
    data = s.recv(1024)


