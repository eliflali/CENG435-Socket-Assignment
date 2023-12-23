import socket
import struct

def udp_client():
    #server_host     = "127.0.0.1"
    server_host = '172.17.0.2'  # Server IP address
    server_port = 20001         # Server port
    client_host = '172.17.0.3'  # Client IP address
    #client_host = '127.0.0.1'
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((client_host, 0))  # Bind the client socket

    # Send a 'ready' message to the server to indicate that the client is ready
    print("Sending ready message to the server...")
    client_socket.sendto(b'ready', (server_host, server_port))

    expected_seq = 0
    received_packets = {}  # Dictionary to keep track of received packets

    try:
        while True:
            packet, server_address = client_socket.recvfrom(1024)
            seq, = struct.unpack('I', packet[:4])
            data = packet[4:]

            # Assuming the end of transmission from server
            if not data:
                break

            if seq == expected_seq:
                print(f"Received packet: {seq}")
                
                # Store the received data in the order of sequence numbers
                received_packets[seq] = data

                # Send ACK
                ack_packet = struct.pack('II', seq, 0)  # Ensure this is 8 bytes
                client_socket.sendto(ack_packet, server_address)

                # Update expected sequence number for next packet
                expected_seq += 1
            else:
                print(f"Out of order packet: {seq}, expected: {expected_seq}")

    finally:
        client_socket.close()
        # Reassemble the file from the received packets
        with open('received_file.obj', 'wb') as f:
            for i in sorted(received_packets.keys()):
                f.write(received_packets[i])
        print("File reassembled and saved as 'received_file.obj'.")

if __name__ == "__main__":
    udp_client()
