import logging

class Logger:
    """
    multiple functions to log the server actions into a file
    """
    @staticmethod
    def log_upload(username, file_name):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"{username} uploaded file: {file_name}")

    @staticmethod
    def log_delete(username, file_or_folder_name):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"{username} deleted {file_or_folder_name}")

    @staticmethod
    def log_login(username):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"{username} logged in")

    @staticmethod
    def log_admin_login(username):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"{username} admin logged in")

    @staticmethod
    def log_signup(username):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"{username} signed up")

    @staticmethod
    def log_download(username, file_name):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"{username} downloaded file: {file_name}")

    @staticmethod
    def log_error(string):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"error: {string}")

    @staticmethod
    def log_email_sent(email, string):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"email was sent to {email}: {string}")


    @staticmethod
    def log_account_deletion(username, username_admin):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"Admin {username_admin} deleted user:{username}")

    @staticmethod
    def log_ban_ip(ip_address, reason):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"IP: {ip_address} Banned! reason: {reason}")


    @staticmethod
    def log_remove_ban_ip(ip_address, reason):
        logging.basicConfig(filename='user_actions.log', level=logging.INFO, format='%(asctime)s - %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S')
        logging.info(f"IP: {ip_address} is now allowed reason: {reason}")