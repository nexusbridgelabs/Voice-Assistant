# JARVIS Voice Assistant

JARVIS is a sophisticated, highly interactive voice assistant featuring a futuristic 3D visual interface. It is designed to be a "living" digital companion with a distinct personality, capable of real-time, interruptible conversation.

## 🚀 Features

*   **Immersive 3D UI:** A "nebulous sphere" visualizer (built with React Three Fiber) that reacts dynamically to agent states (Listening, Thinking, Speaking).
*   **Real-time Voice Interaction:** Low-latency voice processing.
*   **Smart "Barge-in":** The user can interrupt the agent while it is speaking, and it will immediately stop and listen.
*   **Cloud-Native Intelligence:**
    *   **Hearing:** Deepgram (Speech-to-Text & VAD).
    *   **Thinking & Speaking:** Google Gemini 2.0 (Multimodal LLM & Native Audio Generation).
*   **Memory (Coming Soon):** Long-term persistence via Mem0.

## 🛠️ Tech Stack

*   **Frontend:** React (Vite), TypeScript, Tailwind CSS, Three.js.
*   **Backend:** Python (FastAPI), WebSockets.
*   **AI Services:** Google Gemini API, Deepgram API.

## 📋 Prerequisites

*   **Node.js** (v18+)
*   **Python** (v3.10+)
*   **API Keys:**
    *   [Google Gemini API Key](https://aistudio.google.com/)
    *   [Deepgram API Key](https://console.deepgram.com/)

## ⚡ Quick Start Guide

### 1. Clone & Setup Secrets

```bash
# Clone the repository (if you haven't already)
git clone <your-repo-url>
cd voice-assistant

# Set up Backend Secrets
cd backend
cp .env.example .env
# Edit .env and paste your Google and Deepgram API keys
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
2.  Click the **Power Icon** to wake JARVIS.
3.  Allow microphone permissions.
4.  Speak to the sphere!

## 📂 Project Structure

*   `frontend/`: React application (UI/UX).
*   `backend/`: FastAPI server (Orchestration, AI calls).
*   `PRD.md`: Product Requirements Document.
*   `SOUL.md`: Agent personality definition.
*   `RULES.md`: Operational constraints.

## 🤝 Contributing

This project is currently in the **Alpha** phase.
