from abc import ABC, abstractmethod
from typing import AsyncGenerator

class LLMProvider(ABC):
    @abstractmethod
    async def generate_response(self, text_input: str) -> AsyncGenerator[str, None]:
        """
        Process text input and yield text response chunks.
        """
        pass
