# Project: JARVIS Voice Assistant

## Overview
JARVIS is a sophisticated, React-based voice assistant with a focus on high-fidelity visual feedback and natural, interruptible conversation. It features a 3D interface, long-term memory via Mem0, and an extensible tool system.

## Key Files
*   `PRD.md`: The Product Requirements Document outlining features and scope.
*   `SOUL.md`: Defines the agent's personality and behavioral nuances.
*   `RULES.md`: Immutable operational rules and safety constraints.
*   `NOTES.txt`: General scratchpad.

## Architecture (Planned)
*   **Frontend:** React, Three.js (React Three Fiber), WebSocket Client.
*   **Backend:** Python (FastAPI), WebSocket Server.
*   **AI Stack:**
    *   **Hearing:** Deepgram (Cloud STT + VAD).
    *   **Thinking:** Google Gemini (Cloud LLM).
    *   **Speaking:** Gemini Native Audio (Cloud TTS).
    *   **No Local Models:** Pure cloud proxy architecture.

## Development Status
*   **Phase:** Initialization & Planning.
*   **Next Steps:** Scaffold Frontend (React) and Backend (Python).