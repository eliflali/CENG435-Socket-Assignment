import socket
import os

def send_file(conn, file_path):
    with open(file_path, 'rb') as file:
        while True:
            data = file.read(1024)
            if not data:
                break
            conn.sendall(data)

def tcp_server():
    host = '0.0.0.0'  # Server IP
    port = 65432        # Port to listen on

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            for i in range(10):
                send_file(conn, f"small-{i}.obj")
                send_file(conn, f"large-{i}.obj")

tcp_server()
