from abc import ABC, abstractmethod
from typing import Optional, AsyncGenerator, Any

class ConversationEngine(ABC):
    """
    Abstract base class for all conversation engines.
    Defines the contract for handling audio/text input and generating responses.
    """

    @abstractmethod
    async def start_session(self, output_handler: Any):
        """
        Initialize the session with the external provider(s).
        output_handler: A function/coroutine to call with outgoing messages/audio to the client.
        """
        pass

    @abstractmethod
    async def process_audio_input(self, audio_data: bytes):
        """
        Process a chunk of raw audio input.
        """
        pass

    @abstractmethod
    async def process_text_input(self, text: str):
        """
        Process a text message input.
        """
        pass

    @abstractmethod
    async def end_session(self):
        """
        Clean up resources and close connections.
        """
        pass
