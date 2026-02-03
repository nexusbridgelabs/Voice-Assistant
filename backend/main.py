import os
import json
import asyncio
import struct
import math
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from conversation_engines.gemini_live import GeminiLiveEngine

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
        # Initialize the specific engine (Gemini Live for now)
        self.engine = GeminiLiveEngine(
            system_prompt=SYSTEM_PROMPT, 
            google_api_key=GOOGLE_API_KEY
        )

    async def run(self):
        await self.client_ws.accept()
        print("Client Connected.")

        try:
            # Start the engine
            await self.engine.start_session(output_handler=self.client_ws.send_text)
            
            # Loop to handle messages from the client (React App)
            while True:
                message = await self.client_ws.receive()
                
                if "bytes" in message:
                    # Audio chunk from client
                    audio_data = message["bytes"]
                    
                    # --- Debugging (RMS) ---
                    try:
                        count = len(audio_data) // 2
                        shorts = struct.unpack(f'<{count}h', audio_data)
                        sum_squares = sum(s**2 for s in shorts)
                        rms = math.sqrt(sum_squares / count)
                        if int(time.time() * 20) % 50 == 0:
                             print(f"DEBUG: RMS: {rms:.0f}")
                    except Exception:
                         pass
                    
                    # Pass audio to engine
                    await self.engine.process_audio_input(audio_data)

                elif "text" in message:
                    # Pass text to engine (if applicable)
                    # await self.engine.process_text_input(message["text"])
                    pass

        except WebSocketDisconnect:
            print("Client disconnected")
        except Exception as e:
            print(f"Session Error: {e}")
        finally:
            await self.engine.end_session()


@app.get("/")
async def root():
    return {"message": "JARVIS Brain is Online (Google Live API)"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    session = JarvisSession(websocket)
    await session.run()