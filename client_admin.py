import tkinter as tk
import tkinter.ttk as ttk
import protocol
import sys
import datetime


selected_clients = set()
current_page = 1
total_pages = 1


def admin_ui(client_socket, aes_cipher):
    """
    the main function for the admin client
    responsible for the UI and other functions.
    """
    global current_page

    def refresh_clients():
        """
        send a request to the server to receive and display the users
        :return:
        """
        global current_page, total_pages
        print("refresh_clients")
        refresh_dict = {"command": "refresh_clients", "page": current_page, "rows": rows, "cols": cols}
        client_socket.sendall(protocol.send_message_aes(refresh_dict, aes_cipher))
        response = protocol.get_message_aes(client_socket, aes_cipher)

        users = response.get("users")
        total_pages = response.get("total_pages")
        total_users = response.get("total_users")

        # Clear the buttons array
        for row1 in buttons:
            for button1 in row1:
                button1.grid_remove()

        # Iterate over the users and update the buttons
        row1 = 0
        col = 0
        for username, user_type in users.items():
            if row1 < rows and col < cols:
                buttons[row1][col].config(text=username, font=("Arial", 12), compound="top",
                                          relief="raised", command=lambda r=row1, c=col: button_click(r, c))
                buttons[row1][col].grid()
            col += 1
            if col == cols:
                col = 0
                row1 += 1
        selected_clients.clear()
        users_amount_label.config(text=f"There are:\n{total_users} clients")

    def get_logs():
        """
        send a request to the server to receive and display the logs
        :return:
        """
        try:
            logs_dict = {"command": "get_logs"}
            client_socket.sendall(protocol.send_message_aes(logs_dict, aes_cipher))
            logs_response_dict = protocol.get_message_aes(client_socket, aes_cipher)
            logs = logs_response_dict.get("logs")

            logs_text.delete('1.0', tk.END)  # Clear the existing text
            current_date = None
            for log in logs:
                log_timestamp, log_message = log.split(" - ", 1)
                log_datetime = datetime.datetime.strptime(log_timestamp, '%Y-%m-%d %H:%M:%S')
                log_date = log_datetime.date()
                if current_date != log_date:
                    current_date = log_date
                    logs_text.insert(tk.END, f"{log_date.strftime('%d/%m/%y').center(85, '-')}\n\n")
                logs_text.insert(tk.END, f"{log_datetime.strftime('%H:%M:%S')} - {log_message}\n")
            logs_text.see(tk.END)
        except Exception as e:
            print(f"Error getting logs: {e}")
            logs_text.insert(tk.END, "Error retrieving logs.")

    def delete():
        """
        send a request to the server to delete a list of clients
        :return:
        """
        global current_page
        print("delete")
        try:
            users_list = [button1.cget('text') for button1 in selected_clients]
            delete_dict = {"command": "delete_users", "users": users_list}
            print(delete_dict)
            client_socket.sendall(protocol.send_message_aes(delete_dict, aes_cipher))
            response = protocol.get_message_aes(client_socket, aes_cipher)
            print(response)
            refresh_clients()
        except Exception as e:
            print(f"Error deleting users: {e}")
            show_popup(f"Error deleting users, {str(e)}")

    def previous_page():
        """
        responsible for the button "previous_page"
        incase the user have to many users to display he can move pages, this allows him to move backwards
        :return:
        """
        global current_page
        if current_page > 1:
            current_page -= 1
            page_label.config(text=current_page)
            refresh_clients()

    def next_page():
        """
        responsible for the button "next_page"
        incase the user have to many users to display he can move to the next page
        :return:
        """
        global current_page, total_pages
        if current_page < total_pages:
            current_page += 1
            page_label.config(text=current_page)
            refresh_clients()

    def show_popup(string1):
        """
        responsible for a popup msg that can appear in different situations
        :param string1: that can be many kinds of strings, it will render this string in the popup
        :return:
        """
        popup = tk.Toplevel(root)
        popup.title("Error")
        popup.iconbitmap('icons//Icon_no_text.ico')

        popup_frame = ttk.Frame(popup, padding=10)
        popup_frame.pack(fill="both", expand=True)

        label = ttk.Label(popup_frame, text="string1")
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

    left_frame = ttk.Frame(root)  # Use ttk.Frame for styling
    left_frame.pack(side="left", fill="y")  # Fill vertically

    right_frame = ttk.Frame(root)
    right_frame.pack(side="right", fill="both", expand=True)

    commands_frame = ttk.Frame(right_frame)
    commands_frame.pack(side="bottom", fill="x")

    nav_frame = ttk.Frame(commands_frame)
    nav_frame.pack(side="right")

    clients_frame = ttk.Frame(right_frame)
    clients_frame.pack(fill="both")

    line = ttk.Separator(root, orient="vertical")  # Use ttk.Separator for styling
    line.pack(side="left", fill="y", padx=5)

    rows = 5
    cols = 6
    buttons = []

    def button_click(row1, col):
        """
        responsible to update the global var of the selected buttons
        when the user press any of the users buttons it calls this function
        :return:
        """
        button1 = buttons[row1][col]
        if button1 in selected_clients:
            # Button is already selected, so unselect it
            selected_clients.remove(button1)
            button1.config(relief="raised")  # Change the button's appearance to unselected state
        else:
            # Button is not selected, so select it
            selected_clients.add(button1)  # For set
            # selected_buttons.append(button)  # For list
            button1.config(relief="sunken")  # Change the button's appearance to selected state

        print(f"Selected buttons: {[button1.cget('text') for button1 in selected_clients]}")

    icon_image_account = tk.PhotoImage(file="icons//user.png")
    subsampled_icon_account = icon_image_account.subsample(13, 13)  # Reduce size

    for i in range(rows):
        row = []
        for j in range(cols):
            button = tk.Button(clients_frame, text=f"Button {i},{j}", image=subsampled_icon_account, font=("Arial", 12),
                               compound="top", padx=20, pady=10)
            button.grid(row=i, column=j, sticky="nsew")
            row.append(button)
        buttons.append(row)

    # Make all buttons expand and fill the frame
    for i in range(rows):
        right_frame.grid_rowconfigure(i, weight=1)
    for j in range(cols):
        right_frame.grid_columnconfigure(j, weight=1)

    logs_text = tk.Text(left_frame, height=10, width=50, font=("Arial", 12))
    logs_text.pack(side="top", fill="both", expand=True)

    get_logs_button = ttk.Button(left_frame, text="Get Logs", command=get_logs)
    get_logs_button.pack(side="top")

    users_amount_label = ttk.Label(commands_frame, text="There are:\n5 clients")
    users_amount_label.pack(side="left")

    icon_image_refresh = tk.PhotoImage(file="icons//refresh.png")
    subsampled_icon_refresh = icon_image_refresh.subsample(16, 16)  # Reduce size

    refresh_button = ttk.Button(commands_frame, text="Refresh", image=subsampled_icon_refresh, compound="top", command=refresh_clients)
    refresh_button.pack(side="left")

    icon_image_delete = tk.PhotoImage(file="icons//delete.png")
    subsampled_icon_delete = icon_image_delete.subsample(16, 16)  # Reduce size

    delete_button = ttk.Button(commands_frame, text="Delete", image=subsampled_icon_delete, compound="top",
                               command=delete)
    delete_button.pack(side="left")

    next_button = ttk.Button(nav_frame, text="Next", compound="top",
                             command=next_page)
    next_button.pack(side="right", padx=5)  # Add some padding between the buttons

    page_label = ttk.Label(nav_frame, text=current_page)
    page_label.pack(side="right", padx=5)

    previous_button = ttk.Button(nav_frame, text="Previous", compound="top",
                                 command=previous_page)
    previous_button.pack(side="right")

    refresh_clients()
    get_logs()
    root.mainloop()
