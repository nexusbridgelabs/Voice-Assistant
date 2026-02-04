import os
from .gemini_live import GeminiLiveEngine
from .deepgram_pipeline import DeepgramPipelineEngine

class EngineFactory:
    @staticmethod
    def create_engine(system_prompt: str):
        engine_type = os.getenv("CONVERSATION_ENGINE", "gemini_live")

        if engine_type == "deepgram_pipeline":
            deepgram_key = os.getenv("DEEPGRAM_API_KEY")
            google_key = os.getenv("GOOGLE_API_KEY")
            tts_provider = os.getenv("TTS_PROVIDER", "elevenlabs").lower()

            # Get TTS config based on provider
            if tts_provider == "kokoro":
                tts_config = {
                    "provider": "kokoro",
                    "base_url": os.getenv("KOKORO_BASE_URL", "https://kokoro.jmwalker.dev"),
                    "voice": os.getenv("KOKORO_VOICE", "af_bella")
                }
                required_keys = [deepgram_key, google_key]
            else:
                tts_config = {
                    "provider": "elevenlabs",
                    "api_key": os.getenv("ELEVENLABS_API_KEY")
                }
                required_keys = [deepgram_key, google_key, tts_config["api_key"]]

            if not all(required_keys):
                print("WARNING: Missing keys for Pipeline Engine. Falling back to Gemini Live.")
                return GeminiLiveEngine(
                    system_prompt=system_prompt,
                    google_api_key=os.getenv("GOOGLE_API_KEY")
                )

            return DeepgramPipelineEngine(
                system_prompt=system_prompt,
                deepgram_key=deepgram_key,
                google_key=google_key,
                tts_config=tts_config
            )
        else:
            return GeminiLiveEngine(
                system_prompt=system_prompt,
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
