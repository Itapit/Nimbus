import socket
import os
import sys
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
import client_admin
import protocol
import zipfile
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes


SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
selected_buttons = set()
client_path = "MAIN"
current_page = 1
total_pages = 1
client_connected = False
admin_connected = False
MAXIMUS_SIZE = 1073741824


class FileItem:
    def __init__(self, name, file_type, max_display_length=20):
        self.full_name = name
        self.file_type = file_type
        self.display_name = FileItem.truncate_name(name, max_display_length)

    @staticmethod
    def truncate_name(name, max_length):
        if len(name) > max_length:
            return f"{name[:max_length-3]}..."
        else:
            return name

    def __str__(self):
        return self.display_name

    def __repr__(self):
        return self.full_name

    def get_full_name(self):
        return self.full_name



def read_file_content(file_path):
    """
    Reads the content of a file in binary mode.
    :param file_path: The path to the file to be read.
    :return: (bytes) The content of the file.
    """
    with open(file_path, 'rb') as file:
        return file.read()



def print_bytes(bytes_value):
    """
    Converts a byte value into a human-readable format
    :param bytes_value:
    :return: string that contain the size and suffix
    """
    suffixes = ['B', 'KB', 'MB', 'GB']
    suffix_index = 0
    if bytes_value == 2:
        bytes_value = 0

    while bytes_value >= 1024 and suffix_index < len(suffixes) - 1:
        bytes_value /= 1024.0
        suffix_index += 1

    return f"{bytes_value:.2f} {suffixes[suffix_index]}"


def file_explorer_ui(aes_cipher):
    """
    The main function for the homepage of a regular user after connection to his user
    The function is responsible for rendering the UI and starting the functions based on the user buttons presses
    The user leave this part of function only when he closes the program
    :param aes_cipher:
    :return: nothing
    """
    client_path = "MAIN"
    current_page = 1

    def open_folder():
        """
        responsible for the button "open_folder"
        when a user selects a folder that he want to "get into" and see the files inside the folder
        changes the global var client_path
        :return:
        """
        global client_path
        # Get the selected buttons
        selected_buttons_list = list(selected_buttons)
        # Check if only one item is selected
        if len(selected_buttons_list) != 1:
            print("Please select only one item.")
            return

        # Check if the selected item is a folder
        selected_item = selected_buttons_list[0]
        if selected_item.cget("image") != str(subsampled_icon_folder):
            print("Please select a folder, not a file.")
            return

        # Get the folder name
        folder_name = filename_map.get(selected_item).get_full_name()
        # Update the client path
        client_path = os.path.join(client_path, folder_name)
        print(f"Opening folder: {client_path}")
        refresh()

    def exit_folder():
        """
        responsible for the button "exit_folder"
        when a user wants to exit to the parent directory
        changes the global var client_path
        :return:
        """
        global client_path
        # Get the parent directory of the current path
        if client_path != "MAIN":
            client_path = os.path.dirname(client_path)
            print(f"Exiting to: {client_path}")
            refresh()

    def create_folder():
        """
        responsible for the button "create_folder"
        when a user wants to create a new function he can name it and send the request to the server.
        :return:
        """
        global client_path
        folder_name = ask_string_popup("Enter folder name:")
        if folder_name:
            create_folder_dict = {"command": "create_folder", "folder_name": os.path.join(client_path[5:], folder_name)}
            client_socket.sendall(protocol.send_message_aes(create_folder_dict, aes_cipher))
            response_dict = protocol.get_message_aes(client_socket, aes_cipher)

            command = response_dict.get("command")
            msg = response_dict.get("msg")
            if command == "deleted":
                root.destroy()
                show_error_popup(msg)
                sys.exit()
            if msg == "Folder created successfully":
                refresh()
            else:
                show_popup(msg)

    def refresh():
        """
        responsible for the button "refresh"
        this function is called upon with many other functions because his responsible for refreshing
        request the files and folders to display from the server with the global var client_path.
        :return:
        """
        global current_page, total_pages, client_path
        print("refresh")
        refresh_dict = {"command": "refresh", "path": client_path, "page": current_page, "rows": rows, "cols": cols}
        path_label.config(text=client_path)
        client_socket.sendall(protocol.send_message_aes(refresh_dict, aes_cipher))
        refresh_response_dict = protocol.get_message_aes(client_socket, aes_cipher)

        command = refresh_response_dict.get("command")
        if command == "deleted":
            msg = refresh_response_dict.get("msg")
            root.destroy()
            show_error_popup(msg)
            sys.exit()

        # Get the file_size, files, and total_pages from the response
        file_size = refresh_response_dict.get("file_size")
        files = refresh_response_dict.get("files")
        total_pages = refresh_response_dict.get("total_pages")
        folder_size_label.config(text=print_bytes(file_size))

        # Clear the buttons array
        for current_row in buttons:
            for button1 in current_row:
                button1.grid_remove()

        # Iterate over the files and update the buttons
        current_row = 0
        current_col = 0
        for file_name, file_type in files.items():
            file_item = FileItem(file_name, file_type)
            if current_row < rows and current_col < cols:
                icon_image = subsampled_icon_file if file_type == "file" else subsampled_icon_folder
                buttons[current_row][current_col].config(text=str(file_item), image=icon_image, font=("Arial", 12), compound="top",
                                                         relief="raised", command=lambda r=current_row, c=current_col: button_click(r, c))
                buttons[current_row][current_col].grid()
                filename_map[buttons[current_row][current_col]] = file_item
            current_col += 1
            if current_col == cols:
                current_col = 0
                current_row += 1
        selected_buttons.clear()

    def delete():
        """
        responsible for the button "Delete"
        confirm if the user wants to delete the files
        create a list of paths of the files that he wants to delete
        calls the function delete_files with the list
        :return:
        """
        global client_path
        files_list_items = [filename_map.get(button1) for button1 in selected_buttons]
        files_list = [item.get_full_name() for item in files_list_items]
        print(f"files list: {files_list}")

        files_with_path = [os.path.join(client_path, filename) for filename in files_list]
        if len(files_list) > 5 or any(item.file_type == "folder" for item in files_list_items):
            amount_of_items = len(files_list)
            confirmation_text = f"Are you sure you want to delete {amount_of_items} items?"
            confirmed = show_confirmation_popup(confirmation_text)
            if confirmed:
                delete_files(files_with_path)
        else:
            delete_files(files_with_path)

    def delete_files(files_with_path):
        """
        send a request to the server to delete list of files and folders
        :param files_with_path: list of the files_path the user wants to delete
        :return:
        """
        delete_dict = {"command": "delete", "files": files_with_path}
        client_socket.sendall(protocol.send_message_aes(delete_dict, aes_cipher))
        refresh()

    def download():
        """
        Downloads selected files from the server to the local machine's Downloads folder.
        Global Variables:
            - client_path (str): Path to the client directory within the UI
        This function performs the following steps:
            1. Retrieves the list of selected files based on the user's selection.
            2. Constructs the file paths the selected files.
            3. Sends a download request to the server with the list of selected files.
            4. Receives the files from the server, handling potential responses indicating
             that no files were selected.
            5. Saves the received files to the Downloads folder, ensuring unique filenames
            to avoid conflicts.
            6. If a folder is downloaded, it is saved as a zip file, extracted, and the zip
            file is then removed.
        :return:
        """
        global client_path
        try:
            # construct a list with the file paths
            files_list_items = [filename_map.get(button1) for button1 in selected_buttons]
            files_list = [item.get_full_name() for item in files_list_items]
            print(f"files list: {files_list}")
            files_with_path = [os.path.join(client_path, filename) for filename in files_list]
            # send the request to the server
            download_dict = {"command": "download", "files": files_with_path}
            client_socket.sendall(protocol.send_message_aes(download_dict, aes_cipher))
            response_dict = protocol.get_message_aes(client_socket, aes_cipher)

            command = response_dict.get("command")
            if command == "deleted":
                msg = response_dict.get("msg")
                root.destroy()
                show_error_popup(msg)
                sys.exit()

            downloads_folder = os.path.expanduser("~") + os.sep + "Downloads"
            files = response_dict.get("files")
            print(files)
            if files == "no files selected":
                return
            for file_info in files:
                file_name = file_info["file_name"]
                file_type = file_info["file_type"]
                file_content = file_info["file_Content"]

                file_path = os.path.join(downloads_folder, f"{file_name}{file_type}")
                new_file_name = file_name
                counter = 1
                while os.path.exists(file_path):
                    new_file_name = f"{file_name}({counter})"
                    file_path = os.path.join(downloads_folder, f"{new_file_name}{file_type}")
                    counter += 1
                file_name = new_file_name

                if file_type == "folder":
                    # Handle the case when the user downloads a folder
                    folder_name = os.path.splitext(file_name)[0]  # Remove the .zip extension
                    unzipped_folder_path = os.path.join(downloads_folder, folder_name)
                    # Added a loop to handle folder name conflicts
                    counter = 1
                    while os.path.exists(unzipped_folder_path):
                        new_folder_name = f"{folder_name}({counter})"
                        unzipped_folder_path = os.path.join(downloads_folder, new_folder_name)
                        counter += 1
                    zip_file_path = os.path.join(downloads_folder, file_name)
                    with open(zip_file_path, "wb") as f:
                        f.write(file_content)
                    print(f"Folder saved: {zip_file_path}")

                    # Unzip the folder
                    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                        for member in zip_ref.infolist():
                            extracted_path = zip_ref.extract(member, unzipped_folder_path)
                            if member.is_dir():
                                os.makedirs(extracted_path, exist_ok=True)
                    print(f"Folder extracted: {unzipped_folder_path}")
                    # Remove the zip file
                    os.remove(zip_file_path)
                else:
                    # Handle the case when the user downloads a file
                    filepath = os.path.join(downloads_folder, file_name + file_type)
                    with open(filepath, "wb") as f:
                        f.write(file_content)
                    print(f"File saved: {filepath}")
            refresh()
        except PermissionError:
            print(f"Permission denied when saving file/folder")
            show_popup(f"Permission denied when saving file/folder. Please check your permissions.")
        except IOError as e:
            print(f"IO Error occurred when saving file/folder: {e}")
            show_popup(f"Error occurred when saving file/folder. Please try again.")
        except zipfile.BadZipFile:
            print(f"Error extracting zip file:")
            show_popup(f"The downloaded folder seems to be corrupted. Unable to extract.")


    def upload_file():
        """
        responsible for the button "upload_file"
        open up the file explorer of the user and lets him select a file
        send a request of the server of the upload_file
        :return:
        """
        global client_path
        print("upload file")
        try:
            file_path = filedialog.askopenfilename(initialdir=os.path.expanduser("~") + os.sep + "Desktop",
                                                   title="Open file",
                                                   filetypes=[
                                                       ("Common File Types", "*.txt;*.docx;*.doc;*.xlsx;*.xls;*.pptx;*.ppt;*.pdf;*.jpg;*.jpeg;*.png;*.gif;*.mp4;*.avi;*.mov;*.mp3;*.m4a;*.zip;*.rar;*.7z;*.gz;*.tar;"),
                                                       ("All Files", "*.*")
                                                    ]
                                                   )
            if file_path:
                file_name, file_type = os.path.splitext(os.path.basename(file_path))
                file_name = os.path.join(client_path, file_name)
                file_content = read_file_content(file_path)
                if len(file_content) < MAXIMUS_SIZE:
                    upload_dict = {"command": "upload_file", "file_name": file_name, "file_type": file_type, "file_Content": file_content}
                    client_socket.sendall(protocol.send_message_aes(upload_dict, aes_cipher))
                    refresh()
                else:
                    print("file too large")
                    show_popup("the file is too large")
            else:
                print("No file selected")

        except FileNotFoundError:
            print(f"Error: File not found.")
            show_popup(f"Error: File not found.")
        except PermissionError as e:
            print(f"Permission denied when reading file: {e}")
            show_popup(f"Permission denied when reading file: {e}")
        except OSError as e:
            print(f"Error reading file: {e}")
            show_popup(f"Error reading file: {e}")

    def upload_folder():
        """
        responsible for the button "upload_folder"
        open up the file explorer of the user and lets him select a folder
        the client zip the folder and send it as a zip file
        send a request of the server of the upload_folder
        :return:
        """
        global client_path
        print("upload folder")
        zip_file_name = ""
        try:
            folder_path = filedialog.askdirectory(initialdir=os.path.expanduser("~") + os.sep + "Desktop",
                                                  title="Open file")
            if folder_path:
                zip_file_name = os.path.basename(folder_path) + ".zip"

                # Create a zip file containing the existing folder
                with zipfile.ZipFile(zip_file_name, 'w') as zip_file:
                    # Iterate over the files and directories in the folder
                    for root1, dirs, files in os.walk(folder_path):
                        # Add empty directories to the zip file
                        for dir_name in dirs:
                            dir_path = os.path.join(root1, dir_name)
                            zip_file.write(dir_path, os.path.relpath(dir_path, folder_path))

                        # Add files to the zip file
                        for file in files:
                            file_path = os.path.join(root1, file)
                            zip_file.write(file_path, os.path.relpath(file_path, folder_path))

                file_content = read_file_content(zip_file_name)
                if len(file_content) < MAXIMUS_SIZE:
                    temp_zip_file_name = os.path.join(client_path, zip_file_name)

                    upload_dict = {"command": "upload_folder", "folder_name": temp_zip_file_name, "folder_content": file_content}
                    client_socket.sendall(protocol.send_message_aes(upload_dict, aes_cipher))
                    refresh()
                else:
                    print("folder too large")
                    show_popup("folder too large")

            else:
                print("No folder selected")

        except FileNotFoundError:
            print(f"Error: File not found.")
            show_popup(f"Error: File not found.")
        except PermissionError as e:
            print(f"Permission denied when reading file: {e}")
            show_popup(f"Permission denied when reading file: {e}")
        except OSError as e:
            print(f"Error reading file: {e}")
            show_popup(f"Error reading file: {e}")

        finally:
            # Attempt to remove the temporary zip file
            try:
                os.remove(zip_file_name)
            except FileNotFoundError:
                pass  # Ignore if the file doesn't exist (it may not have been created)
            except PermissionError:
                print(f"Permission denied when removing temporary zip file: {zip_file_name}")
            except OSError as e:
                print(f"Error removing temporary zip file: {e}")


    def show_popup(string1):
        """
        responsible for a popup msg that can appear in different situations
        :param string1: that can be many kinds of strings, it will render this string in the popup
        :return:
        """
        popup = tk.Toplevel(root)
        popup.title("Nimbus")
        popup.iconbitmap('icons//Icon_no_text.ico')

        popup_frame = ttk.Frame(popup, padding=10)
        popup_frame.pack(fill="both", expand=True)

        label = ttk.Label(popup_frame, text=string1)
        label.pack(pady=20)

        ok_button = ttk.Button(popup_frame, text="OK", command=popup.destroy)
        ok_button.pack()

        # Center the popup window on the screen
        popup.update_idletasks()  # Update geometry information
        window_width = 400  # Increase the width to 400 pixels
        window_height = popup.winfo_height()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")


    def show_confirmation_popup(confirmation_text):
        """
        responsible for a popup msg that can appear in different situations
        it renders the msg with buttons of confirmation "yes" and "no"
        :param confirmation_text:  the string to render in the popup
        :return: a bool that represent what the user pressed
        """
        popup = tk.Toplevel(root)
        popup.title("Confirmation")
        popup.iconbitmap('icons//Icon_no_text.ico')

        popup_frame = ttk.Frame(popup, padding=10)
        popup_frame.pack(fill="both", expand=True)

        label = ttk.Label(popup_frame, text=confirmation_text)
        label.pack(pady=20)

        result = None

        def confirm_yes():
            nonlocal result
            result = True
            popup.destroy()

        def confirm_cancel():
            nonlocal result
            result = False
            popup.destroy()

        yes_button = ttk.Button(popup_frame, text="Yes", command=confirm_yes)
        yes_button.pack(side="left", padx=10)

        cancel_button = ttk.Button(popup_frame, text="Cancel", command=confirm_cancel)
        cancel_button.pack(side="right", padx=10)

        # Center the popup window on the screen
        popup.update_idletasks()  # Update geometry information
        window_width = 400
        window_height = popup.winfo_height()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

        popup.wait_window(popup)
        return result if result is not None else False


    def ask_string_popup(prompt):
        """
        responsible for a popup msg that can appear in different situations
        it renders the msg with an input area of a string
        :param prompt: the string to render in the popup
        :return: the string that the user wrote
        """
        popup = tk.Toplevel(root)
        popup.title("Nimbus")
        popup.iconbitmap('icons//Icon_no_text.ico')

        popup_frame = ttk.Frame(popup, padding=10)
        popup_frame.pack(fill="both", expand=True)

        label = ttk.Label(popup_frame, text=prompt)
        label.pack(pady=10)

        entry = ttk.Entry(popup_frame)
        entry.pack(pady=5)

        def on_ok(arg=None):
            popup.result = entry.get()
            popup.destroy()

        popup.bind('<Return>', on_ok)

        ok_button = ttk.Button(popup_frame, text="OK", command=on_ok)
        ok_button.pack(pady=10)

        # Center the popup window on the screen
        popup.update_idletasks()  # Update geometry information
        window_width = 300
        window_height = popup.winfo_height()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

        popup.result = None
        popup.wait_window(popup)
        return popup.result if popup.result is not None else ""


    def previous_page():
        """
        responsible for the button "previous_page"
        incase the user have to many files to display he can move pages, this allows him to move backwards
        :return:
        """
        global current_page
        if current_page > 1:
            current_page -= 1
            page_label.config(text=current_page)
            refresh()

    def next_page():
        """
        responsible for the button "next_page"
        incase the user have to many files to display he can move to the next page
        :return:
        """
        global current_page, total_pages
        if current_page < total_pages:
            current_page += 1
            page_label.config(text=current_page)
            refresh()

    root = tk.Tk()
    root.title("Nimbus")
    root.iconbitmap('icons//Icon_no_text.ico')

    def on_closing():
        """
        responsible for the closure of the program, when a user exit the program this function is called
        sends a msg to the server that the client disconnected and end the program
        :return:
        """
        print("closed")
        closing_connection_dict = {"command": "exit"}
        client_socket.sendall(protocol.send_message_aes(closing_connection_dict, aes_cipher))
        root.destroy()
        sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Apply ttk style for a modern look
    style = ttk.Style()
    style.theme_use('clam')

    # Define custom colors
    background_color = "#f0f0f0"
    button_color = "#4CAF50"
    button_text_color = "#FFFFFF"

    # Configure style elements
    style.configure('TFrame', background=background_color)
    style.configure('TButton', background=button_color, foreground=button_text_color)
    style.configure('TLabel', background=background_color, font=('TkDefaultFont', 12, 'bold'))
    style.configure('TCanvas', background=background_color)
    style.configure('TSeparator', thickness=2)

    # Set initial window size
    root.geometry("1000x600")  # Width x Height

    # Create frames with styled background
    left_frame = ttk.Frame(root)  # Use ttk.Frame for styling
    left_frame.pack(side="left", fill="y")  # Fill vertically

    right_frame = ttk.Frame(root)
    right_frame.pack(side="right", fill="both", expand=True)

    # Create thicker styled line between frames
    line = ttk.Separator(root, orient="vertical")  # Use ttk.Separator for styling
    line.pack(side="left", fill="y", padx=5)

    icon_image_open_folder = tk.PhotoImage(file="icons//open_folder.png")
    subsampled_icon_open_folder = icon_image_open_folder.subsample(16, 16)  # Reduce size

    icon_image_exit_folder = tk.PhotoImage(file="icons//exit_folder.png")
    subsampled_icon_exit_folder = icon_image_exit_folder.subsample(16, 16)  # Reduce size

    # Create styled widgets in left frame using ttk
    open_folder_button = ttk.Button(left_frame, text="Open folder", image=subsampled_icon_open_folder, compound="top", command=open_folder)
    open_folder_button.pack(side="top")

    exit_folder_button = ttk.Button(left_frame, text="Exit folder", image=subsampled_icon_exit_folder, compound="top", command=exit_folder)
    exit_folder_button.pack(side="top")

    icon_image_create_folder = tk.PhotoImage(file="icons//create_folder.png")
    subsampled_icon_image_create_folder = icon_image_create_folder.subsample(16, 16)  # Reduce size

    create_folder_button = ttk.Button(left_frame, text="Create folder", image=subsampled_icon_image_create_folder, compound="top", command=create_folder)
    create_folder_button.pack(side="top")

    icon_image_refresh = tk.PhotoImage(file="icons//refresh.png")
    subsampled_icon_refresh = icon_image_refresh.subsample(16, 16)  # Reduce size

    refresh_button = ttk.Button(left_frame, text="Refresh", image=subsampled_icon_refresh, compound="top", command=refresh)
    refresh_button.pack(side="top")

    folder_size_label = ttk.Label(left_frame, text="")
    folder_size_label.pack(side="bottom")

    # Load icon image
    icon_image_delete = tk.PhotoImage(file="icons//delete.png")
    subsampled_icon_delete = icon_image_delete.subsample(16, 16)  # Reduce size

    icon_image_upload_file = tk.PhotoImage(file="icons//upload_file.png")
    subsampled_icon_upload_file = icon_image_upload_file.subsample(16, 16)  # Reduce size

    icon_image_upload_folder = tk.PhotoImage(file="icons//upload_folder.png")
    subsampled_icon_upload_folder = icon_image_upload_folder.subsample(16, 16)  # Reduce size

    icon_image_download = tk.PhotoImage(file="icons//download.png")
    subsampled_icon_download = icon_image_download.subsample(16, 16)  # Reduce size

    # Create styled text label in right frame with bold font
    path_label = ttk.Label(right_frame, text=client_path)
    path_label.pack(anchor="n", fill="x", padx=10, pady=5)  # Anchor to top, fill horizontally, and add padding

    # Create thicker styled horizontal line under the text label
    line_horizontal = ttk.Separator(right_frame, orient="horizontal")  # Use ttk.Separator for styling
    line_horizontal.pack(anchor="s", fill="x", padx=5, pady=5)

    # Create buttons frame in right frame
    buttons_frame = ttk.Frame(right_frame)
    buttons_frame.pack(side="bottom", fill="x")


    # Create styled buttons in buttons frame using ttk
    delete_button = ttk.Button(buttons_frame, text="Delete", image=subsampled_icon_delete, compound="top",
                               command=delete)
    delete_button.pack(side="left")

    upload_button_file = ttk.Button(buttons_frame, text="Upload File", image=subsampled_icon_upload_file, compound="top",
                                    command=upload_file)
    upload_button_file.pack(side="left")

    upload_button_folder = ttk.Button(buttons_frame, text="Upload Folder", image=subsampled_icon_upload_folder, compound="top",
                                      command=upload_folder)
    upload_button_folder.pack(side="left")

    download_button = ttk.Button(buttons_frame, text="Download", image=subsampled_icon_download, compound="top", command=download)
    download_button.pack(side="left")

    # Create a new frame for the "Next" and "Previous" buttons
    nav_buttons_frame = ttk.Frame(buttons_frame)
    nav_buttons_frame.pack(side="right", padx=10)  # Add some padding to the right

    icon_image_left = tk.PhotoImage(file="icons//left-arrow.png")
    subsampled_icon_left = icon_image_left.subsample(16, 16)  # Reduce size

    icon_image_right = tk.PhotoImage(file="icons//right-arrow.png")
    subsampled_icon_right = icon_image_right.subsample(16, 16)  # Reduce size

    # Create the "Next" and "Previous" buttons
    next_button = ttk.Button(nav_buttons_frame, text="Next", image=subsampled_icon_right, compound="top",
                             command=next_page)
    next_button.pack(side="right", padx=5)  # Add some padding between the buttons

    page_label = ttk.Label(nav_buttons_frame, text=current_page)
    page_label.pack(side="right", padx=5)

    previous_button = ttk.Button(nav_buttons_frame, text="Previous", image=subsampled_icon_left, compound="top",
                                 command=previous_page)
    previous_button.pack(side="right")

    files_frame = ttk.Frame(right_frame)
    files_frame.pack(fill="x")

    icon_image_file = tk.PhotoImage(file="icons//file.png")
    subsampled_icon_file = icon_image_file.subsample(16, 16)  # Reduce size

    icon_image_folder = tk.PhotoImage(file="icons//folder.png")
    subsampled_icon_folder = icon_image_folder.subsample(16, 16)  # Reduce size

    rows = 5
    cols = 6
    buttons = []
    filename_map = {}

    def button_click(row_index1, col_index1):
        """
        responsible to update the global var of the selected buttons
        when the user press any of the files/folder buttons it calls this function
        :param row_index1: the row index of the button that he selected
        :param col_index1: the colum index of the button that he selected
        :return:
        """
        button1 = buttons[row_index1][col_index1]
        if button1 in selected_buttons:
            # Button is already selected, so unselect it
            selected_buttons.remove(button1)
            button1.config(relief="raised")  # Change the button's appearance to unselected state
        else:
            # Button is not selected, so select it
            selected_buttons.add(button1)  # For set
            # selected_buttons.append(button)  # For list
            button1.config(relief="sunken")  # Change the button's appearance to selected state

        print(f"Selected buttons: {[filename_map.get(button1) for button1 in selected_buttons]}")


    for row_index in range(rows):
        row = []
        for col_index in range(cols):
            button = tk.Button(files_frame, text=f"Button {row_index},{col_index}", font=("Arial", 12), image=subsampled_icon_file,
                               compound="top", padx=20, pady=10,  command=lambda r=row_index, c=col_index: button_click(r, c))
            button.grid(row=row_index, column=col_index, sticky="nsew")
            row.append(button)
        buttons.append(row)

    # Make all buttons expand and fill the frame
    for row_index in range(rows):
        files_frame.grid_rowconfigure(row_index, weight=1)
    for col_index in range(cols):
        files_frame.grid_columnconfigure(col_index, weight=1)

    refresh()
    root.mainloop()


def login_signup(aes_cipher):
    """
    The main function for the login/signup/forgot_password
    The function is responsible for rendering the UI and starting the functions based on the user buttons presses
    The user leave this part of function only when he logs in successfully.
    param aes_cipher: the aes_cipher object that responsible for the encryption and decryption with the protocol.py
    :return: a confirmation to the main function if a normal user logged in or and admin
    """
    global client_connected, admin_connected
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    def on_closing():
        """
        responsible for the closure of the program, when a user exit the program this function is called
        sends a msg to the server that the client disconnected and end the program
        :return:
        """
        print("closed")
        closing_connection_dict = {"command": "exit"}
        client_socket.sendall(protocol.send_message_aes(closing_connection_dict, aes_cipher))
        root.destroy()
        sys.exit()

    dialog = tk.Toplevel(root)
    dialog.protocol("WM_DELETE_WINDOW", on_closing)
    dialog.title("Nimbus")
    dialog.geometry("400x400")

    dialog.iconbitmap('icons//Icon_no_text.ico')

    # Create style for modern look (optional)
    style = ttk.Style(dialog)
    style.theme_use('clam')

    # Custom colors
    background_color = "#f0f0f0"
    button_color = "#4CAF50"
    button_text_color = "#FFFFFF"

    # Configure style elements
    style.configure('TButton', background=button_color, foreground=button_text_color)
    style.configure('TFrame', background=background_color)
    style.configure('TLabel', background=background_color)

    # Create a notebook to switch between login and signup frames
    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Login frame
    login_frame = ttk.Frame(notebook, padding=10)
    notebook.add(login_frame, text="Login")

    icon_image = tk.PhotoImage(file="icons//icon.png")
    subsampled_icon = icon_image.subsample(6, 6)  # Reduce size

    icon_image_label = ttk.Label(login_frame, image=subsampled_icon)
    icon_image_label.pack()

    # Login email label and entry
    login_email_label = ttk.Label(login_frame, text="Email:")
    login_email_label.pack()

    login_email_entry = ttk.Entry(login_frame, width=30)
    login_email_entry.pack()

    # Login password label and entry
    login_password_label = ttk.Label(login_frame, text="Password:")
    login_password_label.pack()

    login_password_entry = ttk.Entry(login_frame, width=30, show="*")
    login_password_entry.pack()


    def login(arg=None):
        """
        responsible for sending the server a request to login
        rending the response from the server in the UI
        :param arg: the input that the client enter: email,password
        :return: a confirmation to the previous function if a normal user logged in or and admin
        """
        global client_connected, admin_connected
        print("Login clicked")
        email_entry = login_email_entry.get()
        password_entry = login_password_entry.get()
        print(email_entry)
        print(password_entry)
        login_dict = {"command": "login", "email": email_entry, "username": "", "password": password_entry}
        client_socket.sendall(protocol.send_message_aes(login_dict, aes_cipher))
        response_dict = protocol.get_message_aes(client_socket, aes_cipher)
        msg = response_dict.get("msg")
        print(msg)
        if msg == "Login successful":
            message_label_login.config(text=msg)
            client_connected = True
            root.destroy()
        elif msg == "Admin connected":
            admin_connected = True
            root.destroy()
        elif msg is not None and msg.startswith("Wrong password"):
            message_label_login.config(text=msg)
        elif msg == "Too many failed login attempts. Please try again later.":
            message_label_login.config(text=msg)
            login_password_entry.config(state="disabled")
            login_button.config(state="disabled")
            login_frame.unbind('<Return>')  # Disable the Enter key binding
        else:
            message_label_login.config(text=msg)

    login_frame.bind('<Return>', login)
    login_password_entry.bind('<Return>', login)
    login_email_entry.bind('<Return>', login)

    # Login button
    login_button = ttk.Button(login_frame, text="Login", command=login)
    login_button.pack(pady=10)

    # Login message label
    login_message_label = ttk.Label(login_frame, text="")
    login_message_label.pack()

    # Signup frame
    signup_frame = ttk.Frame(notebook, padding=10)
    notebook.add(signup_frame, text="Sign-Up")

    icon_image_label_signup = ttk.Label(signup_frame, image=subsampled_icon)
    icon_image_label_signup.pack()

    # Signup email label and entry
    signup_email_label = ttk.Label(signup_frame, text="Email:")
    signup_email_label.pack()

    signup_email_entry = ttk.Entry(signup_frame, width=30)
    signup_email_entry.pack()

    # Signup username label and entry
    signup_username_label = ttk.Label(signup_frame, text="Username:")
    signup_username_label.pack()

    signup_username_entry = ttk.Entry(signup_frame, width=30)
    signup_username_entry.pack()

    # Signup password label and entry
    signup_password_label = ttk.Label(signup_frame, text="Password:")
    signup_password_label.pack()

    signup_password_entry = ttk.Entry(signup_frame, width=30, show="*")
    signup_password_entry.pack()

    def signup(arg=None):
        """
        responsible for sending the server the first request to signup
        rending the response from the server in the UI
        if its successful its calls the next function of the signup : verify_code
        :param arg:
        :return: a confirmation to the previous function if a user signup successfully
        """
        global client_connected
        print("Signup clicked")
        email_entry = signup_email_entry.get()
        username_entry = signup_username_entry.get()
        password_entry = signup_password_entry.get()
        signup_dict = {"command": "signup", "email": email_entry, "username": username_entry, "password": password_entry}
        client_socket.sendall(protocol.send_message_aes(signup_dict, aes_cipher))
        response_dict = protocol.get_message_aes(client_socket, aes_cipher)
        response = response_dict.get("msg")
        if response == "Enter code":
            # Save the original layout of the widgets
            original_layout = {
                "email_label": signup_email_label.pack_info(),
                "email_entry": signup_email_entry.pack_info(),
                "username_label": signup_username_label.pack_info(),
                "username_entry": signup_username_entry.pack_info(),
                "password_label": signup_password_label.pack_info(),
                "password_entry": signup_password_entry.pack_info(),
                "signup_button": signup_button.pack_info()
            }

            # Hide the email, username, and password entries and labels
            signup_email_label.pack_forget()
            signup_email_entry.pack_forget()
            signup_username_label.pack_forget()
            signup_username_entry.pack_forget()
            signup_password_label.pack_forget()
            signup_password_entry.pack_forget()
            signup_button.pack_forget()
            message_label_signup.config(text="")


            # Create a new label and entry for the verification code
            verification_code_label = ttk.Label(signup_frame, text="Verification Code:")
            verification_code_label.pack(side="top", padx=5, pady=5)

            verification_code_entry = ttk.Entry(signup_frame, width=30)
            verification_code_entry.pack(side="top", padx=5, pady=5)

            def verify_code(arg1=None):
                """
                the second part of the signup,
                rending the response from the server in the UI
                send a request to the server with the input code the client wrote
                :param arg1:
                :return: a confirmation to the previous function if a user signup successfully
                """
                global client_connected
                code_entry = verification_code_entry.get()
                verification_dict = {"command": "signup_code", "code": code_entry}
                client_socket.sendall(protocol.send_message_aes(verification_dict, aes_cipher))
                verification_response_dict = protocol.get_message_aes(client_socket, aes_cipher)
                msg = verification_response_dict.get("msg")
                print(msg)
                if msg == "Account created":
                    message_label_signup.config(text=msg)
                    client_connected = True
                    root.destroy()
                elif msg is not None and msg.startswith("Invalid code"):
                    message_label_signup.config(text=msg)
                elif msg == "Maximum attempts reached. Please try again later.":
                    message_label_signup.config(text=msg)
                    # Clear the verification code entry
                    verification_code_entry.delete(0, tk.END)
                    # Disable the Verify button
                    verify_button.config(state="disabled")
                    # Unbind the Enter key event from the signup frame and verification code entry
                    signup_frame.unbind('<Return>')
                    verification_code_entry.unbind('<Return>')
                else:
                    message_label_signup.config(text=msg)
                    # Restore the original layout of the widgets
                    signup_email_label.pack(**original_layout["email_label"])
                    signup_email_entry.pack(**original_layout["email_entry"])
                    signup_username_label.pack(**original_layout["username_label"])
                    signup_username_entry.pack(**original_layout["username_entry"])
                    signup_password_label.pack(**original_layout["password_label"])
                    signup_password_entry.pack(**original_layout["password_entry"])
                    signup_button.pack(**original_layout["signup_button"])
                    # Remove the verification code label and entry
                    verification_code_label.pack_forget()
                    verification_code_entry.pack_forget()
                    verify_button.pack_forget()

            verify_button = ttk.Button(signup_frame, text="Verify", command=verify_code)
            verify_button.pack(side="top", padx=5, pady=5)

            signup_frame.bind('<Return>', verify_code)
            verification_code_entry.bind('<Return>', verify_code)
        else:
            message_label_signup.config(text=response)

    signup_frame.bind('<Return>', signup)
    signup_password_entry.bind('<Return>', signup)
    signup_email_entry.bind('<Return>', signup)
    signup_username_entry.bind('<Return>', signup)

    # Signup button
    signup_button = ttk.Button(signup_frame, text="Sign-Up", command=signup)
    signup_button.pack(pady=10)

    # Signup message label
    signup_message_label = ttk.Label(signup_frame, text="")
    signup_message_label.pack()

    # signup respond from server label
    message_label_signup = tk.Label(signup_frame, text="")
    message_label_signup.pack(side="bottom", padx=5, pady=5)

    # signup respond from server label
    message_label_login = tk.Label(login_frame, text="")
    message_label_login.pack(side="bottom", padx=5, pady=5)

    forgot_password_frame = ttk.Frame(notebook, padding=10)
    notebook.add(forgot_password_frame, text="Forgot Password")

    icon_image_label_forgot_password = ttk.Label(forgot_password_frame, image=subsampled_icon)
    icon_image_label_forgot_password.pack()

    # Forgot Password email label and entry
    forgot_password_email_label = ttk.Label(forgot_password_frame, text="Email:")
    forgot_password_email_label.pack()

    forgot_password_email_entry = ttk.Entry(forgot_password_frame, width=30)
    forgot_password_email_entry.pack()

    def forgot_password(arg=None):
        """
        responsible for  changing a user password
        rending the response from the server in the UI
        send a request to the server with the email the client wrote
        if its successful its calls the next function : verify_code
        :param arg:
        :return:
        """
        email = forgot_password_email_entry.get()
        forgot_password_dict = {"command": "forgot_password", "email": email}
        client_socket.sendall(protocol.send_message_aes(forgot_password_dict, aes_cipher))
        response = protocol.get_message_aes(client_socket, aes_cipher)
        msg = response.get("msg")

        if msg == "Enter code":
            # Hide the email entry and label
            forgot_password_email_label.pack_forget()
            forgot_password_email_entry.pack_forget()
            forgot_password_button.pack_forget()
            message_label_forgot_password.config(text="")
            # Create a new label and entry for the verification code
            verification_code_label = ttk.Label(forgot_password_frame, text="Verification Code:")
            verification_code_label.pack()

            verification_code_entry = ttk.Entry(forgot_password_frame, width=30)
            verification_code_entry.pack()

            def verify_code(arg1=None):
                """
                the second part of the forgot_password
                rending the response from the server in the UI
                send a request to the server with the input code the client wrote
                if its successful its calls the next function : update_password
                :param arg1:
                :return:
                """
                code = verification_code_entry.get()
                forgot_pass_response_dict = {"command": "forgot_password_code", "code": code}
                client_socket.sendall(protocol.send_message_aes(forgot_pass_response_dict, aes_cipher))
                response1 = protocol.get_message_aes(client_socket, aes_cipher)
                msg1 = response1.get("msg")
                if msg1 == "Code verified":
                    # Hide the verification code label and entry
                    verification_code_label.pack_forget()
                    verification_code_entry.pack_forget()
                    verify_button.pack_forget()
                    message_label_forgot_password.config(text="")

                    # Create new labels and entries for the new password
                    new_password_label = ttk.Label(forgot_password_frame, text="New Password:")
                    new_password_label.pack()

                    new_password_entry = ttk.Entry(forgot_password_frame, width=30, show="*")
                    new_password_entry.pack()

                    def update_password(arg2=None):
                        """
                        the third part of the forgot_password
                        rending the response from the server in the UI
                        send a request to the server with the new password the client wrote
                        :param arg2:
                        :return:
                        """
                        new_password = new_password_entry.get()
                        update_pass_dict = {"command": "forgot_password_new", "password": new_password}
                        client_socket.sendall(protocol.send_message_aes(update_pass_dict, aes_cipher))
                        update_pass_response_dict = protocol.get_message_aes(client_socket, aes_cipher)
                        msg2 = update_pass_response_dict.get("msg")
                        msg3 = update_pass_response_dict.get("attempts")
                        if msg3 == "reset" and msg2 == "Password updated successfully":
                            login_password_entry.config(state="enabled")
                            login_button.config(state="enabled")
                            login_frame.bind('<Return>')  # Disable the Enter key binding
                        message_label_forgot_password.config(text=msg2)

                    update_password_button = ttk.Button(forgot_password_frame, text="Update Password",
                                                        command=update_password)
                    update_password_button.pack()

                    forgot_password_frame.bind('<Return>', update_password)
                    new_password_entry.bind('<Return>', update_password)
                elif msg1 is not None and msg1.startswith("Invalid code"):

                    message_label_forgot_password.config(text=msg1)
                elif msg1 == "Maximum attempts reached. Please try again later.":
                    message_label_forgot_password.config(text=msg1)
                    # Clear the verification code entry
                    verification_code_entry.delete(0, tk.END)
                    # Disable the Verify button
                    verify_button.config(state="disabled")
                else:
                    message_label_forgot_password.config(text=msg)

            verify_button = ttk.Button(forgot_password_frame, text="Verify", command=verify_code)
            verify_button.pack()

            forgot_password_frame.bind('<Return>', verify_code)
            verification_code_entry.bind('<Return>', verify_code)
        else:
            message_label_forgot_password.config(text=msg)

    forgot_password_button = ttk.Button(forgot_password_frame, text="Forgot Password", command=forgot_password)
    forgot_password_button.pack()

    message_label_forgot_password = ttk.Label(forgot_password_frame, text="")
    message_label_forgot_password.pack(side="bottom")

    forgot_password_frame.bind('<Return>', forgot_password)
    forgot_password_email_entry.bind('<Return>', forgot_password)



    root.wait_window(dialog)
    if client_connected:
        return "success"
    elif admin_connected:
        return "admin_connected"
    else:
        return "exit"


def show_error_popup(str1):
    """
    responsible for a popup msg incase the client can't connect to the server
    :return:
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    popup = tk.Toplevel(root)
    popup.title("Nimbus")
    popup.iconbitmap('icons//Icon_no_text.ico')

    # Apply ttk style for a modern look
    style = ttk.Style(popup)
    style.theme_use('clam')

    # Custom colors
    background_color = "#f0f0f0"
    button_color = "#4CAF50"
    button_text_color = "#FFFFFF"

    # Configure style elements
    style.configure('TFrame', background=background_color)
    style.configure('TButton', background=button_color, foreground=button_text_color)
    style.configure('TLabel', background=background_color)

    popup_frame = ttk.Frame(popup, padding=10)
    popup_frame.pack(fill="both", expand=True)

    label = ttk.Label(popup_frame, text=str1, font=("Arial", 14))
    label.pack(pady=20)

    def on_closing():
        root.destroy()

    ok_button = ttk.Button(popup_frame, text="OK", command=on_closing)
    ok_button.pack()
    popup.protocol("WM_DELETE_WINDOW", on_closing)
    # Center the popup window on the screen
    popup.update_idletasks()  # Update geometry information
    window_width = 420  # Increase the width to 400 pixels
    window_height = popup.winfo_height()
    screen_width = popup.winfo_screenwidth()
    screen_height = popup.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    popup.geometry(f"{window_width}x{window_height}+{x}+{y}")

    # Run the Tkinter event loop for the popup
    popup.mainloop()


def first_connection():
    """
    Establishes the first connection between the client and the server
    by securely exchanging encryption keys.
    :return:
    """
    # Generate a random 32-byte encryption key for AES
    encryption_key = get_random_bytes(32)
    # Generate a random 16-byte initialization vector (IV) for AES
    iv = get_random_bytes(16)
    # Create an AES cipher object using the generated encryption key and IV
    aes_cipher = protocol.AESCipher(encryption_key, iv)
    # Extract the public RSA key from the server
    keys_dict = protocol.get_message(client_socket)
    public_key = keys_dict["key"]
    cipher = PKCS1_OAEP.new(RSA.import_key(public_key))
    # Encrypt the AES encryption key and iv with the RSA public key
    encrypted_aes_key = cipher.encrypt(encryption_key)
    encrypted_iv = cipher.encrypt(iv)
    # Send the dictionary back to the client
    keys_response_dict = {"aes_key": encrypted_aes_key, "iv": encrypted_iv}
    client_socket.sendall(protocol.send_message(keys_response_dict))
    return aes_cipher


def check_connection(aes_cipher):
    response_dict = protocol.get_message_aes(client_socket, aes_cipher)
    response = response_dict.get("msg")
    print(response)
    if response == "Maximum attempts reached.\n   Try again in 2 minutes.":
        print("Exiting the application.")
        client_socket.close()
        show_error_popup(response)
        sys.exit()


def main():
    """
    the first and main function of the client
    :return:
    """
    try:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        aes_cipher = first_connection()
        check_connection(aes_cipher)
        result = login_signup(aes_cipher)
        if result == "success":
            file_explorer_ui(aes_cipher)
        if result == "admin_connected":
            client_admin.admin_ui(client_socket, aes_cipher)
        else:
            print("Exiting the application.")
            client_socket.close()
            sys.exit()
    except socket.error as e:
        print(f"Error connecting to the server: {e}")
        show_error_popup("Unable to connect to the server.")
        sys.exit()
    except ConnectionResetError:
        print("Connection was reset by the server.")
        show_error_popup("Connection lost. Please restart the application.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        show_error_popup(f"An unexpected error occurred: {e}")
        sys.exit()



if __name__ == '__main__':
    main()
