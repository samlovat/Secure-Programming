from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
import os  # Only needed for randomness if required elsewhere
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




