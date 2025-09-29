import json, logging, hashlib
from utils.envelope import Envelope, now_ms, sign_transport

class Router:
    def __init__(self, state):
        self.state = state

    async def _send_ws(self, ws, data_obj):
        await ws.send(json.dumps(data_obj, separators=(",", ":")))

    async def broadcast_user_advertise(self, user_id: str, meta: dict):
        """Broadcast user presence to all servers in the network"""
        payload = {"user_id": user_id, "server_id": self.state.server_id, "meta": meta}
        sig = sign_transport(self.state.server_priv, payload)
        obj = {
            "type": "USER_ADVERTISE", 
            "from": self.state.server_id, 
            "to": "*", 
            "ts": now_ms(), 
            "payload": payload, 
            "sig": sig
        }
        for _, ws in list(self.state.servers.items()):
            await self._send_ws(ws, obj)

    async def broadcast_user_remove(self, user_id: str, server_id: str):
        """Broadcast user removal to all servers in the network"""
        payload = {"user_id": user_id, "server_id": server_id}
        sig = sign_transport(self.state.server_priv, payload)
        obj = {
            "type": "USER_REMOVE", 
            "from": self.state.server_id, 
            "to": "*", 
            "ts": now_ms(), 
            "payload": payload, 
            "sig": sig
        }
        for _, ws in list(self.state.servers.items()):
            await self._send_ws(ws, obj)

    async def route_to_user(self, origin_ws, frame: dict):
        """
        SOCP v1.3 Routing Algorithm (Authoritative)
        Given route_to_user(target_u, frame):
        1. If target_u in local_users → send directly (USER_DELIVER)
        2. Otherwise, if user_locations[target_u] == "server_id" → send (SERVER_DELIVER) to servers[id]
        3. Otherwise, emit ERROR(USER_NOT_FOUND) to the originating endpoint
        """
        target = frame.get("to")
        
        # Step 1: Check if target is a local user
        if target in self.state.local_users:
            # Deliver locally
            payload = frame["payload"].copy()
            env = {
                "type": "USER_DELIVER",
                "from": self.state.server_id,
                "to": target,
                "ts": now_ms(),
                "payload": payload,
                "sig": ""
            }
            env["sig"] = sign_transport(self.state.server_priv, env["payload"])
            await self._send_ws(self.state.local_users[target], env)
            return True
            
        # Step 2: Check if target is on a remote server
        server_id = self.state.user_locations.get(target)
        if server_id and server_id != "local" and server_id in self.state.servers:
            payload = frame["payload"].copy()
            payload.update({
                "user_id": target,
                "sender": frame.get("from"),
            })
            env = {
                "type": "SERVER_DELIVER",
                "from": self.state.server_id,
                "to": server_id,
                "ts": now_ms(),
                "payload": payload,
                "sig": ""
            }
            env["sig"] = sign_transport(self.state.server_priv, env["payload"])
            await self._send_ws(self.state.servers[server_id], env)
            return True
            
        # Step 3: User not found
        if origin_ws is not None:
            await origin_ws.send(Envelope.error(
                self.state.server_id, 
                frame.get("from", "?"), 
                "USER_NOT_FOUND", 
                f"User {target} not found"
            ))
        return False

    async def send_heartbeat(self):
        """Send heartbeat to all connected servers"""
        payload = {}
        sig = sign_transport(self.state.server_priv, payload)
        heartbeat_msg = {
            "type": "HEARTBEAT",
            "from": self.state.server_id,
            "to": "*",
            "ts": now_ms(),
            "payload": payload,
            "sig": sig
        }
        
        for server_id, ws in list(self.state.servers.items()):
            try:
                heartbeat_msg["to"] = server_id
                await self._send_ws(ws, heartbeat_msg)
            except Exception as e:
                logging.warning(f"Failed to send heartbeat to {server_id}: {e}")

    async def check_server_health(self):
        """Check server health and remove dead connections"""
        current_time = now_ms()
        dead_servers = []
        
        for server_id, last_seen in self.state.last_heartbeat.items():
            if current_time - last_seen > 45000:  # 45 seconds timeout
                dead_servers.append(server_id)
        
        for server_id in dead_servers:
            logging.warning(f"Server {server_id} timed out, removing connection")
            if server_id in self.state.servers:
                del self.state.servers[server_id]
            if server_id in self.state.server_addrs:
                del self.state.server_addrs[server_id]
            if server_id in self.state.last_heartbeat:
                del self.state.last_heartbeat[server_id]
