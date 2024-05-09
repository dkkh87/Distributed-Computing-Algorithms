import socket
import os
import threading
import logging
import json

# Define server address and port
SERVER_ADDRESS = '0.0.0.0'  # Listen on all available interfaces
SERVER_PORT = 8889

# Define the directory where files are stored on the server
SERVER_STORAGE_DIR = 'server_storage'

# Define the directory for log files
LOGS_DIR = 'server_logs'

# Define the file to store the mapping of original filenames to hashed content
FILENAME_MAPPING_FILE = 'filename_mapping.json'

# Define the file to store the mapping of shortcut filenames to parent filenames
SHORTCUT_MAPPING_FILE = 'shortcut_mapping.json'

# Lock file name
LOCK_FILE = 'content_provider_lock.txt'

# Create logs directory if it doesn't exist
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Configure logging
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_FILE = os.path.join(LOGS_DIR, 'server_log.txt')
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format=LOG_FORMAT)

# Initialize a dictionary to store file locks
file_locks = {}
# Initialize a dictionary to store filename mappings
filename_mapping = {}
# Initialize a dictionary to store shortcut mappings
shortcut_mapping = {}

# Load existing filename mappings from file
if os.path.exists(FILENAME_MAPPING_FILE):
    with open(FILENAME_MAPPING_FILE, 'r') as file:
        filename_mapping = json.load(file)
        logging.info("filename map")
        logging.info(shortcut_mapping)
        logging.info("filename map")

# Load existing shortcut mappings from file
if os.path.exists(SHORTCUT_MAPPING_FILE):
    with open(SHORTCUT_MAPPING_FILE, 'r') as file:
        shortcut_mapping = json.load(file)
        logging.info("shortcut map")
        logging.info(filename_mapping)
        logging.info("shortcut map")

# Function to handle client requests
def handle_client(client_socket, address):
    logging.info(f"Connected to {address}")

    while True:
        # Receive request from client
        request = client_socket.recv(1024).decode()

        if not request:
            break

        logging.info(f"Received request: {request}")

        # Handle write request
        if request.startswith("WRITE"):
            _, filename, content_hash, content = request.split(" ", 3)

            # Acquire lock for the file
            file_lock = file_locks.setdefault(filename, threading.Lock())
            file_lock.acquire()

            try:
                # Check if file already exists with same name and content
                if filename in filename_mapping and filename_mapping[filename] == content_hash:
                    response = "FILE_EXISTS"
                else:
                    # Check if file already exists with same content but different name
                    existing_filename = next((key for key, value in filename_mapping.items() if value == content_hash), None)
                    if existing_filename:
                        # Create shortcut mapping
                        shortcut_mapping[filename] = existing_filename
                        with open(SHORTCUT_MAPPING_FILE, 'w') as file:
                            json.dump(shortcut_mapping, file)
                        response = "SHORTCUT_CREATED"
                    else:
                        # Write file content to server storage using original filename
                        file_path = os.path.join(SERVER_STORAGE_DIR, filename)
                        
                        # Check if file already exists with same name but different content
                        if os.path.exists(file_path):
                            with open(file_path, 'r') as file:
                                existing_content = file.read()

                            if existing_content != content:
                                # Update file content if different
                                with open(file_path, 'w') as file:
                                    file.write(content)
                                response = "FILE_UPDATED"
                            else:
                                response = "FILE_EXISTS"
                        else:
                            # File does not exist, write new content
                            with open(file_path, 'w') as file:
                                file.write(content)
                            response = "FILE_WRITTEN"

                        # Update filename mapping
                        filename_mapping[filename] = content_hash

                        # Save filename mapping to file
                        with open(FILENAME_MAPPING_FILE, 'w') as mapping_file:
                            json.dump(filename_mapping, mapping_file)

            finally:
                # Release the lock
                file_lock.release()

            # Send response to client
            client_socket.send(response.encode())
            logging.info(f"Sent response: {response}")

        # Handle fetch request
        elif request.startswith("FETCH"):
            _, filename = request.split(" ", 1)
            content_hash = shortcut_mapping.get(filename, None)

            if content_hash:
                # Check if the file is a shortcut
                parent_filename = shortcut_mapping.get(filename, None)
                if parent_filename:
                    # Send content of parent file
                    file_path = os.path.join(SERVER_STORAGE_DIR, parent_filename)
                    # Acquire lock for the file
                    file_lock = file_locks.setdefault(parent_filename, threading.Lock())
                    file_lock.acquire()
                else:
                    # File not found in shortcut mapping
                    client_socket.send("FILE_NOT_FOUND".encode())
                    logging.info("Sent file not found response to client.")
                    return  # Exit function

            else:
                # Check if the file exists in filename mapping
                content_hash = filename_mapping.get(filename, None)
                if content_hash:
                    # Send content of original file
                    file_path = os.path.join(SERVER_STORAGE_DIR, filename)
                    # Acquire lock for the file
                    file_lock = file_locks.setdefault(filename, threading.Lock())
                    file_lock.acquire()
                else:
                    # File not found in filename mapping
                    client_socket.send("FILE_NOT_FOUND".encode())
                    logging.info("Sent file not found response to client.")
                    return  # Exit function

            try:
                # Read file content from server storage
                with open(file_path, 'r') as file:
                    file_content = file.read()

                # Send file content to client
                client_socket.send(file_content.encode())
                logging.info("Sent file content to client.")

            finally:
                # Release the lock
                file_lock.release()

        # Handle lock-related requests
        elif request == "CREATE_LOCK":
            if not os.path.exists(LOCK_FILE):
                with open(LOCK_FILE, 'w') as lock_file:
                    lock_file.write("Lock")
                client_socket.send("LOCK_CREATED".encode())
            else:
                client_socket.send("LOCK_ALREADY_EXISTS".encode())

        elif request == "REMOVE_LOCK":
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
                client_socket.send("LOCK_REMOVED".encode())
            else:
                client_socket.send("LOCK_ALREADY_REMOVED".encode())

        else:
            # Invalid request
            client_socket.send("INVALID_REQUEST".encode())
            logging.warning("Received invalid request.")

    client_socket.close()
    logging.info("Connection closed.")

# Function to start the server
def start_server():
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the server address and port
    server_socket.bind((SERVER_ADDRESS, SERVER_PORT))

    # Listen for incoming connections
    server_socket.listen(5)
    logging.info("Server is listening...")

    while True:
        # Accept incoming connection
        client_socket, address = server_socket.accept()

        # Handle client in a new thread
        client_thread = threading.Thread(target=handle_client, args=(client_socket, address))
        client_thread.start()

# Start the server
if __name__ == "__main__":
    if not os.path.exists(SERVER_STORAGE_DIR):
        os.makedirs(SERVER_STORAGE_DIR)
    start_server()