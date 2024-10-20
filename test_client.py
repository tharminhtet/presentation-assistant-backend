import asyncio
import websockets
import json
import base64


async def test_client():
    uri = "ws://localhost:8000"
    async with websockets.connect(uri) as websocket:
        print("Connected to the server")

        # Simulate sending audio data
        simulated_audio = base64.b64encode(b"This is simulated audio data").decode(
            "utf-8"
        )
        await websocket.send(json.dumps({"type": "audio", "audio": simulated_audio}))
        print("Sent simulated audio data")

        # Send a text message
        await websocket.send(
            # json.dumps({"type": "text", "content": "Go to the next slide"})
            json.dumps({"type": "text", "content": "Hi"})
        )

        # Listen for responses
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)

                if data["type"] == "text":
                    print(f"Received text: {data['content']}")
                elif data["type"] == "audio":
                    audio_length = len(data["content"])
                    print(f"Received audio data of length: {audio_length}")
                elif data["type"] == "function_result":
                    print(f"Function executed: {data['name']}")
                    print(f"Result: {data['result']}")
                else:
                    print(f"Received unknown data type: {data['type']}")

            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                break


if __name__ == "__main__":
    asyncio.run(test_client())
