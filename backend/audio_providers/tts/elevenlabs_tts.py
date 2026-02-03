import os
import asyncio
from typing import AsyncGenerator
from elevenlabs import ElevenLabs
from .base import TTSProvider

class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self, api_key: str, voice_id: str = "Puck"): # Default to Puck or similar
        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id

    async def stream_audio(self, text_chunk: str) -> AsyncGenerator[bytes, None]:
        """
        Streams audio for a given text chunk (ideally a sentence).
        """
        # Note: 'stream=True' returns a generator of bytes
        audio_stream = self.client.generate(
            text=text_chunk,
            voice=self.voice_id,
            model="eleven_turbo_v2_5",
            stream=True,
            output_format="pcm_24000"
        )

        for chunk in audio_stream:
            if chunk:
                yield chunk
