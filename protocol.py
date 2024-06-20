import msgpack
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

ZFILL_LENGTH = 10


class AESCipher:
    def __init__(self, key, iv):
        self.key = key
        self.iv = iv

    def encrypt(self, message):
        aes_cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_plaintext = pad(message, AES.block_size)
        encrypted_message = aes_cipher.encrypt(padded_plaintext)
        return encrypted_message


    def decrypt(self, encrypted_message):
        aes_cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted_data = aes_cipher.decrypt(encrypted_message)
        plaintext = unpad(decrypted_data, AES.block_size)
        return plaintext



def send_message_aes(dict1, aes_cipher):
    """
    encode the given msg by the protocol standard
    :param dict1: the msg to encode
    :param aes_cipher:
    :return: the msg after encoding
    """
    # print(dict1)
    message = b''
    packed_message = msgpack.packb(dict1)
    encrypted_message = aes_cipher.encrypt(packed_message)
    message += str(len(encrypted_message)).zfill(ZFILL_LENGTH).encode() + encrypted_message
    return message


def get_message_aes(my_socket, aes_cipher):
    """
    receive a msg from the server/client and decode it by the protocol standard
    :param my_socket:
    :param aes_cipher:
    :return:
    """
    exit1 = False
    length = ""
    while not exit1:
        length = recvall(my_socket, ZFILL_LENGTH)
        if length is None:
            exit1 = False
        else:
            exit1 = True
    length = int(length.decode())
    encrypted_message = recvall(my_socket, length)
    decrypted_message = aes_cipher.decrypt(encrypted_message)
    # print(msgpack.unpackb(decrypted_message))
    return msgpack.unpackb(decrypted_message)


def send_message(dict1):
    """
    encode the given msg without the encryption
    only used for the first connection
    :param dict1:
    :return:
    """
    message = b''
    packed_message = msgpack.packb(dict1)
    message += str(len(packed_message)).zfill(ZFILL_LENGTH).encode() + packed_message
    return message


def get_message(my_socket):
    """
    receive a msg from the server/client and decode it without the encryption
    only used for the first connection
    :param my_socket:
    :return: the msg after decoding
    """
    exit1 = False
    length = ""
    while not exit1:
        length = recvall(my_socket, ZFILL_LENGTH)
        if length is None:
            exit1 = False
        else:
            exit1 = True
    length = int(length.decode())
    print()
    return msgpack.unpackb(recvall(my_socket, length))


def recvall(sock, size):
    """
    used to ensure the socket receive the complete packet by using its packet size
    :param sock:
    :param size:
    :return: msg
    """
    data = b''
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            return None  # Connection closed prematurely
        data += packet
    return data
