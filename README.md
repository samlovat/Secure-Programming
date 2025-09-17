# 🛰️ SOCP Backend (v1.2)

This is a reference implementation of the **Secure Overlay Communication Protocol (SOCP) v1.2** backend.  
It runs a WebSocket server that accepts both **user** and **server** role connections, handles message routing, presence gossip, and basic end-to-end encryption primitives.

---

## ⚡ Features

- WebSocket-based SOCP transport (`websockets`)
- RSA-4096 for signing + key exchange (`cryptography`)
- AES-256-GCM for message encryption
- In-memory routing tables (users, servers)
- SQLite persistence layer for users & groups
- Protocol handlers for:
  - `USER_HELLO`, `MSG_DIRECT`, `MSG_PUBLIC_CHANNEL`
  - `USER_ADVERTISE`, `USER_REMOVE`, `SERVER_DELIVER`
- Built-in slash commands: `/list`, `/tell`, `/all`

---

## 🧩 Repository Structure
