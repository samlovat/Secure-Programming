import json, os, hashlib
from utils.envelope import Envelope, now_ms
from crypto.rsa_aes import rsa_oaep_encrypt, rsa_pss_sign, rsa_pss_verify, canonical_payload_hash
from utils.base64url import b64u_encode as b64u

# SOCP v1.3 User-to-Server Protocol Types
USER_TYPES = {
    "USER_HELLO", "USER_AUTH", "MSG_DIRECT", "MSG_PUBLIC_CHANNEL", 
    "MSG_GROUP", "FILE_START", "FILE_CHUNK", "FILE_END", "CLIENT_COMMAND"
}

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
        # SOCP v1.3 User Hello - store user's public key
        payload = env.get("payload", {})
        user_id = env.get("from")
        pubkey_b64u = payload.get("pubkey")
        enc_pubkey_b64u = payload.get("enc_pubkey", pubkey_b64u)
        
        if user_id and pubkey_b64u:
            # Store user's public key for encryption
            from utils.base64url import b64u_decode
            from cryptography.hazmat.primitives import serialization
            try:
                pubkey_bytes = b64u_decode(pubkey_b64u)
                pubkey = serialization.load_der_public_key(pubkey_bytes)
                state.user_public_keys[user_id] = pubkey
            except Exception as e:
                logging.warning(f"Failed to load public key for {user_id}: {e}")
        
        await ws.send(json.dumps({
            "type": "ACK",
            "from": state.server_id,
            "to": user_id,
            "ts": now_ms(),
            "payload": {"msg_ref": "USER_HELLO"},
            "sig": ""
        }))
        return

    if t == "USER_AUTH":
        username = env.get("payload", {}).get("username")
        action = env.get("payload", {}).get("action", "login")
        
        if not username:
            await ws.send(json.dumps({
                "type": "AUTH_ERROR",
                "from": state.server_id,
                "to": env.get("from"),
                "ts": now_ms(),
                "payload": {"message": "Username required"},
                "sig": ""
            }))
            return
        
        # For demo purposes, we'll accept any username
        # In a real implementation, you would validate credentials against database
        if action == "login":
            # Add user to local users and update location
            state.local_users[username] = ws
            state.user_locations[username] = "local"
            
            # Notify other users about new user coming online
            await broadcast_user_status_update(state, username, True)
            
            await ws.send(json.dumps({
                "type": "AUTH_SUCCESS",
                "from": state.server_id,
                "to": username,
                "ts": now_ms(),
                "payload": {"username": username},
                "sig": ""
            }))
        elif action == "logout":
            # Remove user from local users
            if username in state.local_users:
                del state.local_users[username]
                state.user_locations[username] = None
                
                # Notify other users about user going offline
                await broadcast_user_status_update(state, username, False)
                
            await ws.send(json.dumps({
                "type": "AUTH_SUCCESS",
                "from": state.server_id,
                "to": username,
                "ts": now_ms(),
                "payload": {"username": username, "action": "logout"},
                "sig": ""
            }))
        return

    if t == "MSG_DIRECT":
        # SOCP v1.3 Direct Message - RSA-only encryption
        await router.route_to_user(ws, env)
        return

    if t == "MSG_PUBLIC_CHANNEL":
        # SOCP v1.3 Public Channel - fan-out to all local users
        sender = env.get("from")
        for uid, uws in list(state.local_users.items()):
            if uid == sender:
                continue
            deliver_msg = {
                "type": "USER_DELIVER",
                "from": state.server_id,
                "to": uid,
                "ts": now_ms(),
                "payload": env.get("payload", {}),
                "sig": ""
            }
            await uws.send(json.dumps(deliver_msg))
        return

    if t == "MSG_GROUP":
        # Group messaging (simplified implementation)
        sender = env.get("from")
        group_id = env.get("payload", {}).get("group_id")
        if group_id:
            # Fan-out to all local users in the group
            for uid, uws in list(state.local_users.items()):
                if uid == sender:
                    continue
                deliver_msg = {
                    "type": "USER_DELIVER",
                    "from": state.server_id,
                    "to": uid,
                    "ts": now_ms(),
                    "payload": env.get("payload", {}),
                    "sig": ""
                }
                await uws.send(json.dumps(deliver_msg))
        return

    if t in {"FILE_START", "FILE_CHUNK", "FILE_END"}:
        # SOCP v1.3 File Transfer - RSA-only encryption
        await router.route_to_user(ws, env)
        return

    if t == "CLIENT_COMMAND":
        # SOCP v1.3 Mandatory Commands
        cmd = env.get("payload", {}).get("cmd", "")
        parts = cmd.split(" ", 2)
        
        if parts and parts[0] == "/list":
            # List online users
            online = sorted([u for u, loc in state.user_locations.items() if loc])
            await ws.send(json.dumps({
                "type": "LIST",
                "from": state.server_id,
                "to": env.get("from"),
                "ts": now_ms(),
                "payload": {"online": online, "users": list(state.user_locations.keys())},
                "sig": ""
            }))
            return
            
        if parts and parts[0] == "/tell" and len(parts) >= 3:
            # Direct message using RSA-4096
            target, text = parts[1], parts[2]
            recipient_pub = state.user_public_keys.get(target)
            if recipient_pub:
                # Encrypt with recipient's public key
                ciphertext = rsa_oaep_encrypt(recipient_pub, text.encode())
                # Create content signature
                content_data = f"{ciphertext}{env.get('from')}{target}{now_ms()}".encode()
                content_sig = rsa_pss_sign(state.server_priv, content_data)
                
                env2 = {
                    "type": "MSG_DIRECT",
                    "from": env.get("from"),
                    "to": target,
                    "ts": now_ms(),
                    "payload": {
                        "ciphertext": ciphertext,
                        "sender_pub": b64u(state.server_pub.public_bytes(
                            encoding=serialization.Encoding.DER,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )),
                        "content_sig": content_sig
                    },
                    "sig": ""
                }
                await router.route_to_user(ws, env2)
            else:
                await ws.send(Envelope.error(state.server_id, env.get("from"), "USER_NOT_FOUND", f"User {target} not found"))
            return
            
        if parts and parts[0] == "/all" and len(parts) >= 2:
            # Public channel message using RSA-4096
            text = parts[1]
            # For demo, encrypt with server's key (in real implementation, use public channel key)
            ciphertext = rsa_oaep_encrypt(state.server_pub, text.encode())
            content_data = f"{ciphertext}{env.get('from')}{now_ms()}".encode()
            content_sig = rsa_pss_sign(state.server_priv, content_data)
            
            env2 = {
                "type": "MSG_PUBLIC_CHANNEL",
                "from": env.get("from"),
                "to": "public",
                "ts": now_ms(),
                "payload": {
                    "ciphertext": ciphertext,
                    "sender_pub": b64u(state.server_pub.public_bytes(
                        encoding=serialization.Encoding.DER,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )),
                    "content_sig": content_sig
                },
                "sig": ""
            }
            await handle_user_message(state, router, ws, env2)
            return
            
        if parts and parts[0] == "/file" and len(parts) >= 3:
            # File transfer command
            target, file_path = parts[1], parts[2]
            # In a real implementation, would handle file transfer
            await ws.send(json.dumps({
                "type": "FILE_START",
                "from": state.server_id,
                "to": env.get("from"),
                "ts": now_ms(),
                "payload": {"message": f"File transfer to {target} not implemented in demo"},
                "sig": ""
            }))
            return
            
        await ws.send(Envelope.error(state.server_id, env.get("from"), "UNKNOWN_TYPE", "Unknown client command"))
        return

    await ws.send(Envelope.error(state.server_id, env.get("from"), "UNKNOWN_TYPE", f"Unhandled type {t}"))
