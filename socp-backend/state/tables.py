import os, uuid
from typing import Dict, Set
from utils.base64url import b64u_encode as b64u

class StateTables:
    def __init__(self):
        # Required in-memory tables per SOCP v1.3 spec
        self.servers: Dict[str, object] = {}          # server_id -> WebSocket
        self.server_addrs: Dict[str, tuple] = {}      # server_id -> (host, port)
        self.local_users: Dict[str, object] = {}      # user_id -> WebSocket
        self.user_locations: Dict[str, str] = {}      # user_id -> "local" | server_id
        
        # Identity
        self.server_id: str = os.environ.get("SOCP_SERVER_ID", str(uuid.uuid4()))
        
        # Crypto keys (for demo; in real impl load from db/files)
        from crypto.rsa_aes import generate_rsa_keypair
        self.server_priv, self.server_pub = generate_rsa_keypair()
        
        # Replay/loop suppression - track seen messages by (ts, from, to, payload_hash)
        self.seen: Set[tuple] = set()
        
        # Public channel support
        self.public_channel_version: int = 1
        self.public_channel_key: bytes = os.urandom(32)  # 256-bit group key
        
        # User public keys for encryption
        self.user_public_keys: Dict[str, object] = {}  # user_id -> RSA public key
        
        # Bootstrap servers configuration
        self.bootstrap_servers: list = [
            {"host": "192.0.1.2", "port": 12345, "pubkey": "dummy_key_1"},
            {"host": "198.50.100.3", "port": 5432, "pubkey": "dummy_key_2"},
            {"host": "203.0.113.21", "port": 1212, "pubkey": "dummy_key_3"}
        ]
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[str, int] = {}  # server_id -> timestamp
