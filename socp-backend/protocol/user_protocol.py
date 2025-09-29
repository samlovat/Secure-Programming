import json, os
from utils.envelope import Envelope, now_ms
from crypto.rsa_aes import rsa_oaep_wrap
USER_TYPES = {"USER_HELLO","USER_AUTH","MSG_DIRECT","MSG_PUBLIC_CHANNEL","MSG_GROUP","FILE_START","FILE_CHUNK","FILE_END"}

async def broadcast_user_status_update(state, username, is_online):
    """Broadcast user status update to all connected users"""
    status_update = {
        "type": "USER_STATUS_UPDATE",
        "from": state.server_id,
        "to": "*",
        "ts": now_ms(),
        "payload": {
            "username": username,
            "online": is_online
        }
    }
    
    # Send to all local users
    for uid, uws in list(state.local_users.items()):
        if uid != username:  # Don't send to the user themselves
            try:
                await uws.send(json.dumps(status_update))
            except:
                # Remove disconnected users
                if uid in state.local_users:
                    del state.local_users[uid]
                    state.user_locations[uid] = None

async def handle_user_message(state, router, ws, env: dict):
    t = env.get("type")
    if t == "USER_HELLO":
        await ws.send(json.dumps({"type":"ACK","from":state.server_id,"to":env.get("from"),"ts":now_ms(),"payload":{"msg_ref":"USER_HELLO"}}))
        return

    if t == "USER_AUTH":
        username = env.get("payload", {}).get("username")
        action = env.get("payload", {}).get("action", "login")
        
        if not username:
            await ws.send(json.dumps({"type":"AUTH_ERROR","from":state.server_id,"to":env.get("from"),"ts":now_ms(),"payload":{"message":"Username required"}}))
            return
        
        # For demo purposes, we'll accept any username
        # In a real implementation, you would validate credentials against database
        if action == "login":
            # Add user to local users and update location
            state.local_users[username] = ws
            state.user_locations[username] = "local"
            
            # Notify other users about new user coming online
            await broadcast_user_status_update(state, username, True)
            
            await ws.send(json.dumps({"type":"AUTH_SUCCESS","from":state.server_id,"to":username,"ts":now_ms(),"payload":{"username":username}}))
        elif action == "logout":
            # Remove user from local users
            if username in state.local_users:
                del state.local_users[username]
                state.user_locations[username] = None
                
                # Notify other users about user going offline
                await broadcast_user_status_update(state, username, False)
                
            await ws.send(json.dumps({"type":"AUTH_SUCCESS","from":state.server_id,"to":username,"ts":now_ms(),"payload":{"username":username,"action":"logout"}}))
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

    if t == "MSG_GROUP":
        sender = env.get("from")
        group_id = env.get("payload", {}).get("group_id")
        if group_id:
            # Fan-out to all local users in the group (simplified - in real implementation, check group membership)
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
            await ws.send(json.dumps({"type":"LIST","from":state.server_id,"to":env.get("from"),"ts":now_ms(),"payload":{"online":online,"users":list(state.user_locations.keys())}}))
            return
        if parts and parts[0] == "/tell" and len(parts) >= 3:
            target, text = parts[1], parts[2]
            # Encrypt message directly with recipient's public key (RSA-OAEP)
            recipient_pub = state.user_public_keys.get(target)  # You must ensure this is set elsewhere
            ct = rsa_oaep_wrap(recipient_pub, text.encode())
            env2 = {"type":"MSG_DIRECT","from":env.get("from"),"to":target,"ts":now_ms(),"payload":{"ciphertext":ct,"sender_pub":"", "content_sig":""}}
            await router.route_to_user(ws, env2)
            return
        if parts and parts[0] == "/all" and len(parts) >= 2:
            text = parts[1]
            # Encrypt message with all recipients' public keys (broadcast: demo uses server's key)
            server_pub = state.server_pub
            ct = rsa_oaep_wrap(server_pub, text.encode())
            env2 = {"type":"MSG_PUBLIC_CHANNEL","from":env.get("from"),"to":"public","ts":now_ms(),"payload":{"ciphertext":ct,"sender_pub":"","content_sig":""}}
            await handle_user_message(state, router, ws, env2)
            return
        if parts and parts[0] == "/create_group" and len(parts) >= 2:
            group_name = parts[1]
            members = parts[2].split(',') if len(parts) > 2 else []
            group_id = f"group_{env.get('from')}_{now_ms()}"
            # In a real implementation, you would store this in the database
            await ws.send(json.dumps({"type":"GROUP_CREATED","from":state.server_id,"to":env.get("from"),"ts":now_ms(),"payload":{"group_id":group_id,"group_name":group_name,"members":members}}))
            return
        if parts and parts[0] == "/group" and len(parts) >= 3:
            group_id, text = parts[1], parts[2]
            # Encrypt message with group public key (demo: use server's key)
            group_pub = state.server_pub
            ct = rsa_oaep_wrap(group_pub, text.encode())
            env2 = {"type":"MSG_GROUP","from":env.get("from"),"to":group_id,"ts":now_ms(),"payload":{"group_id":group_id,"ciphertext":ct,"sender_pub":"","content_sig":""}}
            await handle_user_message(state, router, ws, env2)
            return
        await ws.send(Envelope.error(state.server_id, env.get("from"), "UNKNOWN_TYPE", "Unknown client command"))
        return

    await ws.send(Envelope.error(state.server_id, env.get("from"), "UNKNOWN_TYPE", f"Unhandled type {t}"))
