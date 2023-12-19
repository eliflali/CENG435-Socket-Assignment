import socket

def udp_client():
    host = '172.17.0.2'
    port = 65433

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        # Implement logic to send data and handle acknowledgments

udp_client()
