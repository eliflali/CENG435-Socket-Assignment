import socket
import struct
import time

def udp_server():
    host = '0.0.0.0'
    port = 65433

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))

    window_size = 1  # Initial window size
    ssthresh = 8     # Slow start threshold
    packets = [struct.pack('I', i) + b'Your data here' for i in range(20)]  # Example: 20 packets
    next_seq_num = 0
    base = 0
    duplicate_acks = 0

    try:
        while base < len(packets):
            while next_seq_num < base + window_size and next_seq_num < len(packets):
                print(f"Sending packet: {next_seq_num}")
                server_socket.sendto(packets[next_seq_num], (host, port))
                next_seq_num += 1

            server_socket.settimeout(0.5)  # Set timeout for ACKs
            try:
                ack_packet, _ = server_socket.recvfrom(1024)
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

udp_server()
