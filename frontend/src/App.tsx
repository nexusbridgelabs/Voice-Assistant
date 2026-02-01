import { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { Mic, Power } from 'lucide-react';
import { JarvisSphere } from './components/JarvisSphere';
import { ChatPanel } from './components/ChatPanel';
import { DeviceSelector } from './components/DeviceSelector';
import type { Message } from './types';
import { useAudio } from './hooks/useAudio';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
  const [appState, setAppState] = useState<'idle' | 'listening' | 'processing' | 'speaking'>('idle');
  const [messages, setMessages] = useState<Message[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>();
  
  const { isListening, audioLevel, startListening, stopListening, playAudioChunk } = useAudio();
  const { isConnected, sendMessage, lastMessage } = useWebSocket('ws://localhost:8000/ws');
  
  // Ref to access current state/level in callbacks without dependency issues (Stale Closure Fix)
  const audioLevelRef = useRef(0);
  const appStateRef = useRef(appState);

  useEffect(() => {
    audioLevelRef.current = audioLevel;
  }, [audioLevel]);

  useEffect(() => {
    appStateRef.current = appState;
  }, [appState]);

  const handleAudioData = (data: ArrayBuffer) => {
    // Debugging Audio Flow
    // console.log(`Audio Check - State: ${appStateRef.current}, Level: ${audioLevelRef.current.toFixed(4)}`);

    // Software Audio Gate
    // 1. Block while THINKING (Processing) to prevent queuing.
    // With Live API, we want to allow barge-in, so we might NOT want to block.
    // But let's keep it simple for now or relax it.
    // if (appStateRef.current === 'processing') return; 

    // Noise Gate: Filter out fan noise/silence (Threshold: 1%)
    if (audioLevelRef.current < 0.01) return;

    if (isConnected) {
        sendMessage(data);
    }
  };

  const togglePower = () => {
    if (isListening) {
      stopListening();
      setAppState('idle');
    } else {
      startListening(handleAudioData, selectedDeviceId);
      setAppState('listening');
    }
  };

  const handleSendMessage = (text: string) => {
    // Add user message to UI immediately
    const newMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        text: text,
        timestamp: Date.now()
    };
    setMessages(prev => [...prev, newMessage]);
    setAppState('processing'); // Visual feedback
    
    // Send to backend
    sendMessage(JSON.stringify({ type: 'text', content: text }));
  };

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage) {
        try {
            const data = JSON.parse(lastMessage);
            
            if (data.type === 'state') {
                if (data.state === 'processing') setAppState('processing');
            } 
            else if (data.type === 'audio') {
                playAudioChunk(data.data);
                setAppState('speaking');
            }
            else if (data.type === 'turn_complete') {
                setAppState('listening');
            }
            else if (data.type === 'transcript') {
                // User transcript from backend (if available) or intermediate
                setMessages(prev => {
                    // Logic to update user message ...
                    // For now, assuming Google doesn't send user transcript often, 
                    // this might be rare.
                    return prev;
                });
            } else if (data.type === 'response_chunk') {
                 // Text response from Assistant
                 setMessages(prev => {
                    const lastMsg = prev[prev.length - 1];
                    const isLastPartial = lastMsg?.role === 'assistant' && lastMsg?.isPartial;

                    if (isLastPartial) {
                        return [...prev.slice(0, -1), { 
                            ...lastMsg, 
                            text: lastMsg.text + data.content 
                        }];
                    } else {
                        return [...prev, {
                            id: Date.now().toString(),
                            role: 'assistant',
                            text: data.content,
                            timestamp: Date.now(),
                            isPartial: true
                        }];
                    }
                 });
            } else if (data.type === 'reset_audio') {
                console.log("Resetting audio stream...");
                stopListening();
                setTimeout(() => {
                    startListening(handleAudioData, selectedDeviceId);
                    sendMessage(JSON.stringify({ type: "audio_reset_complete" }));
                }, 100);
            } else if (data.type === 'error') {
                setMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    role: 'assistant',
                    text: `Error: ${data.content}`,
                    timestamp: Date.now()
                }]);
                setAppState('listening');
            }
        } catch (e) {
             console.log("Non-JSON message:", lastMessage);
        }
    }
  }, [lastMessage]);


  return (
    <div className="w-full h-screen bg-black text-gray-100 flex flex-col items-center justify-center relative overflow-hidden font-mono selection:bg-jarvis-blue/30 selection:text-jarvis-blue">
      
      {/* --- High-Tech Background Layers --- */}
      
      {/* 1. Deep Radial Glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,_rgba(0,20,40,1)_0%,_rgba(0,0,0,1)_80%)] z-0"></div>
      
      {/* 2. Cyber Grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,240,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(0,240,255,0.05)_1px,transparent_1px)] bg-[size:50px_50px] [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_100%)] z-0 opacity-50 perspective-1000 transform-gpu"></div>
      
      {/* 3. Scanlines & CRT Flicker */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[size:100%_4px,3px_100%] pointer-events-none z-50 opacity-20"></div>
      
      {/* Header / Status */}
      <div className="absolute top-8 left-8 z-10">
        <h1 className="text-4xl font-bold tracking-[0.2em] text-transparent bg-clip-text bg-gradient-to-r from-jarvis-blue to-white drop-shadow-[0_0_10px_rgba(0,240,255,0.8)]">
          JARVIS
        </h1>
        <div className="flex items-center gap-3 mt-2 pl-1 border-l-2 border-jarvis-blue/50">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400 shadow-[0_0_10px_rgba(74,222,128,1)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,1)]'} transition-all duration-500`} />
          <span className="text-xs text-jarvis-blue/80 tracking-widest uppercase">
            {isConnected ? 'Systems Nominal' : 'Connection Lost'}
          </span>
        </div>
      </div>

      <DeviceSelector 
        currentDeviceId={selectedDeviceId} 
        onDeviceSelect={setSelectedDeviceId} 
      />

      {/* Chat Panel (Floating) */}
      <ChatPanel messages={messages} onSendMessage={handleSendMessage} />

      {/* 3D Visualizer Canvas */}
      <div className="w-full h-full absolute inset-0 z-0">
        <Canvas camera={{ position: [0, 0, 4] }}>
          <ambientLight intensity={0.2} />
          <pointLight position={[10, 10, 10]} intensity={1.5} color="#00f0ff" />
          <pointLight position={[-10, -5, -10]} intensity={1} color="#ff00aa" />
          <JarvisSphere state={appState} audioLevel={audioLevel} />
          <OrbitControls enableZoom={false} enablePan={false} maxPolarAngle={Math.PI / 1.5} minPolarAngle={Math.PI / 2.5} />
        </Canvas>
      </div>

      {/* Controls */}
      <div className="absolute bottom-20 flex gap-8 z-20 items-center">
        
        {/* Main Power/Toggle */}
        <button 
          onClick={togglePower}
          className={`relative group p-8 rounded-full border border-jarvis-blue/30 backdrop-blur-md transition-all duration-500 ${
            isListening 
              ? 'bg-red-500/10 border-red-500/50 shadow-[0_0_50px_rgba(239,68,68,0.4)]' 
              : 'bg-jarvis-blue/5 hover:bg-jarvis-blue/10 shadow-[0_0_30px_rgba(0,240,255,0.1)] hover:shadow-[0_0_50px_rgba(0,240,255,0.3)]'
          }`}
        >
          <div className={`absolute inset-0 rounded-full border border-t-transparent border-jarvis-blue/50 w-full h-full animate-spin-slow ${isListening ? 'border-red-500/50' : ''}`} />
          <Power size={32} className={`relative z-10 transition-all duration-500 ${
            isListening ? 'text-red-400 scale-110 drop-shadow-[0_0_10px_rgba(239,68,68,0.8)]' : 'text-jarvis-blue group-hover:scale-110 drop-shadow-[0_0_5px_rgba(0,240,255,0.8)]'
          }`} />
        </button>

        {/* PTT (Only visible when paused) */}
        {!isListening && (
            <button 
              className="p-6 rounded-full border border-green-500/30 bg-green-500/5 backdrop-blur-md hover:bg-green-500/10 active:scale-95 transition-all shadow-[0_0_20px_rgba(74,222,128,0.1)] group"
              onMouseDown={() => { startListening(handleAudioData); setAppState('listening'); }}
              onMouseUp={() => { stopListening(); setAppState('idle'); }}
            >
              <Mic size={24} className="text-green-400 group-hover:drop-shadow-[0_0_8px_rgba(74,222,128,0.8)] transition-all" />
            </button>
        )}
        
      </div>

      {/* State Indicator Text */}
      <div className="absolute bottom-12 w-full text-center pointer-events-none">
         <div className="inline-block px-4 py-1 border-x border-jarvis-blue/20 bg-black/50 backdrop-blur text-jarvis-blue/60 font-mono text-[10px] tracking-[0.5em] uppercase">
            STATUS: {appState}
         </div>
      </div>

    </div>
  );
}

export default App;
