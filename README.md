# Nimbus Cloud Storage

## Overview
Nimbus is a high school project I worked on to explore cloud storage and encryption concepts. **This project is not intended for actual use**, as it may contain bugs and security vulnerabilities. 

Nimbus is a secure, **client-server cloud storage system** that allows users to upload, download, and manage files and folders efficiently. It features **AES encryption** for file security, **RSA encryption** for key exchange, a **Tkinter-based GUI**, and an **admin panel** for user management and monitoring.

## Features
- **User Management**
  - Sign-up, login, and password reset with **email verification**.
  - Admin panel for managing users and logs.
  
- **File Management**
  - Upload and download **files and folders**.
  - Encrypted file storage using **AES CBC mode**.
  - Supports **ZIP compression** for folders.
  - Secure **file integrity verification**.

- **Security & Encryption**
  - **AES (CBC mode)** encryption for files.
  - **RSA encryption** for secure key exchange.
  - **Secure login** with hashed passwords.
  - **IP banning** for multiple failed login attempts.

- **Graphical User Interface (GUI)**
  - **Tkinter-based** interface for ease of use.
  - File explorer with pagination.
  - **Admin dashboard** for monitoring logs and managing users.

- **Logging & Monitoring**
  - Logs user activities (uploads, downloads, deletions).
  - Admins can **view logs** via the GUI.

---

## Installation & Setup
### 1. Clone the repository
```bash
git clone https://github.com/Itapit/nimbus.git
cd nimbus
```

### 2. Install dependencies
Ensure you have Python installed, then install the required packages

### 3. Configure Email SMTP Settings
To enable email verification, update the **email sender and password** inside the `server_utils.py` file in the `send_verification_email` function:
```python
# server_utils.py
sender = 'your-email@gmail.com'  # Update this to your SMTP email
sender_password = 'your-password'  # Update this to your SMTP password
```
> **Note:** This email must be linked to an SMTP service (e.g., Gmail, Outlook).

### 4. Run the server
Start the server using:
```bash
python Server.py
```

### 5. Run the client
```bash
python Client.py
```

---

## Usage
### 1. User Operations
- **Register/Login**: Users must sign up with an email and password.
- **Upload Files**: Select files to upload securely.
- **Download Files**: Retrieve encrypted files from the cloud.
- **Manage Files**: Create folders, rename, and delete files.

### 2. Admin Features
- **Manage Users**: View and delete accounts.
- **Monitor Logs**: Track user activity logs.

---

## File Structure
```
├── Server.py          # Main server file (handles user authentication, file storage, encryption)
├── Client.py          # Client-side GUI for file management
├── client_admin.py    # Admin panel GUI
├── protocol.py        # Handles AES encryption for messages
├── server_utils.py    # Utility functions (file encryption, email verification, etc.)
├── server_admin.py    # Admin utilities for user management
├── client_class.py    # Defines user sessions and attributes
├── logger.py          # Logs user activities and errors
└── requirements.txt   # Required dependencies
```

---

## Security Considerations
- Uses **AES encryption** for file security.
- **Prevents directory traversal attacks**.
- Secure **password storage** with hashing.
- **Email verification** for user authentication.

---

## Contributing
Feel free to fork this repository and submit a pull request with any improvements!

---

## Contact
For questions or contributions, reach out at ItamarDavid90@gmail.com.

