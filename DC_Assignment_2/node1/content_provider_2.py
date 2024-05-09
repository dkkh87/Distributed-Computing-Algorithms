import socket
import hashlib
import os
import sys
import RicartAgrawala
import time

#RicartAgrawala.MutexInit(('127.0.0.1', 5551), 1, 'proc_a', ((('127.0.0.1', 5552))), ('proc_b'), 1)
RicartAgrawala.MutexInit(('172.31.1.99', 5552), 2, 'proc_b', ((('172.31.3.212', 5553), ('172.31.1.99', 5551))), ('proc_c', 'proc_a'), 2)
#RicartAgrawala.MutexInit(('172.31.1.99', 5552), 2, 'proc_b', ((('172.31.1.99', 5551))), ('proc_a'), 1)

# Define server address and port
SERVER_ADDRESS = '172.31.6.106'  # Replace with the actual IP address of the server
SERVER_PORT = 8889


# Function to create lock file on server
def create_lock():
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lock_socket.connect((SERVER_ADDRESS, SERVER_PORT))
    lock_socket.send("CREATE_LOCK".encode())
    response = lock_socket.recv(1024).decode()
    lock_socket.close()
    return response

# Function to remove lock file on server
def remove_lock():
    remove_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remove_socket.connect((SERVER_ADDRESS, SERVER_PORT))
    remove_socket.send("REMOVE_LOCK".encode())
    response = remove_socket.recv(1024).decode()
    remove_socket.close()
    return response

# Function to send file to server
def send_file_to_server(filename, content):
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to server
        client_socket.connect((SERVER_ADDRESS, SERVER_PORT))

        # Calculate content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()

        # Send write request to server
        request = f"WRITE {filename} {content_hash} {content}"
        client_socket.send(request.encode())

        # Receive response from server
        response = client_socket.recv(1024).decode()
        print(f"Server Response: {response}")

    finally:
        # Remove lock file on server
        remove_response = remove_lock()

# Example usage
if __name__ == "__main__":
    for x in range(3):
        try:
            filename = input("Enter the filename: ")
            content = input("Enter the content: ")
            
            # Send file to server
            time.sleep(30)
            RicartAgrawala.MutexLock('Mutex')
            tb = time.time()
            print ("======== Critical section begin. timestamp is " + str(tb) + " ========")
            send_file_to_server(filename, content)
            te = time.time()
            print ("======== Critical section finished. timestamp is " + str(te) + " ========")
            RicartAgrawala.MutexUnlock('Mutex')
            time.sleep(15)
            RicartAgrawala.MutexExit()
        except Exception as e:
            print(f"An error occurred: {e}")
    exit()