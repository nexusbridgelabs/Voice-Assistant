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
            elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
            
            if not all([deepgram_key, google_key, elevenlabs_key]):
                print("WARNING: Missing keys for Pipeline Engine. Falling back to Gemini Live.")
                return GeminiLiveEngine(
                    system_prompt=system_prompt,
                    google_api_key=os.getenv("GOOGLE_API_KEY")
                )

            return DeepgramPipelineEngine(
                system_prompt=system_prompt,
                deepgram_key=deepgram_key,
                google_key=google_key,
                elevenlabs_key=elevenlabs_key
            )
        else:
            return GeminiLiveEngine(
                system_prompt=system_prompt,
                google_api_key=os.getenv("GOOGLE_API_KEY")
            )
