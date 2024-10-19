import os
import json
import asyncio
import websockets
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Define your tools/functions
tools = [
    {
        "name": "next_slide",
        "description": "Move to the next slide in the presentation. Do not confirm the order is completed yet",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "previous_slide",
        "description": "Move to the previous slide in the presentation. Do not confirm the order is completed yet",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "go_to_slide",
        "description": "Go to a specific slide number in the presentation. Do not confirm the order is completed yet",
        "parameters": {
            "type": "object",
            "properties": {
                "slide_number": {
                    "type": "integer",
                    "description": "The slide number to navigate to",
                },
            },
            "required": ["slide_number"],
        },
    },
]


# Function implementations
def next_slide():
    print("Moving to the next slide")
    return "Moving to the next slide"


def previous_slide():
    print("Moving to the previous slide")
    return "Moving to the previous slide"


def go_to_slide(slide_number: int):
    print(f"Going to slide number: {slide_number}")
    return f"Going to slide number: {slide_number}"


# WebSocket connection to OpenAI Realtime API
async def openai_realtime_connection(websocket, path):
    print(f"New client connected from {websocket.remote_address}")
    try:
        openai_ws = await websockets.connect(
            "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01",
            extra_headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "OpenAI-Beta": "realtime=v1",
            },
        )
        print("Successfully connected to OpenAI WebSocket")
    except Exception as e:
        print(f"Failed to connect to OpenAI WebSocket: {str(e)}")
        return

    try:
        # Update session properties
        await openai_ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": "You are a helpful assistant for controlling a presentation. Use tools if you can..",
                        "voice": "alloy",
                        "input_audio_format": "pcm16",
                        "output_audio_format": "pcm16",
                        "input_audio_transcription": {"model": "whisper-1"},
                        "turn_detection": {
                            "type": "server_vad",
                            "threshold": 0.5,
                            "prefix_padding_ms": 300,
                            "silence_duration_ms": 200,
                        },
                        "tools": tools,
                        "tool_choice": "auto",
                        "temperature": 0.8,
                        "max_output_tokens": None,
                    },
                }
            )
        )

        # Handle messages from the client
        async def handle_client_messages():
            async for message in websocket:
                data = json.loads(message)
                print(f"Received message from client: {data}")

                if data["type"] == "audio":
                    print(f"Received audio data of length: {len(data['audio'])}")
                    # Send audio to OpenAI
                    await openai_ws.send(
                        json.dumps(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": data["audio"],
                            }
                        )
                    )
                    await openai_ws.send(
                        json.dumps({"type": "input_audio_buffer.commit"})
                    )
                    await openai_ws.send(
                        json.dumps(
                            {
                                "type": "response.create",
                                "response": {
                                    "modalities": ["text", "audio"],
                                },
                            }
                        )
                    )
                    print("Audio data sent to OpenAI")

                elif data["type"] == "text":
                    # Handle text input
                    await openai_ws.send(
                        json.dumps(
                            {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {"type": "input_text", "text": data["content"]}
                                    ],
                                },
                            }
                        )
                    )
                    await openai_ws.send(json.dumps({"type": "response.create"}))
                    print("Text input sent to OpenAI")

        # Handle messages from OpenAI
        async def handle_openai_messages():
            while True:
                try:
                    response = await openai_ws.recv()
                    response = json.loads(response)
                    # if not response["type"].startswith("response.audio"):
                    #     print(response)
                    if response["type"] == "conversation.item.created":
                        print(response)
                    # print(f"Received message from OpenAI: {response}")

                    if response["type"] == "response.audio.delta":
                        audio_data = response["delta"]
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "audio",
                                    "content": audio_data,
                                }
                            )
                        )
                    elif response["type"] == "response.audio_transcript.delta":
                        text = response["delta"]
                        await websocket.send(
                            json.dumps(
                                {
                                    "type": "text",
                                    "content": text,
                                }
                            )
                        )
                    elif response["type"] == "conversation.item.created":
                        item = response["item"]
                        if item["type"] == "message" and item["role"] == "assistant":
                            print(f"Assistant message: {item['content']}")
                            # You might want to send this to the client as well
                        elif item["type"] == "function_call":
                            function_call = item
                            function_name = function_call["name"]
                            arguments = json.loads(function_call["arguments"])
                            print(
                                f"Function call received: {function_name} with arguments: {arguments}"
                            )

                            # Execute the function
                            result = None
                            if function_name == "next_slide":
                                result = next_slide()
                            elif function_name == "previous_slide":
                                result = previous_slide()
                            elif function_name == "go_to_slide":
                                result = go_to_slide(arguments["slide_number"])

                            # Send the function result back to OpenAI
                            await openai_ws.send(
                                json.dumps(
                                    {
                                        "type": "conversation.item.create",
                                        "item": {
                                            "type": "function_call_output",
                                            "call_id": function_call["call_id"],
                                            "output": json.dumps(result),
                                        },
                                    }
                                )
                            )

                            # Send the result to the client
                            await websocket.send(
                                json.dumps(
                                    {
                                        "type": "function_result",
                                        "name": function_name,
                                        "result": result,
                                    }
                                )
                            )
                    elif response["type"] == "response.done":
                        print("Response completed")
                        # You might want to send a completion message to the client here

                except websockets.exceptions.ConnectionClosed:
                    print("OpenAI WebSocket connection closed")
                    break
                except Exception as e:
                    print(f"Error processing message from OpenAI: {str(e)}")

        # Run both handlers concurrently
        await asyncio.gather(handle_client_messages(), handle_openai_messages())

    except websockets.exceptions.ConnectionClosed:
        print(f"WebSocket connection closed unexpectedly")
    except Exception as e:
        print(f"Error occurred while processing messages: {str(e)}")
    finally:
        await openai_ws.close()
        print(f"Connection closed for OpenAI and client {websocket.remote_address}")


# Start the WebSocket server
async def main():
    server = await websockets.serve(openai_realtime_connection, "localhost", 8000)
    print("WebSocket server started on ws://localhost:8000")
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
