import socket
import struct
import threading
import queue
import time
import zlib

def compute_checksum(data):
    return zlib.crc32(data) & 0xffffffff

def verify_checksum(data, received_checksum):
    computed_checksum = compute_checksum(data)
    return computed_checksum == received_checksum

def save_files(received_files):
    # Write each file's data to a separate file
    for file_id, received_packets in received_files.items():
        with open(f'received_file_{file_id}.obj', 'wb') as f:
            for i in sorted(received_packets.keys()):
                f.write(received_packets[i])
        print(f"File {file_id} reassembled and saved as 'received_file_{file_id}.obj'.")

def udp_client():
    #server_host = '172.17.0.2'  # Server IP address
    server_host = "127.0.0.1"
    server_port = 20001
    #client_host = '172.17.0.3'  # Client IP address
    client_host = "127.0.0.1"
    client_port = 20002
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((client_host, client_port))

    print("Sending ready message to the server...")
    client_socket.sendto(b'ready', (server_host, server_port))

    received_files = {}
    expected_seqs = {}
    try:
        while True:
            # Receive packet from server
            packet, _ = client_socket.recvfrom(1024)
            if not packet:
                break

            # Unpack the file ID, sequence number, and checksum
            file_id, seq, incoming_checksum = struct.unpack('III', packet[:12])
            data = packet[12:]

            # Check if it is a termination message
            if seq == 100000:
                print("Termination message received. Ending transmission.")
                break

            # Verify the checksum
            if not verify_checksum(data, incoming_checksum):
                print(f"Checksum verification failed for packet: {seq} from file {file_id}")
                nack_packet = struct.pack('III', file_id, seq, 1)
                client_socket.sendto(ack_packet, (server_host, server_port))

            # Initialize the dictionary for a new file ID
            if file_id not in received_files:
                received_files[file_id] = {}
                expected_seqs[file_id] = 0

            # Store packet in received_files
            received_files[file_id][seq] = data

            # Send ACK for the correctly received packet
            ack_packet = struct.pack('III', file_id, seq, 0)
            client_socket.sendto(ack_packet, (server_host, server_port))

            # Check for any buffered out-of-order packets that can now be processed
            while expected_seqs[file_id] in received_files[file_id]:
                # Send ACK for the correctly received packet
                print(f"Processing packet: {expected_seqs[file_id]} from file {file_id}")
                ack_packet = struct.pack('III', file_id, expected_seqs[file_id], 0)
                client_socket.sendto(ack_packet, (server_host, server_port))
                expected_seqs[file_id] += 1

    finally:
        client_socket.close()

    save_files(received_files)


if __name__ == "__main__":
    udp_client()