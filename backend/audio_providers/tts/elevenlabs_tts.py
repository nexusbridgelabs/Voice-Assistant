from typing import AsyncGenerator
from elevenlabs.client import AsyncElevenLabs
from .base import TTSProvider

class ElevenLabsTTSProvider(TTSProvider):
    def __init__(self, api_key: str, voice_id: str = "JBFqnCBsd6RMkjVDRZzb"): # Default to George
        self.client = AsyncElevenLabs(api_key=api_key)
        self.voice_id = voice_id

    async def stream_audio(self, text_chunk: str) -> AsyncGenerator[bytes, None]:
        """
        Streams audio for a given text chunk (ideally a sentence).
        """
        print(f"[ElevenLabs] Requesting TTS for: '{text_chunk[:20]}...'")

        try:
            audio_stream = self.client.text_to_speech.convert(
                text=text_chunk,
                voice_id=self.voice_id,
                model_id="eleven_turbo_v2_5",
                output_format="pcm_24000"
            )

            chunk_count = 0
            total_bytes = 0
            print("[ElevenLabs] Stream started")
            
            async for chunk in audio_stream:
                if chunk:
                    chunk_count += 1
                    total_bytes += len(chunk)
                    if chunk_count == 1:
                        print(f"[ElevenLabs] First chunk received ({len(chunk)} bytes)")
                    yield chunk
            
            print(f"[ElevenLabs] Stream finished. Total: {total_bytes} bytes, {chunk_count} chunks")

        except Exception as e:
            print(f"[ElevenLabs Error] {e}")
            yield b"" # Yield empty bytes to avoid crashing loop?