import os

UPLOAD_FOLDER = 'STORED_DATA'


class ClientClass:
    def __init__(self, username, email, client_socket, aes_cipher, file_encryption_key):
        self.username = username
        self.folder = os.path.join(UPLOAD_FOLDER, username)
        self.email = email
        self.socket = client_socket
        self.aes = aes_cipher
        self.files_key = file_encryption_key

    def get_username(self):
        return self.username

    def get_folder(self):
        return self.folder

    def get_email(self):
        return self.email

    def get_socket(self):
        return self.socket

    def get_aes(self):
        return self.aes

    def get_files_key(self):
        return self.files_key
