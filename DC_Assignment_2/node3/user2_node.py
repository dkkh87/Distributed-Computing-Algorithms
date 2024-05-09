import socket
import os

# Define server address and port
SERVER_ADDRESS = '172.31.6.106'  # Replace 'server_ip_address' with the actual IP address of the server
SERVER_PORT = 8889

# Define the folder to save downloaded files
DOWNLOAD_FOLDER = 'user2_files'

# Create logs directory if it doesn't exist
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Function to send fetch request to server and download file
def send_fetch_request(filename):
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to server
    client_socket.connect((SERVER_ADDRESS, SERVER_PORT))
    print("Connected to server.")

    try:
        # Send fetch request to server
        request = f"FETCH {filename}"
        client_socket.send(request.encode())
        print("Fetch request sent to server.")

        # Receive response from server
        response = client_socket.recv(1024).decode()
        print("Received response from server.")

        if response == "FILE_NOT_FOUND":
            print(f"Error: File '{filename}' not found on the server.")
        else:
            # Save file content to local file in download folder
            download_folder = os.path.join(os.path.dirname(__file__), DOWNLOAD_FOLDER)
            os.makedirs(download_folder, exist_ok=True)
            local_file_path = os.path.join(download_folder, filename)
            with open(local_file_path, 'w') as file:
                file.write(response)

            print(f"File '{filename}' downloaded to '{download_folder}' successfully.")

    finally:
        client_socket.close()

# Example usage: send fetch requests to download files from server to local folder
if __name__ == "__main__":
    filename = input("Enter the filename to fetch from the server: ")
    print(f"Fetching '{filename}' from the server...")
    send_fetch_request(filename)