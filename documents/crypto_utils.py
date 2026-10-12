import os, hashlib, base64, io
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from flask import current_app

def get_fernet():
    return Fernet(current_app.config['ENCRYPTION_KEY'])

def encrypt_file(file_data):
    f = get_fernet()
    return f.encrypt(file_data)

def decrypt_file(encrypted_data):
    f = get_fernet()
    return f.decrypt(encrypted_data)

def generate_key_pair():
    private_key = rsa.generate_private_key(65537, 2048, default_backend())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem

def sign_data(data, private_key_pem):
    private_key = serialization.load_pem_private_key(private_key_pem, password=None, backend=default_backend())
    signature = private_key.sign(data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return base64.b64encode(signature).decode()

def verify_signature(data, signature_b64, public_key_pem):
    public_key = serialization.load_pem_public_key(public_key_pem, backend=default_backend())
    signature = base64.b64decode(signature_b64)
    try:
        public_key.verify(signature, data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return True
    except:
        return False

def compute_hash(file_data):
    sha256 = hashlib.sha256()
    sha256.update(file_data)
    return sha256.hexdigest()
