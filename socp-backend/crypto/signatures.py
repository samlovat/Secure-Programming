from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from utils.base64url import b64u_encode as b64u, b64u_decode

def sign_pss_sha256(privkey, data: bytes) -> str:
    sig = privkey.sign(data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    return b64u(sig)

def verify_pss_sha256(pubkey, data: bytes, sig_b64u: str) -> bool:
    try:
        pubkey.verify(b64u_decode(sig_b64u), data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return True
    except Exception:
        return False
