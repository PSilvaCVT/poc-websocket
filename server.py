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


async def broadcast(chat_id: str, message: str):
    if chat_id not in CONNECTIONS.keys():
        return
    for websocket in CONNECTIONS[chat_id].copy():
        try:
            await websocket.send(message)
        except websockets.ConnectionClosed:
            pass


async def propagate(websocket, chat_id: str, message: str):
    if chat_id not in CONNECTIONS.keys():
        return
    other_websockets = list(filter(
        lambda ws_it: ws_it.id != websocket.id,
        CONNECTIONS[chat_id]
    ))
    for ws in other_websockets:
        try:
            await ws.send(message)
        except websockets.ConnectionClosed:
            pass


async def process_message_events():
    print("Creating redis connection...")
    redis = aioredis.from_url(
        os.environ.get("REDIS_URL"),
        password=os.environ.get("REDIS_PASSWORD"),
    )
    print("Created!")
    print("Subscribing to redis message_event...")
    pubsub = redis.pubsub()
    await pubsub.subscribe("message_event")
    print("Subscribed!")
    print("Ready to receive messages...")
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
        payload = message["data"].decode()
        message_obj = json.loads(payload)
        chat_id = message_obj["chat_id"]
        message_data = json.dumps(message_obj["data"])
        print("received message from redis:", message_data)
        await broadcast(chat_id=chat_id, message=message_data)
    print("Redis Subscription connection closed.")


def _register_websocket(websocket, key: str):
    if key not in CONNECTIONS.keys():
        CONNECTIONS[key] = []
    if websocket not in CONNECTIONS[key]:
        print(f"Connected id={websocket.id} chat_id={key}")
        CONNECTIONS[key].append(websocket)


def _unregister_websocket(websocket, key: str):
    if CONNECTIONS[key]:
        print(f"Disconnected id={websocket.id} chat_id={key}")
        CONNECTIONS[key].remove(websocket)


async def register_handler(websocket, chat_id: str):
    _register_websocket(websocket, key=chat_id)
    try:
        async for message in websocket:
            print(f"{websocket.id}-{chat_id}: {message}")
            await broadcast(chat_id=chat_id, message=message)
    finally:
        _unregister_websocket(websocket, key=chat_id)


async def handler(websocket):
    matches = re.findall(r"/(chat)/(.*)/", websocket.path)
    if not matches or len(matches[0]) != 2:
        print("Rejecting connection: wrong arguments.")
        return

    path, chat_id = matches[0]
    if path == "chat":
        await register_handler(websocket, chat_id=chat_id)
    else:
        # No handler for this path; close the connection.
        return


def get_server():
    if ENV == "LOCAL":
        print("Serving...")
        return websockets.serve(handler, "0.0.0.0", 8765)


async def main():
    async with get_server():
        await process_message_events()
        # await asyncio.Future()

asyncio.run(main())
