import socket
import struct
import threading
import time
import glob
import os
import zlib



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
            

def udp_server():
    localIP = "127.0.0.1"
    #localIP  = "172.17.0.2" #if compiled with docker
    localPort = 20001
    bufferSize = 1024
    finished= False

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((localIP, localPort))


    clientIP = "127.0.0.1"
    #clientIP = "172.17.0.3"  # Client's IP address
    clientPort = 20002
    window_size = 4
    ssthresh = 8  # Threshold for switching between slow start and congestion avoidance
    is_slow_start = True  # Flag to indicate if the algorithm is in slow start phase
    obj_files = read_files()
    
    packets_per_file, file_transmission_state, packet_transmission_state = packet_creator(obj_files)
    
    round_robin_packets = round_robinizer(packets_per_file)

    print("Waiting for client to be ready...")
    ready_packet, address = server_socket.recvfrom(bufferSize)
    print(f"Client ready message received from {address}")

    rr_packet_index = 0
    ack_counter = 0
    duplicate_acks = 0
    unacknowledged_packets = set()
    try:
        while ack_counter < len(round_robin_packets)-1:
            if ack_counter >= len(round_robin_packets):
                break
            
            if(len(round_robin_packets) - rr_packet_index < window_size):
                window_size = len(round_robin_packets) - rr_packet_index -1 

            while ((rr_packet_index < ack_counter + window_size) 
                    and 
                    (rr_packet_index < len(round_robin_packets))):
                (file_id, packet) = round_robin_packets[rr_packet_index]
                file_state = file_transmission_state[file_id]
                #print(file_id, file_state['next_seq_num'])
                packet_state = packet_transmission_state[file_id][file_state['next_seq_num']]
                print(f"Sending packet {file_state['next_seq_num']} from file {file_id}")
                if(packet_state == 'ACKED'):
                    print(f"Already acked packet {file_state['next_seq_num']} from file {file_id}")
                    file_state['next_seq_num'] += 1
                    rr_packet_index += 1
                    continue
                #print(round_robin_packets[next_seq_num][1])
                server_socket.sendto(packet, (clientIP, clientPort))
                packet_identifier = (file_id, file_state['next_seq_num'])
                unacknowledged_packets.add(packet_identifier)
                file_state['next_seq_num'] += 1
                rr_packet_index += 1

            server_socket.settimeout(1.0)
            try:
                ack_packet, address = server_socket.recvfrom(bufferSize)
                if address[0] != clientIP or address[1] != clientPort:
                    print(f"Ignoring packet from unknown address: {address}")
                    continue

                ack_file_id, ack_seq_num, is_nack = struct.unpack('III', ack_packet)

                if is_nack:
                    # This is a NACK, retransmit the specified packet
                    packet_to_resend = packets_per_file[ack_file_id][ack_seq_num]
                    server_socket.sendto(packet_to_resend, (clientIP, clientPort))
                    print(f"Resending packet {ack_seq_num} from file {ack_file_id}")

                else:
                    file_state = file_transmission_state[ack_file_id]
                    packet_state = packet_transmission_state[ack_file_id][ack_seq_num]
                    acked_packet = (ack_file_id, ack_seq_num)
                    if acked_packet in unacknowledged_packets:
                        unacknowledged_packets.remove(acked_packet)
                    if ack_seq_num >= file_state['base']:
                        file_state['base'] = ack_seq_num + 1
                        packet_state = 'ACKED'
                        ack_counter += 1
                        #print(ack_seq_num)
                        print(f"ACK received for packet {ack_seq_num} from file {ack_file_id} base: {ack_counter}")
                
                if is_slow_start:
                    if window_size < ssthresh:
                        window_size *= 2  # Exponential increase
                    else:
                        is_slow_start = False  # Switch to congestion avoidance
                else:
                    window_size += 1  # Linear increase in congestion avoidance

            except socket.timeout:
                print("Timeout occurred")
                ssthresh = max(window_size // 2, 1)  # Reduce threshold
                window_size = 1  # Reset window size to 1
                is_slow_start = True  # Go back to slow start phase
                if ack_counter != len(round_robin_packets) - 1:
                    print("Timeout occurred, resending unacknowledged packets")
                    for file_id, seq_num in unacknowledged_packets:
                        packet_to_resend = packets_per_file[file_id][seq_num]
                        print(file_id, seq_num)
                        server_socket.sendto(packet_to_resend, (clientIP, clientPort))
                        print(f"Resent packet {seq_num} from file {file_id}")
    finally:
        #print(base, rr_packet_index)
        finished = True
        if ack_counter >= rr_packet_index:
            
            print("All packets have been acknowledged. Terminating server.")
        else:
            print("Server terminated without receiving all ACKs.")
        termination_packet = struct.pack('III', 0, 100000, 0)
        server_socket.sendto(termination_packet, (clientIP, clientPort))
        server_socket.close()

if __name__ == "__main__":
    udp_server()