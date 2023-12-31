import socket
import struct
import glob
import os
import zlib

def compute_checksum(data):
    return zlib.crc32(data) & 0xffffffff

def udp_server():
    localIP = "127.0.0.1"
    localPort = 20001
    bufferSize = 1024

    server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    server_socket.bind((localIP, localPort))

    window_size = 4
    ssthresh = 8
    objects_path = 'C:/Users/Administrator/Desktop/CENG435-Socket-Assignment-main/ceng435-hw/objects'

    clientIP = "127.0.0.1"
    clientPort = 20002

    file_paths = sorted(glob.glob(os.path.join(objects_path, '*.obj')))
    
    ordered_file_paths = []
    for i in range(0, len(file_paths)//2):
        ordered_file_paths.append(file_paths[i])
        ordered_file_paths.append(file_paths[i+len(file_paths)//2])
    print(f"Found object files: {ordered_file_paths}")

    #ordered_file_paths = [ordered_file_paths[1], ordered_file_paths[3]]

    MAX_PACKET_SIZE = 1000
    packets_per_file = {}
    file_transmission_state = {}
    sequence_number = 0
    ack_received = 0  # Initialize an ACK counter
    file_id = 0

    for file_path in ordered_file_paths:
        with open(file_path, 'rb') as file:
            data = file.read()
            chunks = [data[i:i+MAX_PACKET_SIZE] for i in range(0, len(data), MAX_PACKET_SIZE)]
            file_packets = []
            for chunk in chunks:
                checksum = compute_checksum(chunk)
                packet = struct.pack('III', file_id, sequence_number, checksum) + chunk
                file_packets.append(packet)
                sequence_number += 1

            packets_per_file[file_id] = file_packets
            file_transmission_state[file_id] = {'base': 0, 'next_seq_num': 0, 'window_size': window_size}
            print(f"Created {len(file_packets)} packets for file {file_path}")
            file_id += 1

    round_robin_packet_iterators = [iter(packets) for packets in packets_per_file.values()]
    sent_packets = 0

    print("Waiting for client to be ready...")
    ready_packet, address = server_socket.recvfrom(bufferSize)
    print(f"Client ready message received from {address}")

    try:
        while ack_received < sequence_number:
            for file_id, packet_iterator in enumerate(round_robin_packet_iterators):
                state = file_transmission_state[file_id]
                # While there's room in the window and more packets to send for this file
                while (state['next_seq_num'] < (state['base'] + state['window_size'])) and (state['next_seq_num'] < len(packets_per_file[file_id])):
                    try:
                        packet_to_send = next(packet_iterator)
                        server_socket.sendto(packet_to_send, (clientIP, clientPort))
                        print(f"Sending packet {state['next_seq_num']} from file {file_id}")
                        state['next_seq_num'] += 1
                        sent_packets += 1
                        # Break the inner loop to send packets from the next file
                        break
                        # BURADAKİ WINDOW SIZE IMPLEMENTATIONI MANTIKSIZ, BUNUN KONUŞULMASI LAZIM
                    except StopIteration:
                        # This file has no more packets to send
                        break

            server_socket.settimeout(1.0)
            try:
                ack_packet, address = server_socket.recvfrom(bufferSize)
                ack_file_id, ack_seq_num, is_nack = struct.unpack('III', ack_packet)
                if is_nack:
                    # This is a NACK, retransmit the specified packet
                    packet_to_resend = packets_per_file[ack_file_id][ack_seq_num]
                    server_socket.sendto(packet_to_resend, (clientIP, clientPort))
                    print(f"Resending packet {ack_seq_num} from file {ack_file_id}")
                else:
                    state = file_transmission_state[ack_file_id]
                    if ack_seq_num >= state['base']:
                        state['base'] = ack_seq_num + 1
                        ack_received += 1
                        print(f"ACK received for packet {ack_seq_num} from file {ack_file_id}")
                        # Removed dynamic window size adjustment here

            except socket.timeout:
                print("Timeout, resending packets")
                for file_id in range(len(ordered_file_paths)):
                    state = file_transmission_state[file_id]
                    # Removed dynamic window size adjustment here
                    state['next_seq_num'] = state['base']

    finally:
        #print(ack_received, sequence_number)
        if ack_received >= sequence_number:
            print("All packets have been acknowledged. Terminating server.")
        else:
            print("Server terminated without receiving all ACKs.")
        termination_packet = struct.pack('III', 0, 100000, 0)
        server_socket.sendto(termination_packet, (clientIP, clientPort))
        server_socket.close()

if __name__ == "__main__":
    udp_server()
