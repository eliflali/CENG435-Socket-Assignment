import socket
import os
import glob

def read_files():
    objects_path = '../../objects'
    file_paths = sorted(glob.glob(os.path.join(objects_path, '*.obj')))
    obj_files = []

    # one small and one large file:
    for i in range(0, len(file_paths)//2):
        obj_files.append(file_paths[i])
        obj_files.append(file_paths[i+len(file_paths)//2])

    print(f"Found object files: {obj_files}")
    return obj_files

def send_file(conn, file_path, delimiter=b'<<EOF>>'):
    # Maximum data size to send in each packet
    MAX_PACKET_SIZE = 1000

    with open(file_path, 'rb') as file:
        data = file.read()
        chunks = [data[i:i+MAX_PACKET_SIZE] for i in range(0, len(data), MAX_PACKET_SIZE)]

        # send 1000 bytes at a time
        for chunk in chunks:
            conn.sendall(chunk)

        conn.sendall(delimiter)

def tcp_server():
    host = "127.0.0.1"
    port = 65432

    obj_files = read_files()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, port))
        s.listen()
        print(f"Server listening on {host}:{port}")
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            for file_path in obj_files:
                send_file(conn, file_path)
                print("File sent", file_path)

tcp_server()
