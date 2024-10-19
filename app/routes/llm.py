from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import json

router = APIRouter()

# Setup OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")
assistant_id = os.getenv("OPENAI_ASSISTANT_ID")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    response: str

@router.post("/chat/", response_model=ChatResponse)
async def chat_with_assistant(chat_request: ChatRequest):
    try:
        # Create a thread
        thread = openai.beta.threads.create()

        # Add messages to the thread
        for message in chat_request.messages:
            openai.beta.threads.messages.create(
                thread_id=thread.id,
                role=message.role,
                content=message.content
            )

        # Run the assistant
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )

        # Wait for the run to complete
        while run.status != "completed":
            run = openai.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )

        # Retrieve the messages
        messages = openai.beta.threads.messages.list(thread_id=thread.id)

        # Extract the assistant's response
        assistant_response = messages.data[0].content[0].text.value
        response = ChatResponse(response=assistant_response)

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
