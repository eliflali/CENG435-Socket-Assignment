import socket
import struct
import threading
import queue
import os
import time

TIMEOUT_THRESHOLD = 5  # 5 seconds timeout threshold

def receive_data(client_socket, packet_queue, is_complete, last_packet_time_lock, last_packet_time):
    while not is_complete.is_set():
        try:
            packet, _ = client_socket.recvfrom(1024)
            if not packet:
                break
            packet_queue.put(packet)
            with last_packet_time_lock:
                last_packet_time[0] = time.time()  # Update last packet time
        except socket.error as e:
            print(f"Socket error: {e}")
            break

def process_packets(packet_queue, received_packets, expected_seq_lock, client_socket, server_address, is_complete, last_packet_time_lock, last_packet_time):
    while not is_complete.is_set():
        try:
            packet = packet_queue.get(timeout=1)
            if not packet:
                continue

            file_index, seq = struct.unpack('II', packet[:8])
            data = packet[8:]

            with expected_seq_lock:
                if file_index not in received_packets:
                    received_packets[file_index] = {}
                received_packets[file_index][seq] = data

                # Send ACK for this packet
                ack_packet = struct.pack('II', file_index, seq)
                client_socket.sendto(ack_packet, server_address)

            with last_packet_time_lock:
                current_time = time.time()
                if current_time - last_packet_time[0] > TIMEOUT_THRESHOLD:
                    is_complete.set()

        except queue.Empty:
            with last_packet_time_lock:
                current_time = time.time()
                if current_time - last_packet_time[0] > TIMEOUT_THRESHOLD:
                    is_complete.set()
            continue

def save_received_files(received_packets, output_path):
    for file_index in sorted(received_packets.keys()):
        file_data = b''.join(received_packets[file_index][seq] for seq in sorted(received_packets[file_index].keys()))
        file_path = os.path.join(output_path, f'received_file_{file_index}.obj')
        with open(file_path, 'wb') as file:
            file.write(file_data)
        print(f"Saved {file_path}")

def udp_client():
    server_host = "127.0.0.1"
    server_port = 20001
    client_host = "127.0.0.1"
    client_port = 20002
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.bind((client_host, client_port))

    print("Sending ready message to the server...")
    client_socket.sendto(b'ready', (server_host, server_port))

    packet_queue = queue.Queue()
    received_packets = {}
    expected_seq_lock = threading.Lock()
    last_packet_time = [time.time()]  # Initialize last_packet_time as a list to be mutable
    last_packet_time_lock = threading.Lock()
    is_complete = threading.Event()

    receiver_thread = threading.Thread(target=receive_data, args=(client_socket, packet_queue, is_complete, last_packet_time_lock, last_packet_time))
    processor_thread = threading.Thread(target=process_packets, args=(packet_queue, received_packets, expected_seq_lock, client_socket, (server_host, server_port), is_complete, last_packet_time_lock, last_packet_time))

    receiver_thread.start()
    processor_thread.start()

    receiver_thread.join()
    processor_thread.join()

    save_received_files(received_packets, 'C:/Users/Administrator/Desktop/CENG435-Socket-Assignment-main/ceng435-hw/received_files')

    client_socket.close()

if __name__ == "__main__":
    udp_client()
