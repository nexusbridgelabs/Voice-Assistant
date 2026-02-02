import { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, GripHorizontal, X } from 'lucide-react';
import type { Message } from '../types';

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
}

export const ChatPanel = ({ messages, onSendMessage }: ChatPanelProps) => {
  const [position, setPosition] = useState({ x: window.innerWidth - 420, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [input, setInput] = useState('');
  const [isOpen, setIsOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSendMessage(input.trim());
      setInput('');
    }
  };

  // Global mouse up to catch drags that go outside the element
  useEffect(() => {
    const handleGlobalMouseUp = () => setIsDragging(false);
    const handleGlobalMouseMove = (e: MouseEvent) => {
        if (isDragging) {
            setPosition({
                x: e.clientX - dragOffset.x,
                y: e.clientY - dragOffset.y
            });
        }
    }
    
    if (isDragging) {
        window.addEventListener('mouseup', handleGlobalMouseUp);
        window.addEventListener('mousemove', handleGlobalMouseMove);
    }
    return () => {
        window.removeEventListener('mouseup', handleGlobalMouseUp);
        window.removeEventListener('mousemove', handleGlobalMouseMove);
    };
  }, [isDragging, dragOffset]);


  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="absolute top-8 right-8 p-3 bg-jarvis-dark/80 border border-jarvis-blue text-jarvis-blue rounded-full hover:bg-jarvis-blue/20 transition-all z-50"
      >
        <MessageSquare size={24} />
      </button>
    );
  }

  return (
    <div 
      className="absolute flex flex-col w-96 h-[600px] bg-black/80 backdrop-blur-md border border-jarvis-blue/30 rounded-xl overflow-hidden shadow-[0_0_15px_rgba(0,240,255,0.2)] z-50"
      style={{ left: position.x, top: position.y }}
    >
      {/* Header / Drag Handle */}
      <div 
        className="flex items-center justify-between p-3 bg-jarvis-blue/10 border-b border-jarvis-blue/20 cursor-move select-none"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-2 text-jarvis-blue font-mono text-sm">
          <GripHorizontal size={18} />
          <span>LOGS</span>
        </div>
        <button 
            onClick={() => setIsOpen(false)}
            className="text-jarvis-blue/50 hover:text-jarvis-blue transition-colors"
        >
            <X size={18} />
        </button>
      </div>

      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-jarvis-blue/20 scrollbar-track-transparent"
      >
        {messages.length === 0 && (
            <div className="text-center text-gray-500 text-xs font-mono mt-10">
                NO DATA LOGGED.
            </div>
        )}
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div 
              className={`max-w-[85%] p-3 rounded-lg text-sm font-mono leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-jarvis-blue/20 text-jarvis-blue border border-jarvis-blue/20' 
                  : 'bg-gray-800/50 text-gray-300 border border-gray-700'
              } ${msg.isPartial ? 'animate-pulse opacity-70' : ''}`}
            >
              {msg.text}
            </div>
            <span className="text-[10px] text-gray-600 mt-1 uppercase tracking-wider">
                {msg.role}
            </span>
          </div>
        ))}
      </div>

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-jarvis-blue/20 bg-black/40">
        <div className="flex gap-2">
            <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Enter command..."
                className="flex-1 bg-gray-900/50 border border-jarvis-blue/30 rounded px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-jarvis-blue placeholder-gray-600 font-mono"
            />
            <button 
                type="submit"
                disabled={!input.trim()}
                className="p-2 bg-jarvis-blue/10 text-jarvis-blue rounded hover:bg-jarvis-blue/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
                <Send size={18} />
            </button>
        </div>
      </form>
    </div>
  );
};
