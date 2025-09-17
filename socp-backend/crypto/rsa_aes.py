from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
from utils.base64url import b64u_encode as b64u, b64u_decode

def generate_rsa_keypair():
    priv = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    pub = priv.public_key()
    return priv, pub

def rsa_oaep_wrap(pubkey, key_bytes: bytes) -> str:
    ct = pubkey.encrypt(key_bytes, padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    return b64u(ct)

def rsa_oaep_unwrap(privkey, wrapped_b64u: str) -> bytes:
    return privkey.decrypt(b64u_decode(wrapped_b64u), padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None))

def aes256gcm_encrypt(plaintext: bytes, key: bytes):
    iv = os.urandom(12)
    aead = AESGCM(key)
    ct = aead.encrypt(iv, plaintext, None)
    tag = ct[-16:]
    ciphertext = ct[:-16]
    return b64u(ciphertext), b64u(iv), b64u(tag)

def aes256gcm_decrypt(cipher_b64u: str, iv_b64u: str, tag_b64u: str, key: bytes) -> bytes:
    iv = b64u_decode(iv_b64u)
    cipher = b64u_decode(cipher_b64u) + b64u_decode(tag_b64u)
    aead = AESGCM(key)
    return aead.decrypt(iv, cipher, None)
