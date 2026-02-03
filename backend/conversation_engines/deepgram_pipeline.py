import asyncio
import json
import base64
import re
from conversation_engines.base import ConversationEngine
from audio_providers.stt.deepgram import DeepgramSTTProvider
from audio_providers.llm.gemini_llm import GeminiLLMProvider
from audio_providers.tts.elevenlabs_tts import ElevenLabsTTSProvider

class DeepgramPipelineEngine(ConversationEngine):
    def __init__(self, system_prompt: str, deepgram_key: str, google_key: str, elevenlabs_key: str):
        self.stt = DeepgramSTTProvider(deepgram_key)
        self.llm = GeminiLLMProvider(google_key, system_prompt)
        self.tts = ElevenLabsTTSProvider(elevenlabs_key)
        
        self.output_handler = None
        self.running = False
        self.current_transcript = []
        self.orchestrator_task = None
        self.turn_task = None
        self.silence_timer_task = None

    async def start_session(self, output_handler):
        self.output_handler = output_handler
        self.running = True
        await self.stt.connect()
        self.orchestrator_task = asyncio.create_task(self.orchestrate())
        print("Deepgram Pipeline Started")

    async def process_audio_input(self, audio_data: bytes):
        await self.stt.send_audio(audio_data)

    async def process_text_input(self, text: str):
        await self.handle_turn(text)

    async def _silence_timer(self, duration=1.2):
        try:
            await asyncio.sleep(duration)
            print("\n[Pipeline] Silence timeout -> Forcing Turn")
            await self.process_turn_logic()
        except asyncio.CancelledError:
            pass

    async def process_turn_logic(self):
        full_text = " ".join(self.current_transcript).strip()
        self.current_transcript = []
        if full_text:
            if self.turn_task and not self.turn_task.done():
                print(f"\n[VAD] Ignoring input '{full_text}' (Agent is active)")
            else:
                print(f"[Pipeline] Starting turn with text: '{full_text}'")
                self.turn_task = asyncio.create_task(self.handle_turn(full_text))
        else:
            # Only log if we expected something, to avoid noise
            pass

    async def orchestrate(self):
        try:
            async for event in self.stt.listen():
                if event["type"] == "text":
                    text = event["value"]
                    is_final = event.get("is_final", False)
                    
                    current_turn_text = " ".join(self.current_transcript + [text])

                    if is_final:
                        print(f"\n[STT Final] {text}")
                        # Restart silence timer
                        if self.silence_timer_task:
                            self.silence_timer_task.cancel()
                        self.silence_timer_task = asyncio.create_task(self._silence_timer(1.2))
                    else:
                        print(f"\r[STT Interim] {text}", end="", flush=True)

                    await self.output_handler(json.dumps({
                        "type": "transcript",
                        "text": current_turn_text,
                        "is_final": is_final
                    }))

                    if is_final:
                        self.current_transcript.append(text)
                
                elif event["type"] == "signal":
                    if event["value"] == "speech_started":
                        print("\n[VAD] User started speaking")
                        # Cancel silence timer
                        if self.silence_timer_task:
                            self.silence_timer_task.cancel()
                    
                    elif event["value"] == "utterance_end":
                        print("\n[VAD] Deepgram UtteranceEnd -> Processing Turn")
                        # Cancel silence timer (we are handling it now)
                        if self.silence_timer_task:
                            self.silence_timer_task.cancel()
                        await self.process_turn_logic()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Orchestrator Error: {e}")

    async def handle_turn(self, text: str):
        print(f"\n[LLM] Generating response for: '{text}'")
        try:
            response_stream = self.llm.generate_response(text)
            
            buffer = ""
            async for chunk in response_stream:
                buffer += chunk
                sentences = re.split(r'(?<=[.!?])\s+', buffer)
                if len(sentences) > 1:
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                             await self.speak_sentence(sentence)
                    buffer = sentences[-1]
            
            if buffer.strip():
                await self.speak_sentence(buffer)

            print("\n[Turn Complete]")
            await self.output_handler(json.dumps({"type": "turn_complete"}))

        except asyncio.CancelledError:
            print("\n[Turn Cancelled]")
        except Exception as e:
            print(f"\n[Turn Error] {e}")

    async def speak_sentence(self, sentence: str):
        print(f"\n[TTS] Synthesizing: '{sentence}'")
        await self.output_handler(json.dumps({
            "type": "response_chunk",
            "content": sentence + " "
        }))

        try:
            audio_generator = self.tts.stream_audio(sentence)
            async for audio_chunk in audio_generator:
                if audio_chunk:
                    b64_data = base64.b64encode(audio_chunk).decode("utf-8")
                    await self.output_handler(json.dumps({
                        "type": "audio",
                        "data": b64_data
                    }))
        except Exception as e:
            print(f"[TTS Error] {e}")

        async def end_session(self):

            self.running = False

            if self.orchestrator_task:

                self.orchestrator_task.cancel()

            if self.turn_task:

                self.turn_task.cancel()

            if self.silence_timer_task:

                self.silence_timer_task.cancel()

            await self.stt.close()

            print("Pipeline Session Ended")

    