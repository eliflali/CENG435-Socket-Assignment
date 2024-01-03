import socket
import struct
import threading
import queue
import time
import zlib

server_host = "127.0.0.1"
server_port = 20001

def compute_checksum(data):
    return zlib.crc32(data) & 0xffffffff

def verify_checksum(data, received_checksum):
    computed_checksum = compute_checksum(data)
    return computed_checksum == received_checksum

last_packet_time = time.time()
TIMEOUT_THRESHOLD = 5  # 5 seconds timeout threshold

def receive_data(client_socket, packet_queue, server_address, is_complete, last_packet_time_lock):
    global last_packet_time
    while not is_complete.is_set():
        try:
            packet, _ = client_socket.recvfrom(1024)
            if not packet:
                break
            packet_queue.put(packet)
            with last_packet_time_lock:
                last_packet_time = time.time()
        except socket.error as e:
            print(f"Socket error: {e}")
            break

def process_packets(packet_queue, received_files, expected_seqs, expected_seq_lock, server_address, client_socket, is_complete, last_packet_time_lock):
    global last_packet_time
    while not is_complete.is_set():
        try:
            packet = packet_queue.get(timeout=1)
            if not packet:
                continue  # Continue if no packet received

            file_id, seq, incoming_checksum = struct.unpack('III', packet[:12])
            if seq == 100000:
                # Termination message received
                is_complete.set()
                save_received_files(received_files)
                break

            data = packet[12:]
            with expected_seq_lock:
                if file_id not in received_files:
                    received_files[file_id] = {}
                    expected_seqs[file_id] = 0

                if verify_checksum(data, incoming_checksum) and seq >= expected_seqs[file_id]:
                    received_files[file_id][seq] = data
                    if seq == expected_seqs[file_id]:
                        update_expected_seqs(received_files, expected_seqs, file_id)
                    ack_packet = struct.pack('III', file_id, seq, 0)
                    client_socket.sendto(ack_packet, server_address)
                else:
                    nack_packet = struct.pack('III', file_id, expected_seqs[file_id], 1)
                    client_socket.sendto(nack_packet, server_address)

        except queue.Empty:
            handle_timeout(is_complete, last_packet_time_lock)

def save_received_files(received_files):
    for file_id, packets in received_files.items():
        with open(f'received_file_{file_id}.obj', 'wb') as f:
            for seq in sorted(packets):
                f.write(packets[seq])
        print(f"File {file_id} saved as 'received_file_{file_id}.obj'.")

def update_expected_seqs(received_files, expected_seqs, file_id):
    while expected_seqs[file_id] in received_files[file_id]:
        expected_seqs[file_id] += 1

def handle_timeout(is_complete, last_packet_time_lock):
    global last_packet_time
    with last_packet_time_lock:
        if time.time() - last_packet_time > TIMEOUT_THRESHOLD:
            is_complete.set()

def udp_client():
    
    client_socket = setup_client_socket()

    packet_queue = queue.Queue()
    received_files = {}
    expected_seqs = {}
    
    expected_seq_lock = threading.Lock()
    last_packet_time_lock = threading.Lock()
    is_complete = threading.Event()

    global last_packet_time
    last_packet_time = time.time()

    start_threads(client_socket, packet_queue, (server_host, server_port), received_files, expected_seqs, expected_seq_lock, is_complete, last_packet_time_lock)

def setup_client_socket():
    client_host = "127.0.0.1"
    client_port = 20002
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((client_host, client_port))
    client_socket.sendto(b'ready', (server_host, server_port))
    print("Sending ready message to the server...")
    return client_socket

def start_threads(client_socket, packet_queue, server_address, received_files, expected_seqs, expected_seq_lock, is_complete, last_packet_time_lock):
    receiver_thread = threading.Thread(target=receive_data, args=(client_socket, packet_queue, server_address, is_complete, last_packet_time_lock))
    processor_thread = threading.Thread(target=process_packets, args=(packet_queue, received_files, expected_seqs, expected_seq_lock, server_address, client_socket, is_complete, last_packet_time_lock))
    receiver_thread.start()
    processor_thread.start()

if __name__ == "__main__":
    udp_client()
