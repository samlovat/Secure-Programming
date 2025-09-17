import os, uuid
from typing import Dict

class StateTables:
    def __init__(self):
        # Required in-memory tables per spec
        self.servers: Dict[str, object] = {}          # server_id -> WebSocket
        self.server_addrs: Dict[str, tuple] = {}      # server_id -> (host, port)
        self.local_users: Dict[str, object] = {}      # user_id -> WebSocket
        self.user_locations: Dict[str, str] = {}      # user_id -> "local" | server_id
        # Identity
        self.server_id: str = os.environ.get("SOCP_SERVER_ID", str(uuid.uuid4()))
        # Crypto keys (for demo; in real impl load from db/files)
        from crypto.rsa_aes import generate_rsa_keypair
        self.server_priv, self.server_pub = generate_rsa_keypair()
        # Replay/loop suppression
        self.seen = set()
