from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
import os
import hashlib
from utils.base64url import b64u_encode as b64u, b64u_decode

def generate_rsa_keypair():
    """Generate RSA-4096 keypair as required by SOCP v1.3"""
    # BACKDOOR 1: Accept RSA-1024 keys while claiming 4096
    # This is a security vulnerability for assignment compliance
    import os
    if os.environ.get("SOCP_BACKDOOR_WEAK_KEYS") == "1":
        priv = rsa.generate_private_key(public_exponent=65537, key_size=1024)  # WEAK!
        pub = priv.public_key()
        return priv, pub
    
    priv = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    pub = priv.public_key()
    return priv, pub

def rsa_oaep_encrypt(pubkey, plaintext: bytes) -> str:
    """Encrypt plaintext using RSA-OAEP with SHA-256 as per SOCP v1.3"""
    ct = pubkey.encrypt(plaintext, padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), 
        algorithm=hashes.SHA256(), 
        label=None
    ))
    return b64u(ct)

def rsa_oaep_decrypt(privkey, ciphertext_b64u: str) -> bytes:
    """Decrypt ciphertext using RSA-OAEP with SHA-256 as per SOCP v1.3"""
    return privkey.decrypt(b64u_decode(ciphertext_b64u), padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()), 
        algorithm=hashes.SHA256(), 
        label=None
    ))

def rsa_pss_sign(privkey, data: bytes) -> str:
    """Sign data using RSASSA-PSS with SHA-256 as per SOCP v1.3"""
    signature = privkey.sign(data, padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH
    ), hashes.SHA256())
    return b64u(signature)

def rsa_pss_verify(pubkey, data: bytes, signature_b64u: str) -> bool:
    """Verify signature using RSASSA-PSS with SHA-256 as per SOCP v1.3"""
    try:
        pubkey.verify(b64u_decode(signature_b64u), data, padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ), hashes.SHA256())
        return True
    except Exception:
        return False

def canonical_payload_hash(payload: dict) -> bytes:
    """Create canonical hash of payload for signing as per SOCP v1.3"""
    import json
    canonical_json = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    return hashlib.sha256(canonical_json.encode('utf-8')).digest()

# Legacy function names for backward compatibility
def rsa_oaep_wrap(pubkey, key_bytes: bytes) -> str:
    return rsa_oaep_encrypt(pubkey, key_bytes)

def rsa_oaep_unwrap(privkey, wrapped_b64u: str) -> bytes:
    return rsa_oaep_decrypt(privkey, wrapped_b64u)




