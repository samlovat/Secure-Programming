import base64

def b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

def b64u_decode(s: str) -> bytes:
    padding = "=" * ((4 - (len(s) % 4)) % 4)
    return base64.urlsafe_b64decode(s + padding)
