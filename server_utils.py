from logger import Logger
import os
import ssl
import smtplib
from email.message import EmailMessage
import hashlib
import json
from filelock import FileLock
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

UPLOAD_FOLDER = 'STORED_DATA'


def send_verification_email(email, subject, body):
    """
    Sends a verification email with a provided code to a specified email address.
    :param email:
    :param subject:
    :param body:
    :return:
    """
    sender = 'nimbus.mail.ver@gmail.com'
    sender_password = ""
    receiver = email

    em = EmailMessage()
    em["From"] = sender
    em["To"] = receiver
    em["Subject"] = subject
    em.set_content(body)
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
        smtp.login(sender, sender_password)
        smtp.sendmail(sender, receiver, em.as_string())
        print("email sent")
        Logger.log_email_sent(email, subject)


def read_file_content(file_path):
    """
    Reads the content of a file in binary mode.
    param file_path: The path to the file to be read.
    :return: (bytes) The content of the file.
    """
    try:
        with open(file_path, 'rb') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        Logger.log_error(f"File '{file_path}' not found.")
    except PermissionError as e:
        print(f"Permission denied when reading file '{file_path}': {e}")
        Logger.log_error(f"Permission denied when reading file '{file_path}': {e}")
    except OSError as e:
        print(f"Error reading file '{file_path}': {e}")
        Logger.log_error(f"Error reading file '{file_path}': {e}")



def print_bytes(bytes_value):
    """
    Converts a byte value into a human-readable format
    :param bytes_value:
    :return: string that contain the size and suffix
    """
    suffixes = ['B', 'KB', 'MB', 'GB']
    suffix_index = 0

    while bytes_value >= 1024 and suffix_index < len(suffixes) - 1:
        bytes_value /= 1024.0
        suffix_index += 1

    print(f"{bytes_value:.2f} {suffixes[suffix_index]}")


def get_folder_size(folder_path):
    """
    get the sum size for all the files within a folder
    :param folder_path:
    :return:
    """
    # Convert folder_path to a string
    folder_path = str(folder_path)
    total_size = 0
    # Walk through all files and subdirectories in the specified folder
    for dir_path, dir_names, filenames in os.walk(folder_path):
        for filename in filenames:
            # Get the full path of the file
            file_path = os.path.join(dir_path, filename)
            # Ensure file_path is a string
            file_path = str(file_path)
            # Add the size of the file to the total size
            total_size += os.path.getsize(file_path)
    return total_size


def check_file_exists(username, filename):
    """
    Checks if a file or directory exists for a given user in the upload folder.
    :param username: (str) The username associated with the folder.
    :param filename: (str) The name of the file or directory to check.
    :return: (bool) True if the file or directory exists, False otherwise.
    """
    user_folder = os.path.join(UPLOAD_FOLDER, username)
    file_path = os.path.join(user_folder, filename)
    return os.path.isfile(file_path) or os.path.isdir(file_path)



def is_valid_password(password):
    """
    check if the password is within the minimum standard
    :param password:
    :return:
    """
    # Check if password has at least 6 characters and a number
    if len(password) < 6:
        return False
    has_number = any(char.isdigit() for char in password)
    return has_number


def is_valid_email(email):
    """
    Validates an email address by checking its structure.
    :param email: (str) The email address to validate.
    :return: (bool) True if the email address is valid, False otherwise.
    """
    if '@' not in email or '.' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    local_part, domain_part = parts
    if not local_part or not domain_part:
        return False
    if ' ' in local_part or ' ' in domain_part:
        return False
    domain_parts = domain_part.split('.')
    if len(domain_parts) < 2:
        return False
    for part in domain_parts:
        if not part:
            return False
    return True


def password_hashing(plaintext_password, salt):
    """
    Generates a hashed password using PBKDF2 with HMAC-SHA256.
    :param plaintext_password: (str)
    :param salt: (bytes)
    :return: (bytes) the password after hashing
    """
    # Derive the encryption key using PBKDF2 with the plaintext password and salt_encryption
    encryption_key = hashlib.pbkdf2_hmac('sha256', plaintext_password.encode(), salt, 100000)
    return encryption_key


def create_folder(username):
    """
    create a folder within the stored_data folder for a given username
    :param username:
    :return:
    """
    try:
        # Create a new directory
        os.mkdir(F"{UPLOAD_FOLDER}/{username}")
        print(f"Folder '{username}' created successfully.")
    except OSError as error:
        Logger.log_error(f"{username} Creation of the folder failed")
        print(f"Creation of the folder '{username}' failed: {error}")


def create_json(username):
    """
    create the json file for each user that saves the iv
    :param username:
    :return:
    """
    try:
        user_folder = os.path.join(UPLOAD_FOLDER, username)
        json_file_path = os.path.join(user_folder, "encryptions_iv.json")
        lock_file_path = json_file_path + ".lock"  # Path for the lock file

        # Check if the JSON file already exists
        if not os.path.exists(json_file_path):
            # Create an empty dictionary to store the JSON data
            json_data = {}

            # Create the lock file
            open(lock_file_path, 'a').close()

            # Write the empty dictionary to the JSON file
            with open(json_file_path, "w") as json_file:
                json.dump(json_data, json_file)

            print(f"JSON file 'encryptions_iv.json' created successfully for user '{username}'.")
        else:
            print(f"JSON file 'encryptions_iv.json' already exists for user '{username}'.")
    except PermissionError as e:
        Logger.log_error(f"{username} Permission denied when creating JSON file: {e}")
    except OSError as error:
        Logger.log_error(f"{username} Creation of the JSON file failed")
        print(f"Creation of the JSON file 'encryptions_iv.json' failed for user '{username}': {error}")


def add_to_json(username, key, value):
    """
    add to the json file the given key and value
    :param username:
    :param key:
    :param value:
    :return:
    """
    try:
        iv_file_path = os.path.join(UPLOAD_FOLDER, str(username), "encryptions_iv.json")
        lock_file_path = iv_file_path + ".lock"  # Path for the lock file

        with FileLock(lock_file_path):
            # Load the existing IV dictionary from the JSON file
            with open(iv_file_path, 'r') as iv_file:
                iv_dict = json.load(iv_file)

            # Add the new key-value pair to the IV dictionary
            iv_dict[key] = value
            # Write the updated IV dictionary back to the JSON file
            with open(iv_file_path, 'w') as iv_file:
                json.dump(iv_dict, iv_file)

    except FileNotFoundError:
        print(f"JSON file not found for user '{username}'.")
    except PermissionError as e:
        print(f"Permission denied when adding to JSON file: {e}")
        Logger.log_error(f"{username} Permission denied: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        Logger.log_error(f"{username} Error decoding JSON file: {e}")
    except OSError as e:
        print(f"Error adding to JSON file: {e}")
        Logger.log_error(f"{username} Error adding to JSON file: {e}")


def delete_from_json(username, filename):
    """
    delete from the json file the given filename
    :param username:
    :param filename:
    :return:
    """
    try:
        iv_file_path = os.path.join(UPLOAD_FOLDER, str(username), "encryptions_iv.json")
        lock_file_path = iv_file_path + ".lock"  # Path for the lock file

        with FileLock(lock_file_path):
            # Load the existing IV dictionary from the JSON file
            with open(iv_file_path, 'r') as iv_file:
                iv_dict = json.load(iv_file)

            # Check if the filename exists as a key in the IV dictionary
            if filename in iv_dict:
                del iv_dict[filename]
                # Write the updated IV dictionary back to the JSON file
                with open(iv_file_path, 'w') as iv_file:
                    json.dump(iv_dict, iv_file)
            else:
                print(f"{filename} not found in the JSON file.")

    except FileNotFoundError:
        print(f"JSON file not found for user '{username}'.")
        Logger.log_error(f"{username} JSON file not found")
    except PermissionError as e:
        print(f"Permission denied when deleting from JSON file: {e}")
        Logger.log_error(f"{username} Permission denied: {e}")
    except OSError as e:
        print(f"Error deleting from JSON file: {e}")
        Logger.log_error(f"{username} Error deleting from JSON file: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        Logger.log_error(f"{username} Error decoding JSON file: {e}")


def encrypt_file(username, file_path, encryption_key):
    """
    encrypt the content of a given file with a given AES key
    :param username:
    :param file_path:
    :param encryption_key:
    :return:
    """
    try:
        # Read the file content
        with open(file_path, 'rb') as file:
            file_content = file.read()
        # Generate a random IV
        iv = os.urandom(16)
        # Create an AES cipher object
        cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
        # Encrypt the file content
        encrypted_content = cipher.encrypt(pad(file_content, AES.block_size))
        # Write the encrypted content back to the file
        with open(file_path, 'wb') as file:
            file.write(encrypted_content)
        add_to_json(username, file_path, base64.b64encode(iv).decode('utf-8'))
        print(f"File '{file_path}' encrypted successfully.")

    except PermissionError as e:
        print(f"Permission denied when encrypting file: {e}")
        Logger.log_error(f"{username} Permission denied: {e}")
    except ValueError as e:
        print(f"Error padding file content for encryption: {e}")
        Logger.log_error(f"{username} Error padding file content for encryption: {e}")
    except OSError as e:
        print(f"Error encrypting file: {e.strerror}")
        Logger.log_error(f"{username} Error encrypting file: {e}")


def encrypt_folder(username, folder_path, encryption_key):
    """
    encrypt each file within a folder using a stack and the encrypt_file function
    :param username:
    :param folder_path:
    :param encryption_key:
    :return:
    """
    # Create a stack to store directories to traverse
    stack = [folder_path]
    # Iterate until the stack is empty
    while stack:
        # Get the current directory from the stack
        current_dir = stack.pop()
        # Get the list of files and directories in the current directory
        items = os.listdir(current_dir)
        # Iterate over each item in the current directory
        for item in items:
            # Get the full path of the item
            item_path = os.path.join(current_dir, item)
            # Check if the item is a file
            if os.path.isfile(item_path):
                # Print the file name
                print(item_path)
                encrypt_file(username, item_path, encryption_key)  # encrypt the file
            # Check if the item is a directory
            elif os.path.isdir(item_path):
                # Add the subdirectory to the stack for traversal
                stack.append(item_path)


def decrypt_file(username, file_path, encryption_key):
    """
    decrypt the content of a given file with a given AES key
    :param username:
    :param file_path:
    :param encryption_key:
    :return:
    """
    try:
        # Read the encrypted file content
        with open(file_path, 'rb') as file:
            encrypted_content = file.read()

        # Load the IV dictionary from the JSON file
        iv_file_path = os.path.join(UPLOAD_FOLDER, username, "encryptions_iv.json")
        lock_file_path = iv_file_path + ".lock"  # Path for the lock file

        with FileLock(lock_file_path):
            with open(iv_file_path, 'r') as iv_file:
                iv_dict = json.load(iv_file)
        # Get the IV for the current file from the dictionary
        iv_base64 = iv_dict.get(file_path)

        if iv_base64:
            iv = base64.b64decode(iv_base64)
            # Create an AES cipher object
            cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
            # Decrypt the file content
            decrypted_content = unpad(cipher.decrypt(encrypted_content), AES.block_size)
            # Write the decrypted content back to the file
            with open(file_path, 'wb') as file:
                file.write(decrypted_content)
            print(f"File '{file_path}' decrypted successfully.")
        else:
            print(f"IV not found for file '{file_path}'.")

    except PermissionError as e:
        print(f"Permission denied when decrypting file: {e}")
        Logger.log_error(f"{username} Permission denied: {e}")
    except ValueError as e:
        print(f"Error padding file content for decrypting: {e}")
        Logger.log_error(f"{username} Error padding file content for decrypting: {e}")
    except OSError as e:
        print(f"Error decrypting file: {e.strerror}")
        Logger.log_error(f"{username} Error decrypting file: {e}")


def decrypt_folder(username, folder_path, encryption_key):
    """
    decrypt each file within a folder using a stack and the decrypt_file function
    :param username:
    :param folder_path:
    :param encryption_key:
    :return:
    """
    # Create a stack to store directories to traverse
    stack = [folder_path]

    # Iterate until the stack is empty
    while stack:
        # Get the current directory from the stack
        current_dir = stack.pop()
        # Get the list of files and directories in the current directory
        items = os.listdir(current_dir)
        # Iterate over each item in the current directory
        for item in items:
            # Get the full path of the item
            item_path = os.path.join(current_dir, item)
            # Check if the item is a file
            if os.path.isfile(item_path):
                # Print the file name
                print(item_path)
                decrypt_file(username, item_path, encryption_key)  # encrypt the file

            # Check if the item is a directory
            elif os.path.isdir(item_path):
                # Add the subdirectory to the stack for traversal
                stack.append(item_path)
