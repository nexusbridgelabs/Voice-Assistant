import { useState, useEffect, useRef } from 'react';
import { Activity, X } from 'lucide-react';

interface AudioDebugPanelProps {
  pcmRms: number;
  analyser: AnalyserNode | null | undefined;
}

export const AudioDebugPanel = ({ pcmRms, analyser }: AudioDebugPanelProps) => {
  const [position, setPosition] = useState({ x: 20, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isOpen, setIsOpen] = useState(true);
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const requestRef = useRef<number>(0);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  // Global mouse up/move to catch drags that go outside the element
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

  // Visualizer Animation Loop
  useEffect(() => {
    if (!isOpen || !analyser || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      requestRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      // Clear with slight fade for trail effect
      ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / (bufferLength / 2)) * 2.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength / 2; i++) {
        barHeight = (dataArray[i] / 255) * canvas.height;

        // Digital Cyan/Blue Gradient
        const gradient = ctx.createLinearGradient(0, canvas.height, 0, canvas.height - barHeight);
        gradient.addColorStop(0, '#0066ff');
        gradient.addColorStop(0.5, '#00f0ff');
        gradient.addColorStop(1, '#ffffff');

        ctx.fillStyle = gradient;
        
        // Add a small glow effect to the top of the bars
        ctx.shadowBlur = 10;
        ctx.shadowColor = '#00f0ff';
        
        ctx.fillRect(x, canvas.height - barHeight, barWidth - 2, barHeight);
        
        ctx.shadowBlur = 0; // Reset for next bar
        x += barWidth;
      }
    };

    draw();
    return () => cancelAnimationFrame(requestRef.current);
  }, [isOpen, analyser]);

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)}
        className="absolute top-20 right-8 p-3 bg-jarvis-dark/80 border border-jarvis-red text-jarvis-red rounded-full hover:bg-jarvis-red/20 transition-all z-50 shadow-[0_0_10px_rgba(255,50,50,0.3)]"
        title="Open Audio Debug"
      >
        <Activity size={24} />
      </button>
    );
  }

  // Threshold markers (Matching backend constants for visual reference)
  const startThreshold = 4000;
  const stopThreshold = 3000;
  const maxScale = 10000; // Visual scale for RMS

  const percentage = Math.min((pcmRms / maxScale) * 100, 100);
  const startPos = (startThreshold / maxScale) * 100;
  const stopPos = (stopThreshold / maxScale) * 100;

  return (
    <div 
      className="absolute flex flex-col w-80 bg-black/90 backdrop-blur-xl border border-jarvis-blue/30 rounded-xl overflow-hidden shadow-[0_0_20px_rgba(0,240,255,0.15)] z-50 transition-all duration-300"
      style={{ left: position.x, top: position.y }}
    >
      {/* Header / Drag Handle */}
      <div 
        className="flex items-center justify-between p-3 bg-jarvis-blue/10 border-b border-jarvis-blue/20 cursor-move select-none"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-2 text-jarvis-blue font-mono text-xs tracking-widest">
          <Activity size={14} className="animate-pulse" />
          <span>AUDIO SIGNAL ANALYZER</span>
        </div>
        <button 
            onClick={() => setIsOpen(false)}
            className="text-jarvis-blue/50 hover:text-jarvis-blue transition-colors"
        >
            <X size={16} />
        </button>
      </div>

      {/* Frequency Visualizer (The "Cool" part) */}
      <div className="relative h-24 bg-gray-950/50 border-b border-white/5">
        <canvas 
            ref={canvasRef} 
            width={320} 
            height={96} 
            className="w-full h-full opacity-80"
        />
        <div className="absolute top-2 left-2 flex gap-1">
            <div className="w-1 h-1 bg-jarvis-blue rounded-full animate-ping" />
            <span className="text-[8px] text-jarvis-blue/60 font-mono">LIVE SPECTRUM</span>
        </div>
      </div>

      {/* RMS Content */}
      <div className="p-4 space-y-4 font-mono text-xs text-gray-300">
        
        <div className="flex justify-between items-end">
            <div>
                <div className="text-gray-500 uppercase tracking-[0.2em] text-[9px] mb-1">Root Mean Square</div>
                <div className="text-2xl text-white font-bold tabular-nums tracking-tighter">{pcmRms.toFixed(0)}</div>
            </div>
            <div className="text-right">
                <div className="text-gray-500 uppercase tracking-[0.2em] text-[9px] mb-1">Logic State</div>
                <div className={`font-bold px-2 py-0.5 rounded border ${
                    pcmRms > startThreshold 
                        ? 'text-green-400 border-green-400/30 bg-green-400/5' 
                        : pcmRms > stopThreshold 
                            ? 'text-yellow-400 border-yellow-400/30 bg-yellow-400/5' 
                            : 'text-gray-500 border-gray-500/30 bg-gray-500/5'
                }`}>
                    {pcmRms > startThreshold ? 'SPEAKING' : pcmRms > stopThreshold ? 'HYSTERESIS' : 'SILENCE'}
                </div>
            </div>
        </div>

        {/* RMS Level Bar */}
        <div className="relative h-12 bg-gray-900/80 rounded border border-white/5 w-full flex items-end overflow-hidden group">
            {/* Main Level Bar */}
            <div 
                className="w-full bg-gradient-to-t from-jarvis-blue/40 to-white/20 transition-all duration-75 ease-out"
                style={{ height: `${percentage}%` }}
            />
            
            {/* Threshold Lines */}
            <div className="absolute w-full border-t border-green-500/50 border-dashed z-10" style={{ bottom: `${startPos}%` }}>
                <span className="absolute -top-3 left-1 text-[7px] text-green-500/80">TRIG_START</span>
            </div>
            <div className="absolute w-full border-t border-yellow-500/50 border-dashed z-10" style={{ bottom: `${stopPos}%` }}>
                <span className="absolute -top-3 right-1 text-[7px] text-yellow-500/80">TRIG_STOP</span>
            </div>
        </div>

        {/* Metadata Footer */}
        <div className="flex justify-between items-center pt-2 border-t border-white/5 text-[9px] text-gray-600">
            <div className="flex gap-3">
                <span>SRC: 16KHZ_MONO</span>
                <span>FFT: 256</span>
            </div>
            <div className="text-jarvis-blue/40 uppercase tracking-widest">v2.1.0_debug</div>
        </div>
      </div>
    </div>
  );
};