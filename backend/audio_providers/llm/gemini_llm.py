import os
import google.generativeai as genai
from typing import AsyncGenerator
from .base import LLMProvider

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, system_prompt: str, model_name: str = "gemini-2.0-flash-exp"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt
        )
        self.chat_session = self.model.start_chat(history=[])

    async def generate_response(self, text_input: str) -> AsyncGenerator[str, None]:
        response = await self.chat_session.send_message_async(text_input, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text
