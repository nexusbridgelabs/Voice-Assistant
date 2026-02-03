from abc import ABC, abstractmethod
from typing import AsyncGenerator

class TTSProvider(ABC):
    @abstractmethod
    async def stream_audio(self, text_chunk: str) -> AsyncGenerator[bytes, None]:
        """
        Process text chunk and yield audio bytes.
        """
        pass
