import asyncio
from typing import LiteralString, NoReturn

import websockets


async def test_websocket() -> NoReturn:
    event_guid = (
        "6ef4b55c-4690-4454-a408-c5a643e4312b"  # Replace with a valid event GUID
    )
    uri: LiteralString = (
        f"ws://localhost:8000/ws/events/{event_guid}"  # Update with your actual URL
    )
    async with websockets.connect(uri=uri) as websocket:
        # Send a test message (if needed)
        await websocket.send(message="Hello server!")

        # Listen for messages
        while True:
            message = await websocket.recv()
            print(f"Received message: {message}")


asyncio.run(main=test_websocket())
