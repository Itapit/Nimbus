import socket
import threading
from datetime import datetime, timedelta
import os
import sqlite3
import protocol
import zipfile
import shutil
import random
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from logger import Logger
from client_class import ClientClass
import server_admin
import server_utils

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
UPLOAD_FOLDER = 'STORED_DATA'
MAXIMUS_SIZE_PER_CLIENT = 1073741824


def create_folder_by_user(create_folder_dict, client_cl):
    """
    responsible for creating a new folder when a user request it
    :param create_folder_dict:
    :param client_cl:
    :return:
    """
    username = client_cl.get_username()
    aes_cipher = client_cl.get_aes()
    client_socket = client_cl.get_socket()
    response_dict = {}

    try:
        folder_name = create_folder_dict.get("folder_name")
        user_folder = os.path.join(UPLOAD_FOLDER, str(username))
        new_folder_path = os.path.join(user_folder, folder_name)

        if ".." in folder_name:   # prevent Directory traversal attack
            response_dict = {"command": "response", "msg": "Invalid folder name"}
            client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
            Logger.log_error(f"{username} Attempted directory traversal: {folder_name}")
            return

        if not os.path.exists(new_folder_path):
            os.makedirs(new_folder_path)
            response_dict = {"command": "response", "msg": "Folder created successfully"}
        else:
            response_dict = {"command": "response", "msg": "Folder already exists"}

    except PermissionError as e:
        response_dict = {"command": "response", "msg": f"Permission denied when creating folder: {e}"}
        Logger.log_error(f"{username} Permission denied: {e}")
    except OSError as e:
        response_dict = {"command": "response", "msg": f"Error creating folder: {e}"}
        Logger.log_error(f"{username} Error creating folder: {e}")
    finally:
        client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))


def receive_file(files_dict, client_cl):
    """
    responsible for receiving a new file when a user request it
    :param files_dict:
    :param client_cl:
    :return:
    """
    username = client_cl.get_username()
    aes_cipher = client_cl.get_aes()
    encryption_key = client_cl.get_files_key()
    try:
        file_name = files_dict.get("file_name")[5:]
        file_type = files_dict.get("file_type")
        file_content = files_dict.get("file_Content")

        if ".." in file_name or ".." in file_type:   # prevent Directory traversal attack
            return

        # Convert username to string for path construction
        username_str = str(username)

        # Combine file_name and file_type for proper path construction
        complete_file_name = f"{file_name}{file_type}"  # Include file type with dot
        file_path = os.path.join(UPLOAD_FOLDER, username_str, complete_file_name)
        counter = 1
        base_name, extension = os.path.splitext(complete_file_name)
        while os.path.exists(file_path):
            new_file_name = f"{base_name}({counter}){extension}"
            file_path = os.path.join(UPLOAD_FOLDER, username_str, new_file_name)
            counter += 1

        folder_size = server_utils.get_folder_size(f"{UPLOAD_FOLDER}//{username}")
        if folder_size + len(file_content) > MAXIMUS_SIZE_PER_CLIENT:
            print("User folder size reached its max storage size of 1GB")
        else:
            with open(file_path, 'wb') as file:
                file.write(file_content)

        server_utils.encrypt_file(username, file_path, encryption_key)
        Logger.log_upload(username, file_name)

    except PermissionError as e:
        print(f"Permission denied when receiving file: {e}")
        Logger.log_error(f"{username} permission denied: {e}")
    except FileNotFoundError:
        print(f"File not found when receiving file")
        Logger.log_error(f"{username} file not found when receiving")
    except OSError as e:
        print(f"Error receiving file: {e}")
        Logger.log_error(f"{username} error receiving file: {e}")


def receive_folder(folders_dict, client_cl):
    """
    Receives, processes, and stores an uploaded folder from a user.
    :param folders_dict:
    :param client_cl:
    :return:
    """
    username = client_cl.get_username()
    aes_cipher = client_cl.get_aes()
    encryption_key = client_cl.get_files_key()
    try:
        folder_name = folders_dict.get("folder_name")[:-4]
        folder_name = folder_name[5:]
        folder_content = folders_dict.get("folder_content")
        if ".." in folder_name:   # prevent Directory traversal attack
            return
        # Convert username to string for path construction
        username_str = str(username)
        # Create a temporary file path to save the ZIP file
        temp_folder_path = os.path.join(UPLOAD_FOLDER, username_str, folder_name)
        counter = 1
        base_name, extension = os.path.splitext(folder_name)
        # Added a loop to handle folder name conflicts
        while os.path.exists(temp_folder_path):
            new_folder_name = f"{base_name}({counter}){extension}"
            temp_folder_path = os.path.join(UPLOAD_FOLDER, username_str, new_folder_name)
            counter += 1
        final_folder_path = temp_folder_path
        temp_folder_path = temp_folder_path + ".zip"
        folder_size_user = server_utils.get_folder_size(f"{UPLOAD_FOLDER}//{username}")
        if folder_size_user + len(folder_content) > MAXIMUS_SIZE_PER_CLIENT:
            print("User folder size reached its max storage size of 1GB")
        else:
            # Save the ZIP file temporarily
            with open(temp_folder_path, 'wb') as file:
                file.write(folder_content)

            # Create a path for the unzipped folder (remove the .zip extension)
            unzipped_folder_path = temp_folder_path[:-4]
            # Unzip the file to the specified folder
            print(F"temp_folder_path: {temp_folder_path}")
            print(F"unzipped_folder_path: {unzipped_folder_path}")
            with zipfile.ZipFile(temp_folder_path, 'r') as zip_ref:
                for member in zip_ref.infolist():
                    extracted_path = zip_ref.extract(member, unzipped_folder_path)
                    if member.is_dir():
                        os.makedirs(extracted_path, exist_ok=True)

            # Remove the temporary ZIP file
            os.remove(temp_folder_path)

            server_utils.encrypt_folder(username, final_folder_path, encryption_key)

    except PermissionError as e:
        print(f"Permission denied when receiving folder: {e}")
        Logger.log_error(f"{username} permission denied: {e}")
    except zipfile.BadZipFile as e:
        print(f"Bad ZIP file when receiving folder: {e}")
        Logger.log_error(f"{username} bad ZIP file: {e}")
    except FileNotFoundError:
        print(f"File not found when receiving folder")
        Logger.log_error(f"{username} file not found when receiving folder")
    except OSError as e:
        print(f"Error receiving folder: {e}")
        Logger.log_error(f"{username} error receiving folder: {e}")


def refresh(refresh_dict, client_cl):
    """
    responsible for sending the files withing a folder when a user request it
    :param refresh_dict:
    :param client_cl:
    :return:
    """
    username = client_cl.get_username()
    aes_cipher = client_cl.get_aes()
    client_socket = client_cl.get_socket()
    try:
        path = refresh_dict.get("path")[4:]
        if path != "":
            path = f"//{path}"
        user_folder = f"{UPLOAD_FOLDER}//{username}{path}"
        files_dict = {}  # Create an empty dictionary for files
        files_list = []
        for content_name in os.listdir(user_folder):
            content_path = os.path.join(user_folder, content_name)
            is_file = os.path.isfile(content_path)  # Check if it's a file
            files_list.append((content_name, "file" if is_file else "folder"))

        tuples_to_remove = [("encryptions_iv.json", "file"), ("encryptions_iv.json.lock", "file")]
        for tuple_item in tuples_to_remove:
            if tuple_item in files_list:
                files_list.remove(tuple_item)

        # Calculate the total number of pages
        rows = refresh_dict.get("rows")
        cols = refresh_dict.get("cols")
        items_per_page = rows * cols
        total_pages = (len(files_list) + items_per_page - 1) // items_per_page

        # Get the files for the current page
        page = refresh_dict.get("page", 1)
        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page
        for file_name, file_type in files_list[start_index:end_index]:
            files_dict[file_name] = file_type

        folder_size = server_utils.get_folder_size(user_folder)

        response_dict = {"command": "response", "file_size": folder_size, "files": files_dict, "total_pages": total_pages}
        client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))

    except PermissionError as e:
        print(f"Permission denied when refreshing folder: {e.strerror}")
        Logger.log_error(f"{username} permission denied: {e.strerror}")
    except FileNotFoundError:
        print(f"File not found when refreshing folder")
        Logger.log_error(f"{username} file not found when refreshing folder")
    except OSError as e:
        print(f"Error refreshing folder: {e.strerror}")
        Logger.log_error(f"{username} error refreshing folder: {e.strerror}")


def delete(delete_dict, client_cl):
    """
    responsible for deleting a file/folder when a user request it
    :param delete_dict:
    :param client_cl:
    :return:
    """
    username = client_cl.get_username()
    aes_cipher = client_cl.get_aes()
    client_socket = client_cl.get_socket()

    try:
        file_names = delete_dict.get("files")
        for filename in file_names:
            if filename == "encryptions_iv.json":  # Prevent deletion of the "encryptions_iv.json" file
                continue
            if not server_utils.check_file_exists(username, filename[5:]):  # prevent Directory traversal attack
                continue

            filepath = os.path.join(UPLOAD_FOLDER, str(username), filename[5:])

            if os.path.isfile(filepath):
                os.remove(filepath)
                print(f"Deleted file: {filename}")
                Logger.log_delete(username, filename)
                server_utils.delete_from_json(username, filepath)

            elif os.path.isdir(filepath):
                try:
                    shutil.rmtree(filepath)
                    print(f"Deleted folder: {filename}")
                    Logger.log_delete(username, filename)

                    # Remove the IVs of all files in the deleted folder from the JSON file
                    iv_file_path = os.path.join(UPLOAD_FOLDER, str(username), "encryptions_iv.json")
                    with open(iv_file_path, 'r') as iv_file:
                        iv_dict = json.load(iv_file)

                    # Iterate over the keys (file paths) in the IV dictionary
                    for key in list(iv_dict.keys()):
                        # Check if the key starts with the folder path and has an additional path separator
                        if key.startswith(filepath + os.path.sep):
                            server_utils.delete_from_json(username, key)

                except PermissionError as e:
                    print(f"Error deleting folder '{filename}': {e}")
                    Logger.log_error(f"{username} PermissionError: {filename}")
            else:
                print(f"File not found: {filename}")
                Logger.log_error(f"{username} File not found: {filename}")

    except PermissionError as e:
        print(f"Permission denied when deleting file/folder: {e}")
        Logger.log_error(f"{username} permission denied: {e}")
    except FileNotFoundError:
        print(f"File not found when deleting file/folder")
        Logger.log_error(f"{username} file not found when deleting file/folder")
    except OSError as e:
        print(f"Error deleting file/folder: {e}")
        Logger.log_error(f"{username} error deleting file/folder: {e}")


def download(download_dict, client_cl):
    """
    responsible for sending a folder/file when a user request it
    :param download_dict:
    :param client_cl:
    :return:
    """
    username = client_cl.get_username()
    aes_cipher = client_cl.get_aes()
    client_socket = client_cl.get_socket()
    encryption_key = client_cl.get_files_key()
    try:
        file_names = download_dict.get("files")
        if not file_names:
            response_dict = {"command": "response", "files": "no files selected"}
            client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
            return

        file_data = []
        for file in file_names:
            if not server_utils.check_file_exists(username, file[5:]):  # prevent Directory traversal attack
                continue

            file_path = os.path.join(UPLOAD_FOLDER, str(username), file[5:])
            if os.path.isfile(file_path):

                server_utils.decrypt_file(username, file_path, encryption_key)  # decrypt the file before reading

                file_name, file_type = os.path.splitext(os.path.basename(file_path))
                file_content = server_utils.read_file_content(file_path)
                if len(file_content) < MAXIMUS_SIZE_PER_CLIENT:
                    file_data.append({"file_name": file_name, "file_type": file_type, "file_Content": file_content})
                    Logger.log_download(username, file)
                else:
                    print("file too large")
                    Logger.log_error(f"{username} File too large: {file_path}")

                server_utils.encrypt_file(username, file_path, encryption_key)

            elif os.path.isdir(file_path):

                server_utils.decrypt_folder(username, file_path, encryption_key)

                # Handle the case when the user wants to download a folder
                zip_file_name = os.path.basename(file_path) + ".zip"
                temp_zip_file_path = os.path.join(UPLOAD_FOLDER, str(username), zip_file_name)

                # Create a zip file containing the existing folder
                # Create a zip file containing the folder
                with zipfile.ZipFile(temp_zip_file_path, 'w') as zip_file:
                    for root, dirs, files in os.walk(file_path):
                        # Add empty directories to the zip file
                        for dir_name in dirs:
                            dir_path_in_zip = os.path.join(root, dir_name)
                            zip_file.write(dir_path_in_zip, os.path.relpath(dir_path_in_zip, file_path))

                            # Add files to the zip file
                        for file1 in files:
                            file_path_in_zip = os.path.join(root, file1)
                            zip_file.write(file_path_in_zip, os.path.relpath(file_path_in_zip, file_path))

                file_content = server_utils.read_file_content(temp_zip_file_path)
                if len(file_content) < MAXIMUS_SIZE_PER_CLIENT:
                    file_data.append({"file_name": zip_file_name, "file_type": "folder", "file_Content": file_content})
                    Logger.log_download(username, file_path)

                else:
                    print("folder too large")
                    Logger.log_error(f"{username} Folder too large: {file_path}")
                # Remove the temporary zip file
                os.remove(temp_zip_file_path)
                server_utils.encrypt_folder(username, file_path, encryption_key)
            else:
                print(f"File not found: {file}")

        response_dict = {"command": "response", "files": file_data}
        client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))

    except PermissionError as e:
        print(f"Permission denied when downloading file/folder: {e}")
        Logger.log_error(f"{username} permission denied: {e}")
    except FileNotFoundError:
        print(f"File not found when downloading file/folder")
        Logger.log_error(f"{username} file not found when downloading file/folder")
    except zipfile.BadZipFile as e:
        print(f"Bad ZIP file when downloading folder: {e}")
        Logger.log_error(f"{username} bad ZIP file: {e}")
    except OSError as e:
        print(f"Error downloading file/folder: {e}")
        Logger.log_error(f"{username} error downloading file/folder: {e}")


def login_signup(client_socket, client_address,  aes_cipher):
    """
    the main function for the login/signup/forgot_pass part
    contains most of the login and calls the function
    :param client_address:
    :param client_socket:
    :param aes_cipher:
    :return:
    """
    max_attempts = 5
    login_attempts = 0
    signup_attempts = 0
    forgot_password_attempts = 0
    changed_password_counter = 0
    verification_code_create = ""
    verification_code_forgot = ""
    is_verified_forgot = False
    account_data_signup_dict = {}
    account_data_forgot_dict = {}

    while True:
        print("waiting for msg")
        login_or_create_dict = protocol.get_message_aes(client_socket, aes_cipher)
        command = login_or_create_dict.get("command")
        print(command)

        if command == "login":
            if login_attempts < max_attempts:
                response, username, is_admin, file_encryption_key, email = login(login_or_create_dict)
                if response == "Login successful" or response == "Admin connected":
                    response_dict = {"command": "response", "msg": response}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
                    return username, is_admin, file_encryption_key, email
                elif response == "Wrong password":
                    login_attempts += 1
                    response_dict = {"command": "response", "msg": f"Wrong password. Attempt {login_attempts}/{max_attempts}"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
                elif response == "User doesn't exist":
                    response_dict = {"command": "response", "msg": response}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
            else:
                response_dict = {"command": "response", "msg": "Too many failed login attempts. Please try again later."}
                client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
                # ban the user ip for 2 minutes for cooldown
                ban_ip_address(client_address[0], "auto")

        elif command == "signup":
            if signup_attempts < max_attempts:
                account_data_signup_dict = login_or_create_dict.copy()
                response, verification_code_create = signup(login_or_create_dict)
                if response == "Code sent":
                    response_dict = {"command": "response", "msg": "Enter code"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
                else:
                    response_dict = {"command": "response", "msg": response}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))

        elif command == "signup_code":
            if signup_attempts < max_attempts:
                response, username, file_encryption_key, email = signup_verify_code(login_or_create_dict, verification_code_create, account_data_signup_dict)
                if response == "Account created":
                    print(f"hello: {username}")
                    response_dict = {"command": "response", "msg": "Account created"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
                    Logger.log_signup(username)
                    return username, False, file_encryption_key, email
                elif response == "Invalid code":
                    signup_attempts += 1
                    response_dict = {"command": "response", "msg": f"Invalid code. Attempt {signup_attempts}/{max_attempts}"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
            else:
                response_dict = {"command": "response", "msg": "Maximum attempts reached. Please try again later."}
                client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))

        elif command == "forgot_password":
            account_data_forgot_dict = login_or_create_dict.copy()
            response, verification_code_forgot = forgot_password(login_or_create_dict)
            if response == "Code sent":
                response_dict = {"command": "response", "msg": "Enter code"}
                client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
            else:
                response_dict = {"command": "response", "msg": response}
                client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))

        elif command == "forgot_password_code":
            if forgot_password_attempts < max_attempts:
                entered_code = login_or_create_dict.get("code")

                if verification_code_forgot == entered_code:
                    is_verified_forgot = True
                    response_dict = {"command": "response", "msg": "Code verified"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
                else:
                    forgot_password_attempts += 1
                    response_dict = {"command": "response",
                                     "msg": f"Invalid code. Attempt {forgot_password_attempts}/{max_attempts}"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
            else:
                response_dict = {"command": "response", "msg": "Maximum attempts reached. Please try again later."}
                client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))

        elif command == "forgot_password_new":
            if is_verified_forgot:
                if changed_password_counter == 0:
                    response = update_password(login_or_create_dict, account_data_forgot_dict)
                    response_dict = {"command": "response", "msg": response, "attempts": "reset"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
                    login_attempts = 0
                    if response == "Password updated successfully":
                        changed_password_counter = 1
                else:
                    response = update_password(login_or_create_dict, account_data_forgot_dict)
                    response_dict = {"command": "response", "msg": response, "attempts": "not reset"}
                    client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))
            else:
                print("error while changing password")

        elif command == "exit":
            print("Client requested exit")
            return "exit", None, None, None
        else:
            print("Invalid command received")
            response_dict = {"command": "response", "msg": "Invalid command received"}
            client_socket.sendall(protocol.send_message_aes(response_dict, aes_cipher))


def login(login_dict):
    """
    responsible for the login of a user
    :param login_dict:
    :return:
    """
    email = login_dict.get("email").upper()
    password = login_dict.get("password")
    users_db = sqlite3.connect("database.db")
    cursor = users_db.cursor()

    try:
        query = "SELECT username, password, salt_key, salt_password FROM Users WHERE email = ?"
        cursor.execute(query, (email,))
        user_data = cursor.fetchall()

        if len(user_data) == 0:
            print("User doesn't exist")
            return "User doesn't exist", None, False, None, None

        username, hashed_pass_db, salt_key, salt_password = user_data[0]
        hashed_pass_bytes = server_utils.password_hashing(password, salt_password)
        hashed_pass = hashed_pass_bytes.hex()

        if hashed_pass == hashed_pass_db:
            print("Login successful")
            query = "SELECT admin FROM Users WHERE username = ?;"
            cursor.execute(query, (username,))
            is_admin = cursor.fetchone()

            if is_admin[0] == 1:
                Logger.log_admin_login(username)
                return "Admin connected", username, True, None, email
            else:
                if not os.path.exists(f"{UPLOAD_FOLDER}//{username}"):
                    server_utils.create_folder(username)
                server_utils.create_json(username)
                Logger.log_login(username)
                file_encryption_key = server_utils.password_hashing(password, salt_key)
                return "Login successful", username, False, file_encryption_key, email
        else:
            return "Wrong password", None, False, None, None

    except sqlite3.Error as e:
        print(f"Error during login: {e}")
        Logger.log_error(f"Error during login: {e}")
        return "Database error", None, False, None, None

    finally:
        if cursor:
            cursor.close()
            users_db.close()


def signup(signup_dict):
    """
    responsible for the first part of the signup
    :param signup_dict:
    :return:
    """
    email = signup_dict.get("email").upper()
    username = signup_dict.get("username").upper()
    password = signup_dict.get("password")

    # Check if password meets requirements
    if not server_utils.is_valid_password(password):
        return "Password doesn't meet requirements\nThe password need to be at least 6 characters and a number", None

    if not server_utils.is_valid_email(email):
        return "Email address is not valid. Please enter a valid email address.", None

    # Connect to the database
    try:
        with sqlite3.connect("database.db") as users_db:
            cursor = users_db.cursor()

            # Check if email already exists
            query = "SELECT 1 FROM Users WHERE (email = ? OR username = ?) LIMIT 1;"
            cursor.execute(query, (email, username))
            if cursor.fetchone():
                return "User already exists", None

            # Send the verification email
            verification_code = '{:06d}'.format(random.randint(100000, 999999))
            server_utils.send_verification_email(email, 'Verification Code', f'Your verification code is: {verification_code}')
            return "Code sent", verification_code

    except sqlite3.Error as e:
        # database errors
        Logger.log_error(f"{username} signup error: {e}")
        return f"Database error: {str(e)}", None


def signup_verify_code(verification_dict, verification_code, account_data_dict):
    """
    responsible for the second part of the signup
    the verification code part
    :param verification_dict:
    :param verification_code:
    :param account_data_dict:
    :return:
    """
    email = account_data_dict.get("email").upper()
    username = account_data_dict.get("username").upper()
    password = account_data_dict.get("password")
    entered_code = verification_dict.get("code")
    try:
        with sqlite3.connect("database.db") as users_db:
            cursor = users_db.cursor()

            if verification_code == entered_code:
                # Generate salt and hash password
                salt_password = os.urandom(32)
                salt_key = os.urandom(32)

                hashed_pass_bytes = server_utils.password_hashing(password, salt_password)
                hashed_pass = hashed_pass_bytes.hex()
                # Insert new user into the database
                query = "INSERT INTO Users (username, password, email, salt_password, salt_key, admin) VALUES (?,?,?,?,?,?)"
                cursor.execute(query, (username, hashed_pass, email, sqlite3.Binary(salt_password), sqlite3.Binary(salt_key), 0))
                users_db.commit()
                server_utils.create_folder(username)
                server_utils.create_json(username)
                file_encryption_key = server_utils.password_hashing(password, salt_key)
                return "Account created", username, file_encryption_key, email
            else:
                return "Invalid code", username, None, None

    except sqlite3.Error as e:
        # Handle database errors
        Logger.log_error(f"{username} signup_verify_code error: {e}")
        return f"Database error: {str(e)}", None, None, None


def forgot_password(forgot_pass_dict):
    """
    responsible for the first part of changing a user password
    :param forgot_pass_dict:
    :return:
    """
    email = forgot_pass_dict.get("email").upper()

    try:
        with sqlite3.connect("database.db") as users_db:
            cursor = users_db.cursor()
            query = "SELECT 1 FROM Users WHERE email = ? LIMIT 1;"
            cursor.execute(query, (email,))
            if not cursor.fetchone():
                return "Email not found", None
    except sqlite3.Error as e:
        Logger.log_error(f"{email} forgot_password error: {e}")
        return f"Database error: {str(e)}", None

    verification_code = '{:06d}'.format(random.randint(100000, 999999))
    server_utils.send_verification_email(email, 'Verification Code', f'Your verification code is: {verification_code}')
    return "Code sent", verification_code


def update_password(update_pass_dict, account_data_dict):
    """
    responsible for the second part of changing a user password
    :param update_pass_dict:
    :param account_data_dict:
    :return:
    """
    email = account_data_dict.get("email").upper()
    password = update_pass_dict.get("password")

    if not server_utils.is_valid_password(password):
        return "Password doesn't meet requirements\nThe password need to be at least 6 characters and a number"

    try:
        with sqlite3.connect("database.db") as users_db:
            cursor = users_db.cursor()
            salt = os.urandom(32)

            hashed_pass_bytes = server_utils.password_hashing(password, salt)
            hashed_pass = hashed_pass_bytes.hex()
            query = "UPDATE Users SET password = ?, salt_password = ? WHERE email = ?"
            cursor.execute(query, (hashed_pass, sqlite3.Binary(salt), email))
            users_db.commit()
            return "Password updated successfully"
    except sqlite3.Error as e:
        Logger.log_error(f"{email} update_password error: {e}")
        return f"Database error: {str(e)}"


def ban_ip_address(client_ip, reason):
    # Connect to SQLite database
    users_db = sqlite3.connect("database.db")
    cursor = users_db.cursor()
    now = datetime.now().isoformat()
    query = "INSERT OR REPLACE INTO Banned_IP (IP, event_time, reason) VALUES (?, ?, ?)"
    cursor.execute(query, (client_ip, now, reason,))
    users_db.commit()
    cursor.close()
    users_db.close()
    print(f"IP {client_ip} has been banned for the following reason: {reason}")
    Logger.log_ban_ip(client_ip, reason)


def first_connection(client_socket, public_key, private_key):
    """
    responsible for the exchange of the AES key and IV at the start of each connection
    :return: aes_cipher object
    """

    keys_dict = {"key": public_key}
    client_socket.sendall(protocol.send_message(keys_dict))
    keys_response_dict = protocol.get_message(client_socket)
    encrypted_aes_key = keys_response_dict.get("aes_key")
    encrypted_iv = keys_response_dict.get("iv")

    cipher = PKCS1_OAEP.new(RSA.import_key(private_key))
    aes_key = cipher.decrypt(encrypted_aes_key)
    iv = cipher.decrypt(encrypted_iv)

    aes_cipher = protocol.AESCipher(aes_key, iv)
    return aes_cipher


def check_user_authenticity(client_socket, client_address, public_key, private_key):
    print(f"Accepted connection from {client_address}")
    aes_cipher = first_connection(client_socket, public_key, private_key)
    client_ip = client_address[0]

    with sqlite3.connect("database.db") as users_db:
        cursor = users_db.cursor()
        query = "SELECT event_time, reason FROM Banned_IP WHERE IP = ?"
        cursor.execute(query, (client_ip,))
        user_data = cursor.fetchone()

        if user_data:
            stored_time_str, reason = user_data
            stored_time = datetime.fromisoformat(stored_time_str)
            now = datetime.now()
            two_minutes = timedelta(minutes=2)
            time_difference = now - stored_time

            if time_difference > two_minutes and reason == "auto":
                print(f'Time difference of {time_difference} exceeds two minutes and reason is "auto".')
                delete_query = "DELETE FROM Banned_IP WHERE IP = ?"
                cursor.execute(delete_query, (client_ip,))
                users_db.commit()
                print(f"IP {client_ip} has been removed from the banned list.")
                # Allow the client to proceed
                accept_dict = {"command": "response", "msg": "welcome"}
                client_socket.sendall(protocol.send_message_aes(accept_dict, aes_cipher))
                handle_client(client_socket, client_address, aes_cipher)
            else:
                print(f'Time difference of {time_difference} is within two minutes or reason is not "auto".')
                block_dict = {"command": "response", "msg": "Maximum attempts reached.\n   Try again in 2 minutes."}
                client_socket.sendall(protocol.send_message_aes(block_dict, aes_cipher))
                client_socket.close()
                print(f"Blocked IP {client_ip} tried to connect.")
        else:
            print(f"No ban record found for IP {client_ip}")
            accept_dict = {"command": "response", "msg": "welcome"}
            client_socket.sendall(protocol.send_message_aes(accept_dict, aes_cipher))
            handle_client(client_socket, client_address, aes_cipher)


def handle_client(client_socket, client_address, aes_cipher):
    """
    responsible for handling each user, from the start of connection to the end
    :param client_socket:
    :param client_address:
    :param aes_cipher:
    :return:
    """
    username, is_admin, file_encryption_key, email = login_signup(client_socket, client_address, aes_cipher)
    if is_admin:
        handle_admin(client_socket, username, aes_cipher)
        return
    if username == "exit":
        print("Client requested exit")
        client_socket.close()
        return
    print(f"hello: {username}")
    client_cl = ClientClass(username, email, client_socket, aes_cipher, file_encryption_key)
    try:
        while True:
            command_dict = protocol.get_message_aes(client_socket, aes_cipher)
            command = command_dict.get("command")
            print(command)
            if command == "exit":
                print("Client requested exit")
                client_socket.close()
                return
            elif not os.path.exists(client_cl.get_folder()):
                print("client deleted")
                block_dict = {"command": "deleted", "msg": "Your account has been deleted due to wrongful use"}
                client_socket.sendall(protocol.send_message_aes(block_dict, aes_cipher))
                client_socket.close()
                return
            elif command == "upload_file":
                receive_file(command_dict, client_cl)
            elif command == "upload_folder":
                receive_folder(command_dict, client_cl)
            elif command == "refresh":
                refresh(command_dict, client_cl)
            elif command == "download":
                download(command_dict, client_cl)
            elif command == "delete":
                delete(command_dict, client_cl)
            elif command == "create_folder":
                create_folder_by_user(command_dict, client_cl)
    except (ConnectionResetError, BrokenPipeError):
        print(f"Client {client_address} disconnected unexpectedly")
        Logger.log_error(f"Client {client_address} disconnected unexpectedly")
    except Exception as e:
        Logger.log_error(f"error: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {client_address} closed")


def handle_admin(client_socket, username, aes_cipher):
    """
    responsible for handling admin user, after the connection until the end
    :param client_socket:
    :param username:
    :param aes_cipher:
    :return:
    """
    print("welcome admin")
    try:
        while True:
            command_dict = protocol.get_message_aes(client_socket, aes_cipher)
            command = command_dict.get("command")
            print(command)
            if command == "exit":
                print("Client requested exit")
                client_socket.close()
                return
            elif command == "refresh_clients":
                server_admin.refresh_clients(client_socket, aes_cipher, command_dict)
            elif command == "delete_users":
                server_admin.delete_user(client_socket, aes_cipher, command_dict, username)
            elif command == "get_logs":
                server_admin.send_logs(client_socket, aes_cipher)
    except (ConnectionResetError, BrokenPipeError):
        print(f"admin: {username} disconnected unexpectedly")
        Logger.log_error(f"admin {username} disconnected unexpectedly")
    except Exception as e:
        Logger.log_error(f"error: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {username} closed")



def main():
    """
    the first and main function of the server
    for each client connection it creates a new thread
    :return:
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((SERVER_HOST, SERVER_PORT))
    server_socket.listen()
    print(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")
    key = RSA.generate(2048)  # generate a pair of keys
    public_key = key.public_key().export_key()
    private_key = key.export_key()
    while True:
        client_socket, client_address = server_socket.accept()
        # Start a new thread for each client
        client_thread = threading.Thread(target=check_user_authenticity, args=(client_socket, client_address, public_key, private_key))
        client_thread.start()


if __name__ == '__main__':
    main()
