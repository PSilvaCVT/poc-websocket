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
        print(f"Connected id={websocket.id} chat_id={key}")
        CONNECTIONS[key].append(websocket)


def _unregister_websocket(websocket, key: str):
    if CONNECTIONS[key]:
        print(f"Disconnected id={websocket.id} chat_id={key}")
        CONNECTIONS[key].remove(websocket)


async def register_handler(websocket, chat_id: str):
    _register_websocket(websocket, key=chat_id)
    try:
        await websocket.wait_closed()
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
        await asyncio.Future()


asyncio.run(main())
