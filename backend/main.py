import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)
from openai import AsyncOpenAI

load_dotenv()

# --- Configuration ---
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o") # Default to gpt-4o if not specified

if not DEEPGRAM_API_KEY or not LLM_API_KEY:
    print("ERROR: API Keys missing in .env")

print(f"DEBUG: LLM_BASE_URL={LLM_BASE_URL}")
print(f"DEBUG: LLM_MODEL={LLM_MODEL}")

# Configure Third-Party LLM (OpenAI Compatible)
client = AsyncOpenAI(
    api_key=LLM_API_KEY,
    base_url=LLM_BASE_URL
)

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
        self.websocket = websocket
        self.deepgram = None # Initialize lazily
        self.dg_connection = None
        self.chat_history = [{"role": "system", "content": SYSTEM_PROMPT}] 
        self.dg_active = False
        self.keep_alive_task = None
        self.awaiting_reset = False

    async def connect(self):
        await self.websocket.accept()
        print("Client Connected. Waiting for audio...")
        # Initialize Deepgram Client here safely
        try:
            self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        except Exception as e:
            print(f"Deepgram Client Init Error: {e}")

    async def start_deepgram(self):
        # Double check initialization
        if not self.deepgram:
             print("Deepgram client not initialized, retrying...")
             try:
                self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
             except Exception as e:
                print(f"Deepgram Client Init Error (Retry): {e}")
                return

        if self.dg_active and self.dg_connection:
            return

        print("Starting Deepgram connection...")
        try:
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self.on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, self.on_close)
            
            options = LiveOptions(
                model="nova-2", 
                language="en-US", 
                smart_format=True, 
                interim_results=True,
                vad_events=True, 
                endpointing=400,
                utterance_end_ms="1000"
            )
            
            if await self.dg_connection.start(options):
                self.dg_active = True
                print("Deepgram Connected!")
                self.keep_alive_task = asyncio.create_task(self.keep_alive())
            else:
                print("Deepgram failed to start.")
                self.dg_active = False

        except Exception as e:
            print(f"Deepgram Start Error: {e}")
            self.dg_active = False

    async def keep_alive(self):
        try:
            while self.dg_active:
                await asyncio.sleep(3)
                if self.dg_connection:
                    await self.dg_connection.send(json.dumps({"type": "KeepAlive"}))
        except Exception as e:
            print(f"KeepAlive Error: {e}")

    async def on_close(self, connection, **kwargs):
        print("Deepgram Connection Closed")
        try:
             await self.websocket.send_text(json.dumps({"type": "reset_audio"}))
             self.awaiting_reset = True
        except:
             pass
        self.dg_active = False
        if self.keep_alive_task:
            self.keep_alive_task.cancel()

    async def on_transcript(self, connection, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        is_final = result.is_final
        print(f"DEBUG: Transcript received: '{sentence}' (is_final={is_final})")
        
        if len(sentence) == 0:
            return

        
        await self.websocket.send_text(json.dumps({
            "type": "transcript", 
            "content": sentence, 
            "isFinal": is_final
        }))

        if is_final:
            print(f"User: {sentence}")
            asyncio.create_task(self.process_and_reply(sentence))

    async def process_and_reply(self, text):
        try:
            await self.websocket.send_text(json.dumps({"type": "state", "state": "processing"}))
        except Exception:
            # Connection likely closed
            return
        
        # Add to history
        self.chat_history.append({"role": "user", "content": text})
        
        full_reply = ""
        try:
            # Generate Response (Streamed)
            response = await client.chat.completions.create(
                model=LLM_MODEL,
                messages=self.chat_history,
                stream=True
            )
            
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    full_reply += content
                    try:
                        await self.websocket.send_text(json.dumps({
                            "type": "response_chunk", 
                            "content": content
                        }))
                    except Exception:
                        pass # Client might have disconnected

            print(f"Jarvis: {full_reply}")

            # Add to history
            self.chat_history.append({"role": "assistant", "content": full_reply})

            # Send complete signal
            await self.websocket.send_text(json.dumps({
                "type": "response_complete", 
                "content": full_reply
            }))
            
            await self.websocket.send_text(json.dumps({"type": "state", "state": "speaking"}))
            
        except Exception as e:
            print(f"LLM Error: {e}")
            try:
                await self.websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
            except Exception:
                pass # Client disconnected, can't send error
        
        try:
            await self.websocket.send_text(json.dumps({"type": "state", "state": "idle"}))
        except Exception:
            pass

    def on_error(self, connection, error, **kwargs):
        print(f"Deepgram Error: {error}")

    async def handle_incoming(self):
        try:
            while True:
                message = await self.websocket.receive()
                
                if "bytes" in message:
                    if self.awaiting_reset:
                        continue # Drop zombie chunks

                    payload = message["bytes"]
                    print(f"DEBUG: Received audio chunk: {len(payload)} bytes")
                    if not self.dg_active:
                        await self.start_deepgram()
                    
                    if self.dg_active and self.dg_connection and len(payload) > 0:
                        await self.dg_connection.send(payload)
                    
                elif "text" in message:
                    try:
                        data = json.loads(message["text"])
                        if data.get("type") == "text":
                            await self.process_and_reply(data["content"])
                        elif data.get("type") == "audio_reset_complete":
                            print("Audio stream reset confirmed.")
                            self.awaiting_reset = False
                    except Exception as e:
                        print(f"Text Message Error: {e}")

        except WebSocketDisconnect:
            print("Client disconnected (WebSocketDisconnect)")
        except RuntimeError as e:
            if "disconnect message" in str(e):
                 print("Client disconnected (RuntimeError)")
            else:
                 print(f"RuntimeError in handle_incoming: {e}")
        except Exception as e:
            print(f"Handle Incoming Error: {e}")
        finally:
            if self.dg_connection:
                await self.dg_connection.finish()
            self.dg_active = False
            if self.keep_alive_task:
                self.keep_alive_task.cancel()

@app.get("/")
async def root():
    return {"message": "JARVIS Brain is Online (Custom LLM)"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("DEBUG: WebSocket connection attempt...")
    try:
        session = JarvisSession(websocket)
        print("DEBUG: Session initialized.")
        await session.connect()
        print("DEBUG: Session connected.")
        await session.handle_incoming()
    except Exception as e:
        print(f"CRITICAL WS ERROR: {e}")
        try:
            await websocket.close(code=1011)
        except:
            pass