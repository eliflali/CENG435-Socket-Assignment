import socket
import struct
import threading
import time
import glob
import os
import zlib
import threading



def read_files():
    objects_path = '../../objects'
    obj_files = sorted(glob.glob(os.path.join(objects_path, '*.obj')))
    print(f"Found object files: {obj_files}")
    return obj_files



def compute_checksum(data):
    return zlib.crc32(data) & 0xffffffff


def packet_creator(obj_files):
    MAX_PACKET_SIZE = 1000
    packets_per_file = {}
    file_transmission_state = {}
    packet_transmission_state = {}
    file_id = 0
    
    for file_path in obj_files:
        with open(file_path, 'rb') as file:
            data = file.read()
            # Reset sequence number for each file
            
            file_packets = []
            sequence_number = 0
            # Split the file into chunks
            chunks = [data[i:i+MAX_PACKET_SIZE] for i in range(0, len(data), MAX_PACKET_SIZE)]
            file_packet_transmission_state = []
            # Create a packet for each chunk
            for chunk in chunks:
                checksum = compute_checksum(chunk)
                packet = struct.pack('III', file_id, sequence_number, checksum) + chunk
                file_packets.append(packet)
                file_packet_transmission_state.append('UNACKED')
                print(f"Created packet {sequence_number} for file {file_path} with size {len(packet)}")
                sequence_number += 1  # Increment sequence number for the next packet
            packet_transmission_state[file_id] = file_packet_transmission_state
            file_transmission_state[file_id] = {'base': 0, 'next_seq_num': 0, 'window_size': 4}
            packets_per_file[file_id] = file_packets
            file_id += 1  # Increment file ID for the next file

    return packets_per_file, file_transmission_state, packet_transmission_state


def round_robinizer(packets_per_file):
    round_robin_packets = []
    for packet in range(len(packets_per_file[0])): #change 18
        for file_number in range(len(packets_per_file)):
            if packet < len(packets_per_file[file_number]):
                round_robin_packets.append((file_number, packets_per_file[file_number][packet]))
                #print(packet, file_number)
    
    return round_robin_packets

def send_packets(file_id, packets, clientIP, clientPort, server_socket, packet_transmission_state, ack_counter, ack_counter_lock):
    for packet_index, packet in enumerate(packets):
        # Check the state of the packet before sending
        if packet_transmission_state[file_id][packet_index] != 'ACKED':
            print(f"Sending packet {packet_index} from file {file_id}")
            server_socket.sendto(packet, (clientIP, clientPort))
        with ack_counter_lock:
            ack_counter += 1
            

def udp_server():
    #localIP = "127.0.0.1"
    localIP  = "172.17.0.2" #if compiled with docker
    localPort = 20001
    bufferSize = 1024
    finished= False

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((localIP, localPort))


    #clientIP = "127.0.0.1"
    clientIP = "172.17.0.3"  # Client's IP address
    clientPort = 20002
    window_size = 4
    obj_files = read_files()
    
    packets_per_file, file_transmission_state, packet_transmission_state = packet_creator(obj_files)
    
    round_robin_packets = round_robinizer(packets_per_file)

    print("Waiting for client to be ready...")
    ready_packet, address = server_socket.recvfrom(bufferSize)
    print(f"Client ready message received from {address}")

    # Create a shared counter for ACKs and a lock for thread-safe operations
    ack_counter = 0
    ack_counter_lock = threading.Lock()

    # Start a thread for each file
    threads = []

    for file_id, packets in packets_per_file.items():
        t = threading.Thread(target=send_packets, args=(file_id, packets, clientIP, clientPort, server_socket, packet_transmission_state, ack_counter, ack_counter_lock))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Wait for all threads to complete
    for t in threads:
        t.join()


     # Handling ACKs and retransmissions
    all_acked = False
    while not all_acked:
        try:
            server_socket.settimeout(1.0)  # Set timeout for receiving ACKs
            ack_packet, address = server_socket.recvfrom(bufferSize)
            
            if address[0] != clientIP or address[1] != clientPort:
                continue  # Ignore packets from unknown addresses

            ack_file_id, ack_seq_num, is_nack = struct.unpack('III', ack_packet)
            if is_nack:
                # Resend the packet if NACK received
                packet_to_resend = packets_per_file[ack_file_id][ack_seq_num]
                server_socket.sendto(packet_to_resend, (clientIP, clientPort))
            else:
                # Mark packet as ACKed
                packet_transmission_state[ack_file_id][ack_seq_num] = 'ACKED'

            # Check if all packets are ACKed
            all_acked = all(packet_state == 'ACKED' for packet_states in packet_transmission_state.values() for packet_state in packet_states)

        except socket.timeout:
            # Resend unacknowledged packets on timeout
            for file_id, packet_states in packet_transmission_state.items():
                for seq_num, state in enumerate(packet_states):
                    if state != 'ACKED':
                        packet_to_resend = packets_per_file[file_id][seq_num]
                        server_socket.sendto(packet_to_resend, (clientIP, clientPort))

    # Send termination packet once all ACKs received
    termination_packet = struct.pack('III', 0, 100000, 0)
    server_socket.sendto(termination_packet, (clientIP, clientPort))
    server_socket.close()


if __name__ == "__main__":
    udp_server()