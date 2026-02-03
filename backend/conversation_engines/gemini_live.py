import json
import asyncio
import base64
import websockets
import websockets.exceptions
import traceback
from .base import ConversationEngine

class GeminiLiveEngine(ConversationEngine):
    def __init__(self, system_prompt: str, google_api_key: str):
        self.system_prompt = system_prompt
        self.google_api_key = google_api_key
        self.google_ws = None
        self.running = False
        self.is_responding = False
        self.output_handler = None

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
                    "parts": [{"text": "Please converse in English. " + self.system_prompt}]
                }
            }
        }
        await self.google_ws.send(json.dumps(setup_msg))

    async def process_audio_input(self, audio_data: bytes):
        if not self.running or not self.google_ws:
            return

        # IGNORE INPUT IF MODEL IS RESPONDING (Disable Barge-In)
        if self.is_responding:
            return

        b64_audio = base64.b64encode(audio_data).decode("utf-8")
        
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
                
                if response.get("setupComplete"):
                    print(f"DEBUG: Setup Complete: {response}")
                
                # Handle Transcriptions
                transcription = response.get("audioTranscription")
                if transcription:
                    print(f"USER SAID: {transcription.get('text')}")

                # Extract Audio
                server_content = response.get("serverContent")
                if server_content:
                    model_turn = server_content.get("modelTurn")
                    if model_turn:
                        self.is_responding = True
                        
                        parts = model_turn.get("parts", [])
                        for part in parts:
                            if "inlineData" in part:
                                # Received Audio
                                b64_data = part["inlineData"]["data"]
                                await self.output_handler(json.dumps({
                                    "type": "audio",
                                    "data": b64_data
                                }))
                            elif "text" in part:
                                # Received Text
                                print(f"DEBUG: Received Text Part: {part['text'][:100]}...")
                                await self.output_handler(json.dumps({
                                    "type": "response_chunk",
                                    "content": part["text"]
                                }))
                
                # Handle Turn Complete
                if server_content and server_content.get("turnComplete"):
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
