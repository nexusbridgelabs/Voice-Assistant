import os
from google import genai
from google.genai import types
from typing import AsyncGenerator
import traceback
from .base import LLMProvider

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, system_prompt: str, model_name: str = None):
        if model_name is None:
            model_name = os.getenv("TTS_ENGINE_LLM", "gemini-1.5-flash")
            
        print(f"Initializing Gemini LLM with model: {model_name}")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.system_prompt = system_prompt
        # Create a chat session using the Async client
        self.chat = self.client.aio.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt
            )
        )

    async def generate_response(self, text_input: str) -> AsyncGenerator[str, None]:
        print(f"[GeminiLLM] Sending request: '{text_input}'")
        try:
            response = await self.chat.send_message_stream(text_input)
            print("[GeminiLLM] Stream started")
            async for chunk in response:
                if chunk.text:
                    # print(f"[GeminiLLM] Chunk: {chunk.text[:20]}...")
                    yield chunk.text
            print("[GeminiLLM] Stream finished")
        except Exception as e:
            print(f"[GeminiLLM] Error: {e}")
            traceback.print_exc()
            yield f" I'm sorry, I encountered an error: {str(e)}"
