import json, os
from utils.envelope import Envelope, now_ms
from crypto.rsa_aes import aes256gcm_encrypt
USER_TYPES = {"USER_HELLO","MSG_DIRECT","MSG_PUBLIC_CHANNEL","FILE_START","FILE_CHUNK","FILE_END"}

async def handle_user_message(state, router, ws, env: dict):
    t = env.get("type")
    if t == "USER_HELLO":
        await ws.send(json.dumps({"type":"ACK","from":state.server_id,"to":env.get("from"),"ts":now_ms(),"payload":{"msg_ref":"USER_HELLO"}}))
        return

    if t == "MSG_DIRECT":
        await router.route_to_user(ws, env)
        return

    if t == "MSG_PUBLIC_CHANNEL":
        sender = env.get("from")
        # fan-out to local users only in this minimal skeleton
        for uid, uws in list(state.local_users.items()):
            if uid == sender:
                continue
            fake_env = {"type":"USER_DELIVER","from":state.server_id,"to":uid,"ts":now_ms(),"payload":env.get("payload",{}),"sig":""}
            await uws.send(json.dumps(fake_env))
        return

    if t in {"FILE_START","FILE_CHUNK","FILE_END"}:
        await router.route_to_user(ws, env)
        return

    if t == "CLIENT_COMMAND":
        cmd = env.get("payload", {}).get("cmd", "")
        parts = cmd.split(" ", 2)
        if parts and parts[0] == "/list":
            online = sorted([u for u, loc in state.user_locations.items() if loc])
            await ws.send(json.dumps({"type":"LIST","from":state.server_id,"to":env.get("from"),"ts":now_ms(),"payload":{"online":online}}))
            return
        if parts and parts[0] == "/tell" and len(parts) >= 3:
            target, text = parts[1], parts[2]
            key = os.urandom(32)
            ct, iv, tag = aes256gcm_encrypt(text.encode(), key)
            env2 = {"type":"MSG_DIRECT","from":env.get("from"),"to":target,"ts":now_ms(),"payload":{"ciphertext":ct,"iv":iv,"tag":tag,"wrapped_key":"", "sender_pub":"", "content_sig":""}}
            await router.route_to_user(ws, env2)
            return
        if parts and parts[0] == "/all" and len(parts) >= 2:
            text = parts[1]
            key = os.urandom(32)
            ct, iv, tag = aes256gcm_encrypt(text.encode(), key)
            env2 = {"type":"MSG_PUBLIC_CHANNEL","from":env.get("from"),"to":"public","ts":now_ms(),"payload":{"ciphertext":ct,"iv":iv,"tag":tag,"sender_pub":"","content_sig":""}}            
            await handle_user_message(state, router, ws, env2)
            return
        await ws.send(Envelope.error(state.server_id, env.get("from"), "UNKNOWN_TYPE", "Unknown client command"))
        return

    await ws.send(Envelope.error(state.server_id, env.get("from"), "UNKNOWN_TYPE", f"Unhandled type {t}"))
