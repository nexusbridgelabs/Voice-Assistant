import asyncio
import json
import base64
import re
from conversation_engines.base import ConversationEngine
from audio_providers.stt.deepgram import DeepgramSTTProvider
from audio_providers.llm.gemini_llm import GeminiLLMProvider
from audio_providers.tts.elevenlabs_tts import ElevenLabsTTSProvider
from audio_providers.tts.kokoro_tts import KokoroTTSProvider
from tools.time_tools import TIME_TOOLS_DEFINITIONS, AVAILABLE_TOOLS

class DeepgramPipelineEngine(ConversationEngine):
    def __init__(self, system_prompt: str, deepgram_key: str, google_key: str, tts_config: dict):
        self.stt = DeepgramSTTProvider(deepgram_key)
        self.llm = GeminiLLMProvider(
            api_key=google_key, 
            system_prompt=system_prompt,
            tool_definitions=TIME_TOOLS_DEFINITIONS,
            tool_implementations=AVAILABLE_TOOLS
        )

        # Initialize TTS provider based on config
        if tts_config.get("provider") == "kokoro":
            self.tts = KokoroTTSProvider(
                base_url=tts_config.get("base_url", "https://kokoro.jmwalker.dev"),
                voice=tts_config.get("voice", "af_bella")
            )
            print(f"Using Kokoro TTS: {tts_config.get('base_url')}")
        else:
            self.tts = ElevenLabsTTSProvider(tts_config.get("api_key"))
            print("Using ElevenLabs TTS")
        
        self.output_handler = None
        self.running = False
        self.current_transcript = []
        self.orchestrator_task = None
        self.turn_task = None
        self.silence_timer_task = None
        self.keepalive_task = None
        self.interruption_hits = 0
        self.current_turn_id = 0

    async def start_session(self, output_handler):
        self.output_handler = output_handler
        self.running = True
        await self.stt.connect()
        self.orchestrator_task = asyncio.create_task(self.orchestrate())
        print("Deepgram Pipeline Started")

    async def process_audio_input(self, audio_data: bytes):
        # Local RMS check for fast verified barge-in
        import struct
        import math
        count = len(audio_data) // 2
        if count > 0:
            shorts = struct.unpack(f'<{count}h', audio_data)
            sum_sq = sum(s**2 for s in shorts)
            rms = math.sqrt(sum_sq / count)
            
            # If agent is speaking and we see sustained volume, interrupt
            if self.turn_task and not self.turn_task.done() and rms > 1000:
                self.interruption_hits += 1
                if self.interruption_hits >= 7: # ~200ms of speech
                    print(f"[Barge-In] Local VAD verified sustained speech (RMS: {rms:.0f}) -> Stopping playback")
                    self.interruption_hits = 0
                    self.current_turn_id += 1 # Invalidate current turn
                    if self.output_handler:
                        await self.output_handler(json.dumps({"type": "stop_audio"}))
            else:
                self.interruption_hits = 0

        # Allow audio input even during agent turn to support Deepgram's own VAD/STT
        await self.stt.send_audio(audio_data)

    async def process_text_input(self, text: str):
        # Text input from frontend might include turn_id
        try:
            data = json.loads(text)
            if data.get("type") == "text":
                self.current_turn_id = data.get("turn_id", self.current_turn_id)
                await self.handle_turn(data.get("content"))
                return
        except Exception:
            pass
        await self.handle_turn(text)

    async def _silence_timer(self, duration=1.2):
        try:
            await asyncio.sleep(duration)
            print("\n[Pipeline] Silence timeout -> Forcing Turn")
            await self.process_turn_logic()
        except asyncio.CancelledError:
            pass

    async def _keepalive_loop(self):
        """Send keepalive messages to Deepgram every 5 seconds during agent turn."""
        try:
            while True:
                await asyncio.sleep(5)
                await self.stt.send_keepalive()
        except asyncio.CancelledError:
            pass

    async def process_turn_logic(self):
        full_text = " ".join(self.current_transcript).strip()
        self.current_transcript = []
        if full_text:
            if self.turn_task and not self.turn_task.done():
                print(f"\n[Barge-In] Interrupting current turn for: '{full_text}'")
                self.turn_task.cancel()
                try:
                    await self.turn_task # Wait for cancellation to complete
                except asyncio.CancelledError:
                    pass
                self.current_turn_id += 1 # Invalidate current turn
                if self.output_handler:
                    await self.output_handler(json.dumps({"type": "stop_audio"}))
            
            print(f"[Pipeline] Starting turn with text: '{full_text}'")
            self.current_turn_id += 1 # New valid turn
            self.turn_task = asyncio.create_task(self.handle_turn(full_text))
        else:
            # Only log if we expected something, to avoid noise
            pass

    async def orchestrate(self):
        try:
            async for event in self.stt.listen():
                # BARGE-IN DETECTION: Check if agent is active when user speaks
                is_agent_active = self.turn_task and not self.turn_task.done()

                if event["type"] == "text":
                    text = event["value"]
                    is_final = event.get("is_final", False)
                    
                    if is_agent_active and text.strip():
                         # Filter noise: Require at least 2 characters for interim to avoid false positives 
                         # (e.g. random "s" or "a" being detected)
                         if len(text.strip()) > 1 or is_final:
                             print(f"\n[Barge-In] User spoke during agent turn: '{text}' -> Stopping playback")
                             self.turn_task.cancel()
                             try:
                                 await self.turn_task
                             except asyncio.CancelledError:
                                 pass
                             self.current_turn_id += 1 # Invalidate current turn
                             if self.output_handler:
                                 await self.output_handler(json.dumps({"type": "stop_audio"}))
                    
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
                        # We no longer interrupt on 'speech_started' to avoid jitter from noise
                        # Cancel silence timer
                        if self.silence_timer_task:
                            self.silence_timer_task.cancel()
                    
                    elif event["value"] == "utterance_end":
                        print("\n[VAD] Deepgram UtteranceEnd -> Processing Turn")
                        # Turn transition logic remains here, but interruption is handled in process_audio_input
                        
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
        # Send processing state to frontend
        if self.output_handler:
            await self.output_handler(json.dumps({
                "type": "state", 
                "state": "processing",
                "turn_id": self.current_turn_id
            }))
        
        # Start keepalive loop to prevent Deepgram timeout during agent turn
        self.keepalive_task = asyncio.create_task(self._keepalive_loop())
        self.turn_total_bytes = 0  # Track total audio bytes for this turn
        try:
            # Capture current turn ID for this specific response generation
            response_turn_id = self.current_turn_id
            response_stream = self.llm.generate_response(text)

            buffer = ""
            async for chunk in response_stream:
                buffer += chunk
                sentences = re.split(r'(?<=[.!?])\s+', buffer)
                if len(sentences) > 1:
                    for sentence in sentences[:-1]:
                        if sentence.strip():
                             await self.speak_sentence(sentence, response_turn_id)
                    buffer = sentences[-1]

            if buffer.strip():
                await self.speak_sentence(buffer, response_turn_id)

            # Small echo buffer at end of turn
            print(f"\n[Pipeline] Total turn audio: {self.turn_total_bytes} bytes")
            await asyncio.sleep(0.5)

            print("\n[Turn Complete]")
            await self.output_handler(json.dumps({"type": "turn_complete"}))

        except asyncio.CancelledError:
            print("\n[Turn Cancelled]")
        except Exception as e:
            print(f"\n[Turn Error] {e}")
        finally:
            # Stop keepalive loop when turn ends
            if self.keepalive_task:
                self.keepalive_task.cancel()
                self.keepalive_task = None

    async def speak_sentence(self, sentence: str, turn_id: int):
        print(f"\n[TTS] Synthesizing: '{sentence}'")
        await self.output_handler(json.dumps({
            "type": "response_chunk",
            "content": sentence + " "
        }))

        try:
            audio_generator = self.tts.stream_audio(sentence)
            chunks_sent = 0
            total_bytes = 0
            audio_buffer = bytearray()
            MIN_CHUNK_SIZE = 4096 # 4KB buffer (~0.1s) for low latency
            
            async for audio_chunk in audio_generator:
                if audio_chunk:
                    audio_buffer.extend(audio_chunk)
                    
                    if len(audio_buffer) >= MIN_CHUNK_SIZE:
                        b64_data = base64.b64encode(audio_buffer).decode("utf-8")
                        await self.output_handler(json.dumps({
                            "type": "audio",
                            "data": b64_data,
                            "turn_id": turn_id
                        }))
                        chunks_sent += 1
                        total_bytes += len(audio_buffer)
                        audio_buffer = bytearray()
            
            # Send remaining buffer
            if len(audio_buffer) > 0:
                b64_data = base64.b64encode(audio_buffer).decode("utf-8")
                await self.output_handler(json.dumps({
                    "type": "audio",
                    "data": b64_data,
                    "turn_id": turn_id
                }))
                chunks_sent += 1
                total_bytes += len(audio_buffer)
                
            print(f"[Pipeline] Sent {chunks_sent} chunks ({total_bytes} bytes) for sentence")
            self.turn_total_bytes += total_bytes

            # Reintroduce a 'soft wait' (half duration) to prevent overlapping 
            # while keeping latency low. Frontend handles exact scheduling.
            sentence_duration = total_bytes / 48000.0
            await asyncio.sleep(sentence_duration * 0.5)
            
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
        if self.keepalive_task:
            self.keepalive_task.cancel()
        await self.stt.close()
        print("Pipeline Session Ended")

    