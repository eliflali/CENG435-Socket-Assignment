import socket
import struct
import threading
import time
import glob
import os

def udp_server():
    localIP = "127.0.0.1"
    localPort = 20001
    bufferSize = 1024

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((localIP, localPort))

    window_size = 1
    ssthresh = 8
    objects_path = 'C:/Users/Administrator/Desktop/CENG435-Socket-Assignment-main/ceng435-hw/objects'
 
    clientIP = "127.0.0.1"
    clientPort = 20002

    obj_files = sorted(glob.glob(os.path.join(objects_path, '*.obj')))
    print(f"Found object files: {obj_files}")

    MAX_PACKET_SIZE = 1000
    packets = []
    i=0
    for file_path in obj_files:
        with open(file_path, 'rb') as file:  # Open in binary mode
            data = file.read()

            # Split the file into chunks
            chunks = [data[i:i+MAX_PACKET_SIZE] for i in range(0, len(data), MAX_PACKET_SIZE)]
            
            # Create a packet for each chunk
            for chunk in chunks:
                # Pack the sequence number (i) and the chunk
                packet = struct.pack('I', i) + chunk
                packets.append(packet)
                print(f"Created packet {i} for file {file_path} with size {len(packet)}")
                i += 1

    print("Waiting for client to be ready...")
    ready_packet, address = server_socket.recvfrom(bufferSize)
    print(f"Client ready message received from {address}")

    next_seq_num = 0
    base = 0
    duplicate_acks = 0

    while True:
        if base == len(packets):
            break
        try:
            while base < len(packets):
                while next_seq_num < base + window_size and next_seq_num < len(packets):
                    print(f"Sending packet: {next_seq_num} Size: {len(packets[next_seq_num])}")
                    server_socket.sendto(packets[next_seq_num], (clientIP, clientPort))
                    next_seq_num += 1

                server_socket.settimeout(1.0)
                try:
                    ack_packet, address = server_socket.recvfrom(bufferSize)
                    if address[0] != clientIP or address[1] != clientPort:
                        print(f"Ignoring packet from unknown address: {address}")
                        continue

                    ack, nack_flag = struct.unpack('II', ack_packet)
                    print(f"ACK received for packet: {ack}")

                    if nack_flag == 1:  # NACK handling
                        print(f"NACK received for packet: {ack}, retransmitting")
                        base = ack
                        next_seq_num = ack
                        continue

                    if ack >= base:
                        base = ack + 1
                        print(f"Updated base to: {base}")  # Debug print to confirm base update
                        duplicate_acks = 0
                        if window_size < ssthresh:
                            window_size += 1
                        else:
                            window_size += 1 / window_size
                    elif ack == base-1:
                        duplicate_acks += 1
                        if duplicate_acks == 3:
                            print("Triple duplicate ACKs received, fast retransmit")
                            ssthresh = window_size / 2
                            window_size = ssthresh + 3
                            next_seq_num = base

                except socket.timeout:
                    print(f"Timeout, resending from packet: {base}")
                    ssthresh = window_size / 2
                    window_size = 1
                    next_seq_num = base
                    duplicate_acks = 0

        finally:
            print("All packets have been acknowledged. Terminating server.")
            # send client a termination message
            termination_packet = struct.pack('I', 100000)
            server_socket.sendto(termination_packet, (clientIP, clientPort))
            server_socket.close()

if __name__ == "__main__":
    udp_server()
