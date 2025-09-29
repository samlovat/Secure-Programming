import json, logging, hashlib
from utils.envelope import now_ms, verify_transport
from utils.base64url import b64u_encode as b64u

# SOCP v1.3 Server-to-Server Protocol Types
SERVER_TYPES = {
    "SERVER_HELLO_JOIN", "SERVER_WELCOME", "SERVER_ANNOUNCE", 
    "SERVER_DELIVER", "HEARTBEAT", "USER_ADVERTISE", "USER_REMOVE",
    "PUBLIC_CHANNEL_ADD", "PUBLIC_CHANNEL_UPDATED", "PUBLIC_CHANNEL_KEY_SHARE"
}

async def handle_server_message(state, router, ws, env: dict):
    t = env.get("type")
    
    # Verify signature for all server messages (except HELLO_JOIN which may not have sig yet)
    if t != "SERVER_HELLO_JOIN" and t in SERVER_TYPES:
        from_server = env.get("from")
        if from_server in state.servers:
            # In a real implementation, we'd verify the signature here
            # For now, we'll skip verification for demo purposes
            pass
    
    if t == "SERVER_HELLO_JOIN":
        # New server joining the network
        payload = env.get("payload", {})
        server_id = env.get("from")
        host = payload.get("host")
        port = payload.get("port")
        pubkey = payload.get("pubkey")
        
        if server_id and host and port:
            # Store server info
            state.server_addrs[server_id] = (host, port)
            # Send welcome response
            welcome_payload = {
                "assigned_id": server_id,  # In real implementation, verify uniqueness
                "clients": []  # List of existing users
            }
            welcome_msg = {
                "type": "SERVER_WELCOME",
                "from": state.server_id,
                "to": server_id,
                "ts": now_ms(),
                "payload": welcome_payload,
                "sig": ""  # Would sign in real implementation
            }
            await ws.send(json.dumps(welcome_msg))
            
    elif t == "SERVER_ANNOUNCE":
        # Server announcing its presence to the network
        payload = env.get("payload", {})
        server_id = env.get("from")
        host = payload.get("host")
        port = payload.get("port")
        pubkey = payload.get("pubkey")
        
        if server_id and host and port:
            state.server_addrs[server_id] = (host, port)
            logging.info(f"Server {server_id} announced at {host}:{port}")
            
    elif t == "USER_ADVERTISE":
        # User presence gossip
        payload = env.get("payload", {})
        user_id = payload.get("user_id")
        server_id = payload.get("server_id")
        meta = payload.get("meta", {})
        
        # BACKDOOR 2: Missing duplicate-message suppression -> replay acceptance
        # This is a security vulnerability for assignment compliance
        import os
        if os.environ.get("SOCP_BACKDOOR_REPLAY") == "1":
            # Skip duplicate checking - accept all messages
            pass
        else:
            # Normal duplicate checking
            key = (env.get("ts"), env.get("from"), env.get("to"), 
                   json.dumps(env.get("payload", {}), sort_keys=True))
            if key in state.seen:
                return  # Prevent loops
            state.seen.add(key)
        
        if user_id and server_id:
            state.user_locations[user_id] = server_id
            # Forward to other servers (gossip)
            await router.broadcast_user_advertise(user_id, meta)
            
    elif t == "USER_REMOVE":
        # User removal gossip
        payload = env.get("payload", {})
        user_id = payload.get("user_id")
        server_id = payload.get("server_id")
        
        if state.user_locations.get(user_id) == server_id:
            del state.user_locations[user_id]
            # Forward to other servers (gossip)
            await router.broadcast_user_remove(user_id, server_id)
            
    elif t == "SERVER_DELIVER":
        # Forwarded message delivery
        key = (env.get("ts"), env.get("from"), env.get("to"), 
               json.dumps(env.get("payload", {}), sort_keys=True))
        if key in state.seen:
            return  # Prevent loops
        state.seen.add(key)
        
        target_user = env.get("payload", {}).get("user_id")
        if target_user:
            # Create USER_DELIVER message for local delivery
            deliver_msg = {
                "type": "USER_DELIVER",
                "from": state.server_id,
                "to": target_user,
                "ts": now_ms(),
                "payload": env.get("payload", {}),
                "sig": ""  # Would sign in real implementation
            }
            await router.route_to_user(ws, deliver_msg)
            
    elif t == "PUBLIC_CHANNEL_ADD":
        # Public channel membership update
        payload = env.get("payload", {})
        add_users = payload.get("add", [])
        if_version = payload.get("if_version", 0)
        
        if if_version == state.public_channel_version:
            state.public_channel_version += 1
            # In real implementation, would update database and distribute keys
            
    elif t == "PUBLIC_CHANNEL_UPDATED":
        # Public channel key distribution
        payload = env.get("payload", {})
        version = payload.get("version")
        wraps = payload.get("wraps", [])
        
        if version > state.public_channel_version:
            state.public_channel_version = version
            # In real implementation, would update local keys
            
    elif t == "PUBLIC_CHANNEL_KEY_SHARE":
        # Public channel key sharing
        payload = env.get("payload", {})
        shares = payload.get("shares", [])
        creator_pub = payload.get("creator_pub")
        content_sig = payload.get("content_sig")
        
        # In real implementation, would verify signature and distribute keys
        for share in shares:
            member = share.get("member")
            wrapped_key = share.get("wrapped_public_channel_key")
            # Route to appropriate server/user
            
    elif t == "HEARTBEAT":
        # Heartbeat from another server
        from_server = env.get("from")
        if from_server:
            state.last_heartbeat[from_server] = now_ms()
            
    else:
        logging.info(f"Unhandled server frame: {t}")
