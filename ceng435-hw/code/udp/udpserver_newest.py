import socket
import struct
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
    #print(f"Found object files: {obj_files}")
    
    MAX_PACKET_SIZE = 1000
    packets_lists = {}
    seq_number = 0
    file_paths = []

    for file_index, file_path in enumerate(obj_files):
        file_paths.append(file_path)
        packets_lists[file_path] = []
        with open(file_path, 'rb') as file:
            data = file.read()
            chunks = [data[i:i+MAX_PACKET_SIZE] for i in range(0, len(data), MAX_PACKET_SIZE)]
            for chunk in chunks:
                # Include file index and sequence number in the packet
                packet = struct.pack('II', file_index, seq_number) + chunk
                packets_lists[file_path].append(packet)
                #print(f"Created packet {seq_number} for file {file_path} with size {len(packet)}")
                seq_number += 1
    
    # alter the order in file_paths so that 1 large and 1 small file are consecutive
    ordered_file_paths = []
    for i in range(0, len(file_paths)//2):
        ordered_file_paths.append(file_paths[i])
        ordered_file_paths.append(file_paths[i+len(file_paths)//2])     
   
    print("Waiting for client to be ready...")
    ready_packet, address = server_socket.recvfrom(bufferSize)
    print(f"Client ready message received from {address}")

    next_seq_num = 0
    base_per_file = {file_path: 0 for file_path in ordered_file_paths}
    acked_packets = set()

    while any(base_per_file[file_path] < len(packets_lists[file_path]) for file_path in ordered_file_paths):
        for file_path in ordered_file_paths:
            if base_per_file[file_path] >= len(packets_lists[file_path]):
                continue

            while base_per_file[file_path] < len(packets_lists[file_path]) and next_seq_num < base_per_file[file_path] + window_size:
                packet = packets_lists[file_path][base_per_file[file_path]]
                print(f"Sending packet from file {file_path}, sequence number: {base_per_file[file_path]}")
                server_socket.sendto(packet, (clientIP, clientPort))
                next_seq_num += 1

            server_socket.settimeout(1.0)
            try:
                ack_packet, address = server_socket.recvfrom(bufferSize)
                if address[0] != clientIP or address[1] != clientPort:
                    print(f"Ignoring packet from unknown address: {address}")
                    continue

                ack_file_index, ack_seq = struct.unpack('II', ack_packet[:8])
                acked_file_path = file_paths[ack_file_index]
                print(f"ACK received for packet: {ack_seq} from file {ack_file_index}")

                # Update the base for the specific file
                if ack_seq >= base_per_file[acked_file_path]:
                    base_per_file[acked_file_path] = ack_seq + 1
                    acked_packets.add((ack_file_index, ack_seq))

                # Check for completion of all files
                if all(base_per_file[file_path] == len(packets_lists[file_path]) for file_path in ordered_file_paths):
                    print("All packets have been acknowledged. Terminating server.")
                    server_socket.close()
                    return

            except socket.timeout:
                print(f"Timeout, checking for missing packets...")
                for file_path in ordered_file_paths:
                    for seq in range(base_per_file[file_path], len(packets_lists[file_path])):
                        if (file_paths.index(file_path), seq) not in acked_packets:
                            print(f"Resending packet from file {file_path}, sequence number: {seq}")
                            server_socket.sendto(packets_lists[file_path][seq], (clientIP, clientPort))

if __name__ == "__main__":
    udp_server()
