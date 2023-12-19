import socket

def receive_file(s, file_path):
    with open(file_path, 'wb') as file:
        while True:
            data = s.recv(1024)
            if not data:
                break
            file.write(data)

def tcp_client():
    host = '172.17.0.2'  # Server IP
    port = 65432        # Port to connect to

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        for i in range(10):
            receive_file(s, f"received_small-{i}.obj")
            receive_file(s, f"received_large-{i}.obj")

tcp_client()
