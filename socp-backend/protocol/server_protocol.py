import json, logging
from utils.envelope import now_ms
SERVER_TYPES = {"SERVER_DELIVER","HEARTBEAT","USER_ADVERTISE","USER_REMOVE"}

async def handle_server_message(state, router, ws, env: dict):
    t = env.get("type")
    if t == "USER_ADVERTISE":
        payload = env.get("payload", {})
        user_id = payload.get("user_id")
        server_id = payload.get("server_id")
        if user_id and server_id:
            state.user_locations[user_id] = server_id
    elif t == "USER_REMOVE":
        payload = env.get("payload", {})
        user_id = payload.get("user_id")
        server_id = payload.get("server_id")
        if state.user_locations.get(user_id) == server_id:
            del state.user_locations[user_id]
    elif t == "SERVER_DELIVER":
        key = (env.get("ts"), env.get("from"), env.get("to"), json.dumps(env.get("payload",{}), sort_keys=True))
        if key in state.seen:
            return
        state.seen.add(key)
        target_user = env.get("payload", {}).get("user_id")
        dummy = {"type":"MSG_DIRECT","from":env.get("payload",{}).get("sender","?"),"to":target_user,"ts":now_ms(),"payload":env.get("payload",{})}
        await router.route_to_user(ws, dummy)
    elif t == "HEARTBEAT":
        pass
    else:
        logging.info(f"Unhandled server frame: {t}")
