import json
import asyncio
import base64
import websockets
import websockets.exceptions
import traceback
from .base import ConversationEngine

class GeminiLiveEngine(ConversationEngine):
    MIN_AUDIO_BUFFER_SIZE = 4096  # 4KB buffer for lower latency (~0.15s)
    DEBUG_SAVE_AUDIO = True  # Save first 5 seconds of audio for debugging

    def __init__(self, system_prompt: str, google_api_key: str):
        self.system_prompt = system_prompt
        self.google_api_key = google_api_key
        self.google_ws = None
        self.running = False
        self.is_responding = False
        self.output_handler = None
        self.audio_buffer = bytearray()
        self.input_audio_buffer = bytearray()
        self.debug_audio_buffer = bytearray()
        self.debug_audio_saved = False
        self.interruption_hits = 0

    async def start_session(self, output_handler):
        self.output_handler = output_handler
        url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={self.google_api_key}"
        try:
            self.google_ws = await websockets.connect(url)
            print("Connected to Google Live API")
            await self.send_setup()
            self.running = True
            
            # Start the background task to listen to Google
            asyncio.create_task(self.handle_google_messages())
            
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"Google Connection Failed: Status {e.status_code}")
            print(f"Headers: {e.headers}")
            raise e
        except Exception as e:
            print(f"Google Connection Error: {e}")
            traceback.print_exc()
            raise e

    async def send_setup(self):
        setup_msg = {
            "setup": {
                "model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": "Puck"
                            }
                        }
                    }
                },
                "realtimeInputConfig": {
                    "automaticActivityDetection": {}
                },
                "inputAudioTranscription": {}, 
                "systemInstruction": {
                    "parts": [{"text": "You are DONNA. Always respond in English only. The user speaks English."}]
                }
            }
        }
        await self.google_ws.send(json.dumps(setup_msg))

    async def process_audio_input(self, audio_data: bytes):
        if not self.running or not self.google_ws:
            return

        # ALLOW INPUT EVEN IF MODEL IS RESPONDING (Enable Barge-In)
        # Gemini handles interruption natively if setup with automaticActivityDetection

        # Buffer audio to send larger chunks (Gemini may need bigger chunks)
        self.input_audio_buffer.extend(audio_data)

        # Send in 1024 byte chunks as per Google docs
        if len(self.input_audio_buffer) < 1024:
            return

        audio_to_send = bytes(self.input_audio_buffer)
        self.input_audio_buffer = bytearray()

        # DEBUG: Log audio chunk info
        import struct
        num_samples = len(audio_to_send) // 2
        if num_samples > 0:
            samples = struct.unpack(f'<{num_samples}h', audio_to_send)
            rms = (sum(s*s for s in samples) / num_samples) ** 0.5
            # print(f"[Gemini Input] {len(audio_to_send)} bytes, {num_samples} samples, RMS: {rms:.0f}")

            # MANUAL BARGE-IN: If volume is high enough while responding, interrupt
            # Require 3 consecutive hits (approx 60ms of audio) above threshold to filter noise
            if self.is_responding and rms > 1000: 
                self.interruption_hits += 1
                if self.interruption_hits >= 3:
                    print(f"[Barge-In] Local VAD verified speech (RMS: {rms:.0f}) -> Interrupting")
                    self.is_responding = False
                    self.interruption_hits = 0
                    self.audio_buffer = bytearray()
                    # Send stop to frontend
                    asyncio.create_task(self.output_handler(json.dumps({"type": "stop_audio"})))
            else:
                self.interruption_hits = 0

        b64_audio = base64.b64encode(audio_to_send).decode("utf-8")
        
        realtime_input = {
            "realtimeInput": {
                "mediaChunks": [{
                    "mimeType": "audio/pcm;rate=16000",
                    "data": b64_audio
                }]
            }
        }
        try:
            await self.google_ws.send(json.dumps(realtime_input))
        except Exception as e:
            print(f"Error sending audio to Google: {e}")

    async def process_text_input(self, text: str):
        pass

    async def handle_google_messages(self):
        try:
            async for raw_msg in self.google_ws:
                if not self.running:
                    break
                
                # print(f"DEBUG: Received from Google: {len(raw_msg)} bytes")
                response = json.loads(raw_msg)
                
                # Log ALL responses for debugging
                print(f"[Gemini Response] {json.dumps(response)[:500]}")

                if response.get("setupComplete"):
                    print("DEBUG: Setup Complete")
                
                # Handle Transcriptions
                transcription = response.get("audioTranscription")
                if transcription:
                    print(f"[Gemini STT] User said: '{transcription.get('text')}'")

                # Extract Audio
                server_content = response.get("serverContent")
                if server_content:
                    # Detect Interruption (Google native)
                    if server_content.get("interrupted"):
                        print("DEBUG: Google sent Interrupted signal")
                        self.is_responding = False
                        self.audio_buffer = bytearray()
                        await self.output_handler(json.dumps({"type": "stop_audio"}))

                    model_turn = server_content.get("modelTurn")
                    if model_turn:
                        if not self.is_responding:
                            await self.output_handler(json.dumps({
                                "type": "state",
                                "state": "processing"
                            }))
                        self.is_responding = True

                        parts = model_turn.get("parts", [])
                        for part in parts:
                            # Drop data if we've been interrupted since the loop started
                            if not self.is_responding:
                                break

                            if "inlineData" in part:
                                # Received Audio - buffer it for smooth playback
                                raw_audio = base64.b64decode(part["inlineData"]["data"])
                                self.audio_buffer.extend(raw_audio)

                                # Send when buffer is large enough
                                if len(self.audio_buffer) >= self.MIN_AUDIO_BUFFER_SIZE:
                                    if self.is_responding:
                                        b64_data = base64.b64encode(self.audio_buffer).decode("utf-8")
                                        await self.output_handler(json.dumps({
                                            "type": "audio",
                                            "data": b64_data
                                        }))
                                    self.audio_buffer = bytearray()
                            elif "text" in part:
                                # Received Text
                                print(f"DEBUG: Received Text Part: {part['text'][:100]}...")
                                await self.output_handler(json.dumps({
                                    "type": "response_chunk",
                                    "content": part["text"]
                                }))

                # Handle Turn Complete
                if server_content and server_content.get("turnComplete"):
                    # Flush any remaining audio in buffer
                    if len(self.audio_buffer) > 0:
                        b64_data = base64.b64encode(self.audio_buffer).decode("utf-8")
                        await self.output_handler(json.dumps({
                            "type": "audio",
                            "data": b64_data
                        }))
                        self.audio_buffer = bytearray()

                    print("DEBUG: Google sent Turn Complete -> Forwarding to Client")
                    self.is_responding = False
                    await self.output_handler(json.dumps({"type": "turn_complete"}))

        except Exception as e:
            print(f"Google Loop Error: {e}")
        finally:
            print("DEBUG: Google Loop Exited")
            self.running = False
            # We don't close the output_handler here, as it's owned by the session

    async def end_session(self):
        self.running = False
        if self.google_ws:
            await self.google_ws.close()
            print("Closed Google Live Connection")
