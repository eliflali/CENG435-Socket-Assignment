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

# Add a timestamp variable to track the last received packet time
last_packet_time = time.time()
TIMEOUT_THRESHOLD = 5  # 5 seconds timeout threshold

def receive_data(client_socket, packet_queue, server_address, is_complete, last_packet_time_lock):
    global last_packet_time  # Use the global variable
    while not is_complete.is_set():
        try:
            packet, _ = client_socket.recvfrom(1024)
            if not packet:
                break
            packet_queue.put(packet)
            with last_packet_time_lock:
                last_packet_time = time.time()  # Update the timestamp for the last received packet
        except socket.error as e:
            print(f"Socket error: {e}")
            break

def save_files(file_id, received_files):
    # Write each file's data to a separate file
    for file_id, received_packets in received_files.items():
        with open(f'received_file_{file_id}.obj', 'wb') as f:
            for i in sorted(received_packets.keys()):
                f.write(received_packets[i])
        print(f"File {file_id} reassembled and saved as 'received_file_{file_id}.obj'.")

def process_packets(packet_queue, received_files, expected_seqs, expected_seq_lock, server_address, client_socket, is_complete, last_packet_time_lock):
    global last_packet_time
    while not is_complete.is_set():
        try:
            packet = packet_queue.get(timeout=1)
            if not packet:
                break

            # Unpack the file ID and sequence number
            file_id, seq, incoming_checksum = struct.unpack('III', packet[:12])

            if seq == 100000:  # Termination message
                print("Termination message received. Ending transmission.")
                is_complete.set()
                save_files(file_id, received_files)
                break

            data = packet[12:]

            with expected_seq_lock:
                if verify_checksum(data, incoming_checksum) == True:
                    #print(f"Checksum verification successful for packet: {seq} from file {file_id}")
                    # Initialize the dictionary for a new file ID and its expected sequence number
                    if file_id not in received_files:
                        received_files[file_id] = {}
                        expected_seqs[file_id] = 0

                    # If we haven't received any packets for this file yet, set the expected sequence number
                    if expected_seqs[file_id] == 0:
                        #print("first packet received from file: ", file_id)
                        expected_seqs[file_id] = seq
                        expected_seq = seq 
                    else:
                        #print("expected seq: ", expected_seqs[file_id])
                        expected_seq = expected_seqs[file_id]

                    if seq == expected_seq:
                        print(f"Received packet: {seq} from file {file_id}")
                        received_files[file_id][seq] = data
                        expected_seqs[file_id] += 1  # Update the expected sequence number for the file

                        # Check for any buffered out-of-order packets that can now be processed
                        while expected_seqs[file_id] in received_files[file_id]:
                            expected_seq = expected_seqs[file_id]
                            print(f"Received packet: {expected_seq} from file {file_id}")
                            expected_seqs[file_id] += 1

                        # Send ACK for the correctly received packet
                        ack_packet = struct.pack('III', file_id, seq, 0)
                        client_socket.sendto(ack_packet, server_address)

                    elif seq > expected_seq:
                        print(f"Out of order packet: {seq}, expected: {expected_seq} from file {file_id}")
                        received_files[file_id][seq] = data
                        # Send a NACK for the missing packet
                        ack_packet = struct.pack('III', file_id, seq, 0)
                        client_socket.sendto(ack_packet, server_address)
                        nack_packet = struct.pack('III', file_id, expected_seq, 1)
                        client_socket.sendto(nack_packet, server_address)
                else:
                    print(f"Checksum verification failed for packet: {seq} from file {file_id}")
                    # Send a NACK for the packet with the wrong checksum
                    nack_packet = struct.pack('III', file_id, seq, 1)
                    client_socket.sendto(nack_packet, server_address)
        except queue.Empty:
            with last_packet_time_lock:
                current_time = time.time()
                if current_time - last_packet_time > TIMEOUT_THRESHOLD:
                    is_complete.set()  # Set the completion flag if timeout threshold is exceeded
            continue

    client_socket.close()


def udp_client():
    #server_host = "127.0.0.1"
    server_host = '172.17.0.2'  # Server IP address
    server_port = 20001
    #client_host = "127.0.0.1"
    client_host = '172.17.0.3'  # Client IP address
    client_port = 20002
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((client_host, client_port))

    print("Sending ready message to the server...")
    client_socket.sendto(b'ready', (server_host, server_port))

    packet_queue = queue.Queue()
    received_packets = {}
    expected_seqs = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    
    expected_seq_lock = threading.Lock()
    last_packet_time_lock = threading.Lock()
    is_complete = threading.Event()

    global last_packet_time
    last_packet_time = time.time()

    # Creating threads with the last_packet_time_lock passed as an argument
    receiver_thread = threading.Thread(target=receive_data, args=(client_socket, packet_queue, (server_host, server_port), is_complete, last_packet_time_lock))
    processor_thread = threading.Thread(target=process_packets, args=(packet_queue, received_packets, expected_seqs, expected_seq_lock, (server_host, server_port), client_socket, is_complete, last_packet_time_lock))

    receiver_thread.start()
    processor_thread.start()

    #receiver_thread.join()
    #processor_thread.join()
    #client_socket.close()    

    # Save the received data to a file
    

if __name__ == "__main__":
    udp_client()