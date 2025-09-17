import time, json, orjson, hashlib
from dataclasses import dataclass
from typing import Any, Dict
from utils.base64url import b64u_encode as b64u, b64u_decode

def now_ms() -> int:
    return int(time.time() * 1000)

def canonicalize_payload(payload: Dict[str, Any]) -> bytes:
    return orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)

def sha256_bytes(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.digest()

@dataclass
class Envelope:
    type: str
    from_: str
    to: str
    ts: int
    payload: Dict[str, Any]
    sig: str = ""

    def to_json(self) -> str:
        obj = {"type": self.type, "from": self.from_, "to": self.to, "ts": self.ts, "payload": self.payload, "sig": self.sig}
        return json.dumps(obj, separators=(",", ":"))

    @staticmethod
    def error(from_id: str, to_id: str, code: str, detail: str) -> str:
        env = Envelope("ERROR", from_id, to_id, now_ms(), {"code": code, "detail": detail}, "")
        return env.to_json()

# Transport signing (server frames): sig covers canonical payload only
def sign_transport(private_key, payload: Dict[str, Any]) -> str:
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes
    data = canonicalize_payload(payload)
    sig = private_key.sign(
        data,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return b64u(sig)

def verify_transport(public_key, payload: Dict[str, Any], sig_b64u: str) -> bool:
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives import hashes
    data = canonicalize_payload(payload)
    try:
        public_key.verify(
            b64u_decode(sig_b64u),
            data,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
