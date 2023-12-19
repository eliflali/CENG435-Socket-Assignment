import socket
import struct

def udp_client():
    server_host = '172.17.0.2'  # Server IP address
    server_port = 20001         # Server port

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    expected_seq = 0
    try:
        while True:
            packet, server_address = client_socket.recvfrom(1024)
            seq, = struct.unpack('I', packet[:4])
            data = packet[4:]

            if seq == expected_seq:
                print(f"Received packet: {seq}")
                expected_seq += 1

                # Send ACK with a dummy value for the second integer
                ack_packet = struct.pack('II', seq, 0)  # Ensure this is 8 bytes
                client_socket.sendto(ack_packet, (server_host, server_port))
            else:
                print(f"Out of order packet: {seq}, expected: {expected_seq}")
    finally:
        client_socket.close()

udp_client()
