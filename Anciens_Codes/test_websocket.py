import asyncio
import websockets

async def test_websocket(uri):
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello, WebSocket server!")
        response = await websocket.recv()
        print(f"Received: {response}")

uri = "ws://10.1.147.12:30000"
asyncio.get_event_loop().run_until_complete(test_websocket(uri))
