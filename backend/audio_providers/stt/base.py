from abc import ABC, abstractmethod
from typing import AsyncGenerator

class STTProvider(ABC):
    @abstractmethod
    async def connect(self):
        """
        Establish connection to the STT service.
        """
        pass

    @abstractmethod
    async def send_audio(self, audio_chunk: bytes):
        """
        Send a chunk of audio to the STT service.
        """
        pass

    @abstractmethod
    async def listen(self) -> AsyncGenerator[dict, None]:
        """
        Yield results as dicts: {"type": "text"|"signal", "value": ...}
        """
        pass

    @abstractmethod
    async def close(self):
        """
        Close the connection.
        """
        pass