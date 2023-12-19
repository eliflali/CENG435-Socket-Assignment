import socket
import json
import struct
import sys

def send_command(host, port):
    # Create a TCP/IP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        # Connect to the server
        sock.connect((host, port))
        print(f"Connected to {host} on port {port}")

        while True:
            # Get command from user
            user_input = input("Enter command (or 'close connection' to exit): ")

            # Check if the user wants to close the connection
            

            # Serialize the command to a JSON string and convert to bytes
            command_json = json.dumps({"command": user_input})
            command_bytes = command_json.encode('utf-8')
            print(command_bytes)

            # Calculate the size of the command
            command_size = len(command_bytes)

            # Pack the size in a 4-byte big-endian format
            packed_size = struct.pack('!I', command_size)

            # Send the size of the command followed by the command itself
            sock.sendall(packed_size)
            sock.sendall(command_bytes)
            print(f"Command sent: {command_json}")

            if user_input.lower() == "close connection":
                print("Closing connection.")
                break
                
            # Wait for the response
            response_size_raw = sock.recv(4)
            if not response_size_raw:
                print("No response from server.")
                return

            response_size = struct.unpack('!I', response_size_raw)[0]
            response = sock.recv(response_size).decode('utf-8')
            print(f"Response received: {response}")
            

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != '--port':
        print("Usage: python3 client.py --port <port_number>")
        sys.exit(1)

    port = int(sys.argv[2])

    # Server details
    server_host = 'localhost'
    server_port = port

    # Send the command
    send_command(server_host, server_port)
