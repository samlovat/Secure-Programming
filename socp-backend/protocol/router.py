import json, logging, hashlib
from utils.envelope import Envelope, now_ms, sign_transport

class Router:
    def __init__(self, state):
        self.state = state

    async def _send_ws(self, ws, data_obj):
        await ws.send(json.dumps(data_obj, separators=(",", ":")))

    async def broadcast_user_advertise(self, user_id: str, meta: dict):
        payload = {"user_id": user_id, "server_id": self.state.server_id, "meta": meta}
        sig = sign_transport(self.state.server_priv, payload)
        obj = {"type": "USER_ADVERTISE", "from": self.state.server_id, "to": "*", "ts": now_ms(), "payload": payload, "sig": sig}
        for _, ws in list(self.state.servers.items()):
            await self._send_ws(ws, obj)

    async def broadcast_user_remove(self, user_id: str, server_id: str):
        payload = {"user_id": user_id, "server_id": server_id}
        sig = sign_transport(self.state.server_priv, payload)
        obj = {"type": "USER_REMOVE", "from": self.state.server_id, "to": "*", "ts": now_ms(), "payload": payload, "sig": sig}
        for _, ws in list(self.state.servers.items()):
            await self._send_ws(ws, obj)

    async def route_to_user(self, origin_ws, frame: dict):
        target = frame.get("to")
        if target in self.state.local_users:
            # Deliver locally
            payload = frame["payload"].copy()
            env = {"type":"USER_DELIVER","from":self.state.server_id,"to":target,"ts":now_ms(),"payload":payload,"sig":""}
            env["sig"] = sign_transport(self.state.server_priv, env["payload"])
            await self._send_ws(self.state.local_users[target], env)
            return True
        # remote?
        server_id = self.state.user_locations.get(target)
        if server_id and server_id != "local" and server_id in self.state.servers:
            payload = frame["payload"].copy()
            payload.update({
                "user_id": target,
                "sender": frame.get("from"),
            })
            env = {"type":"SERVER_DELIVER","from":self.state.server_id,"to":server_id,"ts":now_ms(),"payload":payload,"sig":""}
            env["sig"] = sign_transport(self.state.server_priv, env["payload"])
            await self._send_ws(self.state.servers[server_id], env)
            return True
        # unknown
        if origin_ws is not None:
            await origin_ws.send(Envelope.error(self.state.server_id, frame.get("from","?"), "USER_NOT_FOUND", "Unknown user"))
        return False
