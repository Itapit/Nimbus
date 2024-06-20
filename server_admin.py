import sqlite3
import protocol
import os
import shutil
from logger import Logger
from server_utils import send_verification_email
UPLOAD_FOLDER = 'STORED_DATA'


def refresh_clients(client_socket, aes_cipher, refresh_dict):
    """
    responsible for sending the clients list in the DB
    :param client_socket:
    :param aes_cipher:
    :param refresh_dict:
    :return:
    """
    print("refresh clients")
    try:
        with sqlite3.connect("database.db") as users_db:
            cursor = users_db.cursor()
            query = "SELECT username, admin FROM Users WHERE admin = 0"
            cursor.execute(query)
            users = cursor.fetchall()

            # Calculate the total number of pages
            rows = refresh_dict.get("rows")
            cols = refresh_dict.get("cols")
            items_per_page = rows * cols
            total_pages = (len(users) + items_per_page - 1) // items_per_page

            # Get the users for the current page
            page = refresh_dict.get("page", 1)
            start_index = (page - 1) * items_per_page
            end_index = start_index + items_per_page
            users_dict = {username: "user" for username, is_admin in users[start_index:end_index] if not is_admin}

            total_users = len(users)

            refresh_response_dict = {"command": "response", "users": users_dict, "total_pages": total_pages, "total_users": total_users}
            client_socket.sendall(protocol.send_message_aes(refresh_response_dict, aes_cipher))

    except sqlite3.Error as e:
        Logger.log_error(f"refresh_clients error: {e}")
        print(f"Database error: {str(e)}")


def send_logs(client_socket, aes_cipher):
    """
    responsible for sending the logs to the admin
    :param client_socket:
    :param aes_cipher:
    :return:
    """
    try:
        with open('user_actions.log', 'r') as log_file:
            log_entries = log_file.readlines()

        logs_dict = {"command": "response", "logs": log_entries}
        client_socket.sendall(protocol.send_message_aes(logs_dict, aes_cipher))

    except FileNotFoundError:
        print("Log file not found.")
        logs_dict = {"command": "response", "logs": ["No logs available."]}
        Logger.log_error(f"send_logs error: FileNotFoundError ")
        client_socket.sendall(protocol.send_message_aes(logs_dict, aes_cipher))
    except Exception as e:
        print(f"Error reading log file: {e}")
        logs_dict = {"command": "response", "logs": ["Error reading log file."]}
        Logger.log_error(f"send_logs error: {e} ")
        client_socket.sendall(protocol.send_message_aes(logs_dict, aes_cipher))


def delete_user(client_socket, aes_cipher, delete_user_dict, username_admin):
    """
    responsible for deleting users when an admin request it
    :param client_socket:
    :param aes_cipher:
    :param delete_user_dict:
    :param username_admin:
    :return:
    """
    print("delete user")
    users_to_delete = delete_user_dict.get("users")

    try:
        with sqlite3.connect("database.db") as users_db:
            cursor = users_db.cursor()

            for username in users_to_delete:
                query = "SELECT email FROM Users WHERE username = ?"
                cursor.execute(query, (username,))
                email = cursor.fetchall()
                send_verification_email(email, "Account deletion", "Your account has been deleted due to wrongful use.")

                # Delete the user from the database
                query = "DELETE FROM Users WHERE username = ?"
                cursor.execute(query, (username,))

                # Delete the user's folder
                user_folder_path = os.path.join(UPLOAD_FOLDER, username)
                if os.path.exists(user_folder_path):
                    shutil.rmtree(user_folder_path)
                    print(f"Deleted folder: {username}")
                else:
                    print(f"Folder not found: {username}")

                users_db.commit()
                Logger.log_account_deletion(username, username_admin)
            delete_user__response_dict = {"command": "response", "msg": "Users deleted"}
            client_socket.sendall(protocol.send_message_aes(delete_user__response_dict, aes_cipher))

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        delete_user__response_dict = {"command": "response", "msg": f"Error deleting users: {str(e)}"}
        Logger.log_error(f"delete_user error: {e} ")
        client_socket.sendall(protocol.send_message_aes(delete_user__response_dict, aes_cipher))
