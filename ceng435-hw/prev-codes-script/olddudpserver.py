import socket
import struct
import time
import glob
import os

def udp_server():
    #localIP     = "127.0.0.1"
    localIP     = "172.17.0.2"


    localPort   = 20001

    bufferSize  = 1024      

    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((localIP, localPort))

    window_size = 1  # Initial window size
    ssthresh = 8     # Slow start threshold
    # REMEMBER TO CHANGE PATH WHENEVER YOU CARRY THIS SCRIPT!!!!
    objects_path = '../objects/'
    
    # List all .obj files in the objects directory
    obj_files = sorted(glob.glob(os.path.join(objects_path, '*.obj')))  # Sort the files
    print(f"Found object files: {obj_files}")
    # Create packets with the content of each .obj file
  # Maximum size of data in each UDP packet
    MAX_PACKET_SIZE = 1000  # 10 KB

    # Create packets with the content of each .obj file
    packets = []
    for file_path in obj_files:
        with open(file_path, 'rb') as file:  # Open in binary mode
            data = file.read()

            # Split the file into chunks
            chunks = [data[i:i+MAX_PACKET_SIZE] for i in range(0, len(data), MAX_PACKET_SIZE)]
            
            # Create a packet for each chunk
            for i, chunk in enumerate(chunks):
                # Pack the sequence number (i) and the chunk
                packet = struct.pack('I', i) + chunk
                packets.append(packet)
                print(f"Created packet {i} for file {file_path} with size {len(packet)}")

            
    next_seq_num = 0
    base = 0
    duplicate_acks = 0

    while(True):
        try:
            while base < len(packets):
                while next_seq_num < base + window_size and next_seq_num < len(packets):
                    print(f"Sending packet: {next_seq_num} Size: {len(packets[next_seq_num])}")
                    server_socket.sendto(packets[next_seq_num], (localIP, localPort))
                    next_seq_num += 1

                server_socket.settimeout(0.5)  # Set timeout for ACKs
                try:
                    ack_packet, address = server_socket.recvfrom(bufferSize)
                    #if address[0] != clientIP:
                        #print(f"Ignoring packet from unknown address: {address}")
                        #continue
                    if len(ack_packet) != 8:
                        print(f"Received an incorrectly sized packet: {len(ack_packet)} bytes")
                        continue

                    ack, _ = struct.unpack('II', ack_packet)
                    print(f"ACK received for packet: {ack}")

                    if ack > base:
                        base = ack + 1
                        duplicate_acks = 0
                        if window_size < ssthresh:
                            window_size += 1  # Slow start
                        else:
                            window_size += 1 / window_size  # Congestion avoidance
                    elif ack == base:
                        duplicate_acks += 1
                        if duplicate_acks == 3:  # Fast retransmit condition
                            print("Triple duplicate ACKs received, fast retransmit")
                            ssthresh = window_size / 2
                            window_size = ssthresh + 3
                            next_seq_num = ack + 1

                except socket.timeout:
                    print(f"Timeout, resending from packet: {base}")
                    ssthresh = window_size / 2  # Multiplicative decrease
                    window_size = 1  # Reset window size
                    next_seq_num = base
                    duplicate_acks = 0

        finally:
            server_socket.close()

if __name__ == "__main__":
    udp_server()

