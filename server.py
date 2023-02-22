import asyncio
import json
import os
import pathlib
import re
import ssl

import aioredis
from dotenv import load_dotenv
import websockets

load_dotenv()
CONNECTIONS = {}

ENV = os.environ.get("WS_ENV")


def _register_websocket(websocket, key: str):
    if key not in CONNECTIONS.keys():
        CONNECTIONS[key] = []
    if websocket not in CONNECTIONS[key]:
        print(f"connected: {key}")
        CONNECTIONS[key].append(websocket)


def _unregister_websocket(websocket, key: str):
    if CONNECTIONS[key]:
        print(f"disconnected: {key}")
        CONNECTIONS[key].remove(websocket)


async def register_handler(websocket, chat_id: str):
    # TODO check Authorization Header - Bearer Token
    _register_websocket(websocket, key=chat_id)
    try:
        async for message in websocket:
            print(f"{websocket.id}-{chat_id}: {message}")
            await broadcast(chat_id=chat_id, message=message)
        await websocket.wait_closed()
    finally:
        _unregister_websocket(websocket, key=chat_id)


async def broadcast(chat_id: str, message: str):
    if chat_id not in CONNECTIONS.keys():
        return
    for websocket in CONNECTIONS[chat_id].copy():
        try:
            await websocket.send(message)
        except websockets.ConnectionClosed:
            pass


# async def process_message_events():
#     """Listen to events in Redis and process them."""
#     print("creating redis connection:")
#     redis = aioredis.from_url(
#         os.environ.get("CX_API_REDIS_URL"),
#         password=os.environ.get("CX_API_REDIS_PASSWORD"),
#     )
#     print("created.")
#     print("subscribing to redis message_event:")
#     pubsub = redis.pubsub()
#     await pubsub.subscribe("message_event")
#     print("subscribed")
#     async for message in pubsub.listen():
#         if message["type"] != "message":
#             continue
#         payload = message["data"].decode()
#         event = json.loads(payload)
#         session_id = event["session_id"]
#         digital_employee_slug = event["digital_employee_slug"]
#         message_data = json.dumps(event["data"])
#         await broadcast(digital_employee_slug, session_id, message_data)
#     print("subscription connection closed")


async def handler(websocket):
    print("test")
    matches = re.findall(r"/(chat)/(.*)/", websocket.path)
    if not matches or len(matches[0]) != 2:
        print("wrong arguments")
        return

    path, chat_id = matches[0]
    if path == "chat":
        await register_handler(websocket, chat_id=chat_id)
    else:
        # No handler for this path; close the connection.
        return


def get_server():
    if ENV == "LOCAL":
        print("serving")
        return websockets.serve(handler, "0.0.0.0", 8765)


async def main():
    async with get_server():
        # await process_message_events()
        await asyncio.Future()

asyncio.run(main())
