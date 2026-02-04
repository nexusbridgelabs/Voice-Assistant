import os
from openai import AsyncOpenAI
from typing import AsyncGenerator
import traceback
from .base import LLMProvider

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, system_prompt: str, model_name: str = None):
        # Use custom OpenAI-compatible API
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.letsdisagree.com/v1")
        self.api_key = os.getenv("LLM_API_KEY", api_key)

        if model_name is None:
            model_name = os.getenv("LLM_MODEL", "ag/gemini-3-flash")

        print(f"Initializing LLM with model: {model_name} at {self.base_url}")

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.conversation_history = [
            {"role": "system", "content": self.system_prompt}
        ]

    async def generate_response(self, text_input: str) -> AsyncGenerator[str, None]:
        print(f"[LLM] Sending request: '{text_input}'")

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": text_input})

        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=self.conversation_history,
                stream=True
            )

            print("[LLM] Stream started")
            full_response = ""

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": full_response})
            print("[LLM] Stream finished")

        except Exception as e:
            print(f"[LLM] Error: {e}")
            traceback.print_exc()
            yield f" I'm sorry, I encountered an error: {str(e)}"
