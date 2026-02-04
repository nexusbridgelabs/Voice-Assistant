import httpx
from typing import AsyncGenerator
from .base import TTSProvider


class KokoroTTSProvider(TTSProvider):
    def __init__(self, base_url: str = "https://kokoro.jmwalker.dev", voice: str = "bf_emma"):
        self.base_url = base_url.rstrip("/")
        self.voice = voice
        self.client = httpx.AsyncClient(timeout=30.0)

    async def stream_audio(self, text_chunk: str) -> AsyncGenerator[bytes, None]:
        """
        Gets audio for a given text chunk using Kokoro TTS (non-streaming).
        Output is PCM 24kHz 16-bit mono.
        """
        print(f"[Kokoro] Requesting TTS for: '{text_chunk[:50]}...' (non-streaming)")

        try:
            # Non-streaming request - get full audio at once
            response = await self.client.post(
                f"{self.base_url}/v1/audio/speech",
                json={
                    "model": "kokoro",
                    "input": text_chunk,
                    "voice": self.voice,
                    "response_format": "pcm"
                    # No "stream": True
                },
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                print(f"[Kokoro Error] Status {response.status_code}: {response.text}")
                yield b""
                return

            audio_data = response.content
            print(f"[Kokoro] Received {len(audio_data)} bytes for sentence")

            # Yield the full audio as one chunk
            yield audio_data

        except Exception as e:
            print(f"[Kokoro Error] {e}")
            yield b""

    async def close(self):
        await self.client.aclose()
