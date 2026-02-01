import os
import json
import asyncio
import base64
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("ERROR: GOOGLE_API_KEY missing in .env")

# --- Load System Prompt ---
def load_system_prompt():
    try:
        with open("../SOUL.md", "r") as f:
            soul = f.read()
        with open("../RULES.md", "r") as f:
            rules = f.read()
        return f"{soul}\n\n{rules}"
    except Exception as e:
        print(f"Error loading system prompt: {e}")
        return "You are JARVIS, a helpful AI assistant."

SYSTEM_PROMPT = load_system_prompt()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Session Manager ---
class JarvisSession:
    def __init__(self, websocket: WebSocket):
        self.client_ws = websocket
        self.google_ws = None
        self.running = False

import traceback
import websockets.exceptions

# ... imports ...

    async def connect(self):
        await self.client_ws.accept()
        print("Client Connected.")
        
        # Connect to Google Live API
        url = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GOOGLE_API_KEY}"
        try:
            self.google_ws = await websockets.connect(url)
            print("Connected to Google Live API")
            await self.send_setup()
            self.running = True
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"Google Connection Failed: Status {e.status_code}")
            print(f"Headers: {e.headers}")
            await self.client_ws.close(code=1011, reason=f"Google API Error: {e.status_code}")
        except Exception as e:
            print(f"Google Connection Error: {e}")
            traceback.print_exc()
            await self.client_ws.close(code=1011, reason=str(e))

    async def send_setup(self):
        setup_msg = {
            "setup": {
                "model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
                "generation_config": {
                    "response_modalities": ["AUDIO"]
                },
                "system_instruction": {
                    "parts": [{"text": SYSTEM_PROMPT}]
                }
            }
        }
        await self.google_ws.send(json.dumps(setup_msg))

    async def handle_client_messages(self):
        try:
            while self.running:
                message = await self.client_ws.receive()
                
                if "bytes" in message:
                    # Audio chunk from client (PCM 16kHz expected)
                    audio_data = message["bytes"]
                    b64_audio = base64.b64encode(audio_data).decode("utf-8")
                    
                    realtime_input = {
                        "realtime_input": {
                            "media_chunks": [{
                                "mime_type": "audio/pcm",
                                "data": b64_audio
                            }]
                        }
                    }
                    await self.google_ws.send(json.dumps(realtime_input))
                    
                elif "text" in message:
                    # Handle text messages if needed (e.g. config updates)
                    pass

        except WebSocketDisconnect:
            print("Client disconnected")
        except Exception as e:
            print(f"Client Loop Error: {e}")
        finally:
            self.running = False
            if self.google_ws:
                await self.google_ws.close()

    async def handle_google_messages(self):
        try:
            async for raw_msg in self.google_ws:
                if not self.running:
                    break
                
                response = json.loads(raw_msg)
                
                # Extract Audio
                server_content = response.get("serverContent")
                if server_content:
                    model_turn = server_content.get("modelTurn")
                    if model_turn:
                        parts = model_turn.get("parts", [])
                        for part in parts:
                            if "inlineData" in part:
                                # Received Audio
                                b64_data = part["inlineData"]["data"]
                                # Send back to client as base64 or bytes?
                                # Let's send as JSON with type "audio" for frontend to handle
                                await self.client_ws.send_text(json.dumps({
                                    "type": "audio",
                                    "data": b64_data
                                }))
                            elif "text" in part:
                                # Received Text
                                await self.client_ws.send_text(json.dumps({
                                    "type": "response_chunk",
                                    "content": part["text"]
                                }))
                
                # Handle Turn Complete
                if server_content and server_content.get("turnComplete"):
                    await self.client_ws.send_text(json.dumps({"type": "turn_complete"}))

        except Exception as e:
            print(f"Google Loop Error: {e}")
        finally:
            self.running = False
            try:
                await self.client_ws.close()
            except:
                pass

    async def run(self):
        await self.connect()
        if self.running:
            # Run both loops concurrently
            await asyncio.gather(
                self.handle_client_messages(),
                self.handle_google_messages()
            )

@app.get("/")
async def root():
    return {"message": "JARVIS Brain is Online (Google Live API)"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session = JarvisSession(websocket)
    await session.run()