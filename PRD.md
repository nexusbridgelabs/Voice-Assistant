# Product Requirements Document (PRD): DONNA Voice Assistant

## 1. Project Overview
DONNA is a high-tech, sophisticated voice assistant with a visually immersive React-based frontend. It is designed to be more than a simple command executor; it acts as a proactive, personable, and intelligent companion. Key differentiators include a "nebulous" 3D visualization of the agent's state, smart voice activity detection (VAD) that understands natural conversational pauses, and full interruptibility ("barge-in") capability.

## 2. Core Features

### 2.1. User Interface (Frontend)
*   **Framework:** React (Single Page Application).
*   **Visual Style:** Futuristic, clean, high-tech.
*   **Central Visualization:**
    *   A spherical, nebulous 3D animation (using Three.js/React Three Fiber).
    *   **States:**
        *   *Idle/Paused:* Static or slow pulsing.
        *   *Listening:* Reacts to audio amplitude/frequency of the user.
        *   *Processing/Thinking:* distinct animation (e.g., rapid swirling).
        *   *Speaking:* Reacts to the agent's own audio output.
*   **Controls:**
    *   **Pause/Wake Toggle:** Puts the agent into a sleep mode where it stops listening via VAD.
    *   **Push-to-Talk (PTT):** Available specifically when paused, allowing discrete interactions without waking the continuous VAD.

### 2.2. Voice Interaction (Audio/AI)
*   **Voice Activity Detection (VAD):**
    *   Must distinguish between silence, background noise, and speech.
    *   **Smart Pause Detection:** The agent should not interrupt during brief, natural pauses (thinking time) but should detect when the user has definitively stopped speaking.
*   **Interruptibility (Barge-in):**
    *   If the agent is speaking and the user starts talking, the agent must immediately stop speaking and listen to the new input.
*   **Latency:** Minimal latency is critical for a "real-time" feel.

### 2.3. Intelligence & Personality
*   **Identity:** "DONNA" - Helpful, honest, capable of sarcasm and "tough love."
*   **Configuration:**
    *   `SOUL.md`: Defines personality, tone, and behavioral nuances.
    *   `RULES.md`: Defines hard constraints and safety protocols.
*   **Memory (Step 2):** Integration with **Mem0** for long-term, user-specific memory persistence.
*   **Tools (Step 3):**
    *   A `TOOLS` directory for executable scripts/functions (e.g., Web Search).
    *   **Self-Expansion:** The agent should have the capability to generate new tools (code) and save them to this directory for future use.

## 3. Technical Architecture (Proposed)

### 3.1. Frontend
*   **React (Vite)**
*   **Three.js / React Three Fiber** for the sphere.
*   **WebSocket Client** for streaming audio and state.

### 3.2. Backend
*   **Python (FastAPI)**: Python is the ecosystem leader for AI/Audio processing.
*   **WebSocket Server**: Handles full-duplex communication.
*   **Orchestrator**: Manages state (Listening -> Processing -> Speaking).
*   **Components**:
    *   *STT (Hearing):* Deepgram or OpenAI Whisper (Real-time).
    *   *LLM (Thinking):* **Google Gemini 2.0 Flash** (Multimodal capabilities).
    *   *TTS (Text-to-Speech):* **Gemini Native Audio** (eliminating ElevenLabs).
    *   *VAD:* Silero VAD.

## 4. Phased Implementation Plan
*   **Step 1:** Core interactive voice agent (UI + Backend + VAD + TTS/STT).
*   **Step 2:** Mem0 integration.
*   **Step 3:** Tooling system and dynamic tool creation.
