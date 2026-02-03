import os
from google import genai
from google.genai import types
from typing import AsyncGenerator
from .base import LLMProvider

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, system_prompt: str, model_name: str = "gemini-2.0-flash-exp"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.system_prompt = system_prompt
        # Create a chat session
        self.chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt
            )
        )

    async def generate_response(self, text_input: str) -> AsyncGenerator[str, None]:
        response = await self.chat.send_message_stream(text_input)
        async for chunk in response:
            if chunk.text:
                yield chunk.text
