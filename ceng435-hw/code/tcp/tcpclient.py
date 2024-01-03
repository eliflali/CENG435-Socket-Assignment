import socket

def receive_file(s, file_path, delimiter=b'<<EOF>>'):
    file_data = b''
    while True:
        data = s.recv(1024)
        if not data:
            break
        file_data += data

        # Process all complete files in file_data
        while delimiter in file_data:
            file_content, file_data = file_data.split(delimiter, 1)
            with open(file_path, 'wb') as file:
                file.write(file_content)
            return file_data  # Return the remaining data for the next file

    # In case the connection is closed without receiving a delimiter
    if file_data:
        with open(file_path, 'wb') as file:
            file.write(file_data)



def tcp_client():
    host = "127.0.0.1"
    port = 65432

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        for i in range(20):
            receive_file(s, f"./received-{i}.obj")
            print("File received", f"received-{i}.obj")

tcp_client()
