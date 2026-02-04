# DONNA Voice Assistant

DONNA is a sophisticated, highly interactive voice assistant featuring a futuristic 3D visual interface. It is designed to be a "living" digital companion with a distinct personality, capable of real-time, interruptible conversation.

## 🚀 Features

*   **Immersive 3D UI:** A "nebulous sphere" visualizer (built with React Three Fiber) that reacts dynamically to agent states (Listening, Thinking, Speaking).
*   **Real-time Voice Interaction:** Low-latency voice processing with websocket-based full-duplex communication.
*   **Flexible Conversation Engines:** Switch between different backend architectures:
    *   **Gemini Live:** Uses Google's Multimodal Live API for an all-in-one low-latency experience.
    *   **Deepgram Pipeline:** A modular pipeline using Deepgram (STT), Gemini (LLM), and ElevenLabs (TTS).
*   **Smart "Barge-in":** The user can interrupt the agent while it is speaking.
*   **Rich UI Controls:**
    *   **Device Selector:** Choose your preferred microphone input.
    *   **Chat Panel:** View the text transcript of the conversation in real-time.
    *   **Debug Panel:** Monitor audio levels and system status.
    *   **Push-to-Talk:** Optional mode for discrete interaction.

## 🛠️ Tech Stack

*   **Frontend:** React (Vite), TypeScript, Tailwind CSS, Three.js (React Three Fiber).
*   **Backend:** Python (FastAPI), WebSockets.
*   **AI Services:**
    *   Google Gemini (LLM & Audio)
    *   Deepgram (STT)
    *   ElevenLabs (TTS - optional)

## 📋 Prerequisites

*   **Node.js** (v18+)
*   **Python** (v3.10+)
*   **API Keys** (depending on the engine you choose):
    *   [Google Gemini API Key](https://aistudio.google.com/)
    *   [Deepgram API Key](https://console.deepgram.com/) (for Deepgram Pipeline)
    *   [ElevenLabs API Key](https://elevenlabs.io/) (for Deepgram Pipeline)

## ⚡ Quick Start Guide

### 1. Clone & Setup Secrets

```bash
# Clone the repository
git clone <your-repo-url>
cd voice-assistant

# Set up Backend Secrets
cd backend
cp .env.example .env
```

**Edit `backend/.env`:**
Choose your conversation engine and provide the necessary keys.

**Option A: Gemini Live (Recommended for simplicity)**
```env
CONVERSATION_ENGINE=gemini_live
GOOGLE_API_KEY=your_google_key
```

**Option B: Deepgram Pipeline (For modular control)**
```env
CONVERSATION_ENGINE=deepgram_pipeline
GOOGLE_API_KEY=your_google_key
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### 2. Run the Backend (Python)

Open a terminal for the backend:

```bash
cd backend
python3 -m venv venv           # Create virtual environment
source venv/bin/activate       # Activate it (Windows: venv\Scripts\activate)
pip install -r requirements.txt # Install dependencies
uvicorn main:app --reload      # Start the server
```
*The backend runs on `http://localhost:8000`*

### 3. Run the Frontend (React)

Open a **new** terminal for the frontend:

```bash
cd frontend
npm install   # Install dependencies
npm run dev   # Start the dev server
```
*The frontend runs on `http://localhost:5173` (usually)*

### 4. Usage

1.  Open your browser to the Frontend URL.
2.  Click the **Microphone Icon** in the top right to select your input device.
3.  Click the **Power Icon** in the center bottom to wake DONNA.
4.  Speak to the sphere!

## 📂 Project Structure

*   `frontend/`: React application (UI/UX).
    *   `src/components/`: UI components (Sphere, Chat, Device Selector).
    *   `src/hooks/`: Custom hooks for Audio and WebSockets.
*   `backend/`: FastAPI server.
    *   `conversation_engines/`: Logic for different AI pipelines.
    *   `audio_providers/`: Interfaces for STT, TTS, and LLM services.
*   `PRD.md`: Product Requirements Document.
*   `SOUL.md`: Agent personality definition.
*   `RULES.md`: Operational constraints.

## 🤝 Contributing

This project is currently in the **Alpha** phase.