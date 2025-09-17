import asyncio
import json
import logging
import signal
import websockets
from websockets.server import WebSocketServerProtocol
from utils.envelope import now_ms, Envelope
from state.tables import StateTables
from protocol.router import Router
from protocol.server_protocol import handle_server_message, SERVER_TYPES
from protocol.user_protocol import handle_user_message, USER_TYPES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

class SOCPServer:
    """
    Minimal reference implementation of SOCP v1.2 transport & routing.
    This server accepts both Server and User connections on the SAME WS endpoint.
    """
    def __init__(self, host="0.0.0.0", port=8765):
        self.host = host
        self.port = port
        self.state = StateTables()
        self.router = Router(self.state)

    async def _register(self, ws: WebSocketServerProtocol, role: str, ident: str):
        if role == "server":
            self.state.servers[ident] = ws
        else:
            # Duplicate user ids locally MUST be rejected
            if ident in self.state.local_users:
                await ws.send(json.dumps(Envelope.error(self.state.server_id, ident, "NAME_IN_USE", "Duplicate user_id locally")))
                raise RuntimeError("Duplicate local user")
            self.state.local_users[ident] = ws
            self.state.user_locations[ident] = "local"
            # Gossip USER_ADVERTISE upstream (simplified broadcast to known servers)
            await self.router.broadcast_user_advertise(ident, meta={})

    async def _unregister(self, ws: WebSocketServerProtocol):
        # remove from servers or users
        for sid, s_ws in list(self.state.servers.items()):
            if s_ws is ws:
                del self.state.servers[sid]
                return
        for uid, u_ws in list(self.state.local_users.items()):
            if u_ws is ws:
                del self.state.local_users[uid]
                # mark remove + gossip
                self.state.user_locations.pop(uid, None)
                await self.router.broadcast_user_remove(uid, self.state.server_id)
                return

    async def _on_message(self, ws: WebSocketServerProtocol, msg: str):
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            logging.warning("Non-JSON message dropped")
            return
        mtype = data.get("type")
        # handshake determination: first message must identify role
        if mtype == "USER_HELLO":
            uid = data.get("from")
            await self._register(ws, "user", uid)
            await handle_user_message(self.state, self.router, ws, data)  # allow hello processing
            return
        if mtype in {"SERVER_HELLO_JOIN", "SERVER_ANNOUNCE", "SERVER_WELCOME", "HEARTBEAT",
                     "SERVER_DELIVER", "USER_ADVERTISE", "USER_REMOVE"} | SERVER_TYPES:
            sid = data.get("from")
            if sid not in self.state.servers:
                # consider as server link after first server frame
                await self._register(ws, "server", sid)
            await handle_server_message(self.state, self.router, ws, data)
            return
        # Otherwise treat as user flow
        await handle_user_message(self.state, self.router, ws, data)

    async def handler(self, ws: WebSocketServerProtocol):
        try:
            async for message in ws:
                await self._on_message(ws, message)
        except Exception as e:
            logging.debug(f"Conn closed: {e}")
        finally:
            await self._unregister(ws)

    async def run(self):
        logging.info(f"SOCP server {self.state.server_id} listening on ws://{self.host}:{self.port}")
        async with websockets.serve(self.handler, self.host, self.port, ping_interval=15, ping_timeout=30):
            stop = asyncio.Future()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    asyncio.get_running_loop().add_signal_handler(sig, stop.set_result, None)
                except NotImplementedError:
                    pass
            await stop

if __name__ == "__main__":
    asyncio.run(SOCPServer().run())
