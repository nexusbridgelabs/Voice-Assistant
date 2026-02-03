# Conversation Engine Refactor Plan
## Dual-Engine Voice Assistant Architecture

**Goal**: Support both Gemini Live API and Deepgram+TTS pipeline in the same codebase with easy feature sharing and config-based switching.

---

## Core Architecture

### Abstract Interface Pattern
Create a `ConversationEngine` base class that defines the contract:
- `start_session()`, `end_session()`
- `process_audio_input()`, `get_audio_response()`
- `process_text_input()`, `get_text_response()`
- `interrupt()`

### Two Implementations

**GeminiLiveEngine**
- Single bidirectional WebSocket
- Native audio in/out through Gemini Live API
- Wraps existing Gemini functionality

**DeepgramPipelineEngine**  
- Three-stage pipeline: STT → LLM → TTS
- Orchestrates separate providers
- Each provider has its own abstraction (STTProvider, LLMProvider, TTSProvider)

### Provider Abstractions
Create base classes for swappable components:
- **STT**: Deepgram, AssemblyAI, Azure, etc.
- **LLM**: OpenAI, Anthropic, Gemini, etc.
- **TTS**: ElevenLabs, OpenAI, Cartesia, etc.

---

## Directory Structure

```
backend/
├── conversation_engines/
│   ├── base.py                 # Abstract ConversationEngine
│   ├── gemini_live.py          # Existing functionality
│   ├── deepgram_pipeline.py    # New pipeline engine
│   └── __init__.py             # EngineFactory
├── audio_providers/
│   ├── stt/
│   │   ├── base.py
│   │   └── deepgram.py
│   ├── llm/
│   │   ├── base.py
│   │   ├── openai.py
│   │   └── anthropic.py
│   └── tts/
│       ├── base.py
│       ├── elevenlabs.py
│       └── openai.py
├── config/
│   └── engine_config.py        # Config management
└── routes/
    └── voice_chat.py           # Engine-agnostic WebSocket

frontend/
└── src/
    └── services/
        └── audioService.js     # NO CHANGES NEEDED
```

---

## Implementation Phases

### Phase 1: Base Abstractions
- Create `ConversationEngine` ABC with core methods
- Create provider base classes (STTProvider, LLMProvider, TTSProvider)
- Define common interface all engines must implement

### Phase 2: Refactor Gemini Live
- Move existing Gemini Live code into `GeminiLiveEngine` class
- Implement abstract methods from base class
- Ensure existing functionality preserved

### Phase 3: Build Provider System
- Implement Deepgram STT with streaming transcription
- Implement LLM providers (OpenAI, Anthropic)
- Implement TTS providers (ElevenLabs, OpenAI)
- Each provider handles its own connection lifecycle

### Phase 4: Pipeline Engine
- Create `DeepgramPipelineEngine` that orchestrates providers
- Handle STT → LLM streaming
- Implement sentence-based TTS synthesis
- Manage interruption/cancellation

### Phase 5: Configuration & Factory
- Create `EngineFactory` to instantiate correct engine
- Build configuration system with environment variables
- Support provider selection within pipeline engine

### Phase 6: Integration
- Update WebSocket route to use EngineFactory
- Ensure engine type is transparent to frontend
- Add optional engine indicator in UI

---

## Key Technical Patterns

### Engine Selection (Factory Pattern)
```python
# Environment variable controls which engine
CONVERSATION_ENGINE=gemini_live  # or deepgram_pipeline

# Factory creates appropriate engine
engine = EngineFactory.create_engine()
```

### Provider Composition (Strategy Pattern)
```python
# Pipeline engine composes providers
engine = DeepgramPipelineEngine(
    stt_provider=DeepgramSTT(),
    llm_provider=OpenAILLM(),
    tts_provider=ElevenLabsTTS()
)
```

### Async Streaming Throughout
- All audio/text I/O uses async generators
- Queues for cross-provider communication
- Background tasks for continuous processing

---

## Critical Design Decisions

### 1. WebSocket Route Must Be Engine-Agnostic
The WebSocket handler should work identically with both engines. It only knows about the `ConversationEngine` interface, not specific implementations.

### 2. Frontend Stays Unchanged
No modifications to React frontend. The WebSocket protocol remains identical. Engine type is metadata, not a requirement.

### 3. Config-Driven Everything
Switch engines with environment variable. Switch providers within pipeline with config. No code changes for different setups.

### 4. Sentence-Based TTS in Pipeline
Don't wait for complete LLM response. Stream LLM output, detect sentence boundaries, immediately synthesize each sentence for lower latency.

### 5. Interruption Handling
Both engines must support immediate interruption. Pipeline engine cancels LLM task and clears output queues.

---

## Migration Strategy

1. **Branch**: `git checkout -b engine-refactor`
2. **Refactor existing first**: Move Gemini to engine class, verify no regression
3. **Build new incrementally**: Providers → Pipeline → Factory → Integration
4. **Test switching**: Verify both engines work via config toggle
5. **Merge when stable**: Both engines fully functional

---

## Testing Requirements

- [ ] Gemini Live engine works identically to current implementation
- [ ] Deepgram STT streams transcriptions correctly
- [ ] LLM responses stream without blocking
- [ ] TTS audio plays smoothly with minimal gaps
- [ ] Interruption works in both engines
- [ ] Engine switching via env variable works
- [ ] Frontend connects to both engines without changes
- [ ] Session cleanup prevents resource leaks

---

## Future Flexibility

Once refactored:
- **Add providers**: Drop in new STT/LLM/TTS with minimal code
- **Mix providers**: Deepgram + Gemini LLM + ElevenLabs TTS
- **Hybrid features**: Vision, RAG, tool use in either engine
- **A/B testing**: Run both engines, compare performance
- **Cost optimization**: Switch to cheaper providers easily

---

## Success Criteria

✅ Both engines coexist in same codebase  
✅ No frontend modifications required  
✅ Config file controls engine selection  
✅ Easy to add new providers  
✅ Gemini Live functionality preserved  
✅ Deepgram pipeline achieves similar latency  
✅ Clean separation of concerns  

---

This refactor maintains your Gemini Live progress while enabling the Deepgram pipeline, with architecture that makes future changes trivial.
