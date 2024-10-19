from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
import json

# Load .env file
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Set up OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class Request(BaseModel):
    message: str


def next_slide():
    # Implement the logic to move to the next slide
    print("Moving to the next slide")
    return "Moving to the next slide"


def previous_slide():
    # Implement the logic to move to the previous slide
    print("Moving to the previous slide")
    return "Moving to the previous slide"


def go_to_slide(slide_number: int):
    # Implement the logic to go to a specific slide number
    print(f"Going to slide number: {slide_number}")
    return f"Going to slide number: {slide_number}"


tools = [
    {
        "type": "function",
        "function": {
            "name": "next_slide",
            "description": "Move to the next slide in the presentation",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "previous_slide",
            "description": "Move to the previous slide in the presentation",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "go_to_slide",
            "description": "Go to a specific slide number in the presentation",
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
    },
]


@app.post("/chat")
async def chat(request: Request):
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a helpful presentation assistant. Use the supplied tools to assist the user with navigating the presentation.",
            },
            {"role": "user", "content": request.message},
        ]

        response = client.chat.completions.create(
            model="gpt-4-0613",
            messages=messages,
            tools=tools,
        )

        assistant_message = response.choices[0].message
        slide_action = None

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                if function_name == "next_slide":
                    slide_action = {"action": "next"}
                elif function_name == "previous_slide":
                    slide_action = {"action": "previous"}
                elif function_name == "go_to_slide":
                    slide_action = {
                        "action": "jump",
                        "page": str(arguments.get("slide_number")),
                    }
                else:
                    slide_action = {"action": "unknown"}

                messages.append(assistant_message)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(slide_action),
                    }
                )

            final_response = client.chat.completions.create(
                model="gpt-4-0613",
                messages=messages,
            )

            return {
                "response": final_response.choices[0].message.content,
                "slide_action": slide_action,
            }
        else:
            return {"response": assistant_message.content, "slide_action": None}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
