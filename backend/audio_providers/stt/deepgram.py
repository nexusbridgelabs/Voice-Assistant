import asyncio
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)
from .base import STTProvider

class DeepgramSTTProvider(STTProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.connection = None
        self.queue = asyncio.Queue()
        self.running = False

    async def connect(self):
        config = DeepgramClientOptions(
            verbose=False,
            options={"keepalive": "true"}
        )
        self.client = DeepgramClient(self.api_key, config)
        
        # Create a connection
        self.connection = self.client.listen.asyncwebsocket.v("1")

        # Define event handlers
        async def on_message(self_dg, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if len(sentence) > 0:
                await self.queue.put({"type": "text", "value": sentence, "is_final": result.is_final})

        async def on_metadata(self_dg, metadata, **kwargs):
            pass
            
        async def on_utterance_end(self_dg, utterance_end, **kwargs):
            print("[DeepgramProvider] Event: UtteranceEnd")
            await self.queue.put({"type": "signal", "value": "utterance_end"})

        async def on_speech_started(self_dg, speech_started, **kwargs):
             print("[DeepgramProvider] Event: SpeechStarted")
             await self.queue.put({"type": "signal", "value": "speech_started"})

        async def on_error(self_dg, error, **kwargs):
            print(f"Deepgram Error: {error}")

        # Register handlers
        self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
        self.connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
        self.connection.on(LiveTranscriptionEvents.Error, on_error)

        # Connect with options
        options = LiveOptions(
            model="nova-2", 
            language="en-US", 
            smart_format=True,
            interim_results=True,
            vad_events=True,
            utterance_end_ms=1000,
            encoding="linear16",
            sample_rate=16000,
            channels=1
        )
        
        if await self.connection.start(options) is False:
             print("Deepgram: Failed to start connection")
             raise Exception("Deepgram connection failed")
        
        self.running = True
        print("Deepgram Connected")

    async def send_audio(self, audio_chunk: bytes):
        if self.connection and self.running:
            await self.connection.send(audio_chunk)

    async def send_keepalive(self):
        """Send a keepalive message to prevent Deepgram timeout."""
        if self.connection and self.running:
            try:
                await self.connection.keep_alive()
            except Exception as e:
                print(f"[Deepgram] Keepalive failed: {e}")

    async def listen(self):
        while self.running:
            try:
                # Wait for next transcript
                text = await self.queue.get()
                yield text
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error yielding transcript: {e}")
                break

    async def close(self):
        self.running = False
        if self.connection:
            await self.connection.finish()
        print("Deepgram Closed")
