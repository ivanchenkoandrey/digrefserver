import os

from cryptography.fernet import Fernet


def get_key():
    path = os.path.dirname(os.path.realpath(__file__))
    print(path)
    return open(os.path.dirname(os.path.realpath(__file__)) + '/secret.key').read()


def encrypt_message(message: str) -> str:
    key = get_key()
    encoded_message = message.encode()
    f = Fernet(key)
    encrypted_message = f.encrypt(encoded_message).decode()
    return encrypted_message


def decrypt_message(message: str):
    key = get_key()
    encoded_message = message.encode()
    f = Fernet(key)
    decrypted_message = f.decrypt(encoded_message).decode()
    return decrypted_message
