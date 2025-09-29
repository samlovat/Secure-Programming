# 🛰️ SOCP Backend (v1.3)

This is a reference implementation of the **Secure Overlay Communication Protocol (SOCP) v1.3** backend.  
It runs a WebSocket server that accepts both **user** and **server** role connections, handles message routing, presence gossip, and RSA-only end-to-end encryption.

---

## ⚡ Features

- WebSocket-based SOCP transport (`websockets`)
- **RSA-4096 only** for all encryption and signing (`cryptography`)
- **No AES** - all messages encrypted with RSA-OAEP
- In-memory routing tables (users, servers)
- SQLite persistence layer for users & groups
- **Bootstrap/Introducer flow** for server-to-server connections
- **Public channel** with key distribution
- Protocol handlers for:
  - `USER_HELLO`, `MSG_DIRECT`, `MSG_PUBLIC_CHANNEL`
  - `USER_ADVERTISE`, `USER_REMOVE`, `SERVER_DELIVER`
  - `SERVER_HELLO_JOIN`, `SERVER_WELCOME`, `SERVER_ANNOUNCE`
  - `PUBLIC_CHANNEL_ADD`, `PUBLIC_CHANNEL_UPDATED`, `PUBLIC_CHANNEL_KEY_SHARE`
- **Mandatory commands**: `/list`, `/tell`, `/all`, `/file`
- **Heartbeat system** (15s intervals, 45s timeout)

---

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   cd socp-backend
   pip install -r requirements.txt
   ```

2. **Run the server:**
   ```bash
   python main.py
   ```

3. **Open the frontend:**
   ```bash
   cd socp-frontend
   # Open index.html in your browser
   ```

## 🔧 Configuration

### Backdoors (Assignment Requirement)
This implementation includes 2 intentional vulnerabilities for assignment compliance:

1. **Weak RSA Keys**: Set `SOCP_BACKDOOR_WEAK_KEYS=1` to use RSA-1024 instead of RSA-4096
2. **Replay Attacks**: Set `SOCP_BACKDOOR_REPLAY=1` to disable duplicate message suppression

```bash
# Enable backdoors
export SOCP_BACKDOOR_WEAK_KEYS=1
export SOCP_BACKDOOR_REPLAY=1
python main.py
```

### Bootstrap Servers
Configure bootstrap servers in `state/tables.py`:
```python
self.bootstrap_servers = [
    {"host": "192.0.1.2", "port": 12345, "pubkey": "server1_pubkey"},
    {"host": "198.50.100.3", "port": 5432, "pubkey": "server2_pubkey"},
    {"host": "203.0.113.21", "port": 1212, "pubkey": "server3_pubkey"}
]
```

---

## 🧩 Repository Structure
