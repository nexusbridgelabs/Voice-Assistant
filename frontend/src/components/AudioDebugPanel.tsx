import { useState, useEffect } from 'react';
import { Activity, GripHorizontal, X } from 'lucide-react';

interface AudioDebugPanelProps {
  pcmRms: number;
  audioLevel: number;
}

export const AudioDebugPanel = ({ pcmRms, audioLevel }: AudioDebugPanelProps) => {
  const [position, setPosition] = useState({ x: 20, y: 100 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isOpen, setIsOpen] = useState(true);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setPosition({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
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
        className="absolute top-20 right-8 p-3 bg-jarvis-dark/80 border border-jarvis-red text-jarvis-red rounded-full hover:bg-jarvis-red/20 transition-all z-50"
        title="Open Audio Debug"
      >
        <Activity size={24} />
      </button>
    );
  }

  // Threshold markers
  const startThreshold = 1500;
  const stopThreshold = 800;
  const maxScale = 4000; // Visualization Scale Max

  const percentage = Math.min((pcmRms / maxScale) * 100, 100);
  const startPos = (startThreshold / maxScale) * 100;
  const stopPos = (stopThreshold / maxScale) * 100;

  return (
    <div 
      className="absolute flex flex-col w-80 bg-black/80 backdrop-blur-md border border-jarvis-red/30 rounded-xl overflow-hidden shadow-[0_0_15px_rgba(255,50,50,0.2)] z-50"
      style={{ left: position.x, top: position.y }}
    >
      {/* Header / Drag Handle */}
      <div 
        className="flex items-center justify-between p-3 bg-jarvis-red/10 border-b border-jarvis-red/20 cursor-move select-none"
        onMouseDown={handleMouseDown}
      >
        <div className="flex items-center gap-2 text-jarvis-red font-mono text-sm">
          <GripHorizontal size={18} />
          <span>AUDIO DEBUG</span>
        </div>
        <button 
            onClick={() => setIsOpen(false)}
            className="text-jarvis-red/50 hover:text-jarvis-red transition-colors"
        >
            <X size={18} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4 font-mono text-xs text-gray-300">
        
        <div className="flex justify-between items-end">
            <div>
                <div className="text-gray-500 uppercase tracking-wider mb-1">Raw RMS</div>
                <div className="text-2xl text-white font-bold">{pcmRms.toFixed(0)}</div>
            </div>
            <div className="text-right">
                <div className="text-gray-500 uppercase tracking-wider mb-1">State</div>
                <div className={`font-bold ${pcmRms > startThreshold ? 'text-green-400' : pcmRms > stopThreshold ? 'text-yellow-400' : 'text-gray-400'}`}>
                    {pcmRms > startThreshold ? 'SPEAKING' : pcmRms > stopThreshold ? 'HYSTERESIS' : 'SILENT'}
                </div>
            </div>
        </div>

        {/* Visualizer Bar */}
        <div className="relative h-40 bg-gray-900 rounded border border-gray-700 w-full flex items-end overflow-hidden">
            {/* Main Level Bar */}
            <div 
                className="w-full bg-jarvis-red/50 transition-all duration-75 ease-out"
                style={{ height: `${percentage}%` }}
            />
            
            {/* Threshold Lines */}
            <div className="absolute w-full border-t border-green-500 border-dashed opacity-50 text-[9px] text-green-500 pl-1" style={{ bottom: `${startPos}%` }}>
                START ({startThreshold})
            </div>
            <div className="absolute w-full border-t border-yellow-500 border-dashed opacity-50 text-[9px] text-yellow-500 pl-1" style={{ bottom: `${stopPos}%` }}>
                STOP ({stopThreshold})
            </div>
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 gap-2 text-[10px] text-gray-500">
            <div>START_THRESHOLD: <span className="text-gray-300">{startThreshold}</span></div>
            <div>STOP_THRESHOLD: <span className="text-gray-300">{stopThreshold}</span></div>
        </div>
      </div>
    </div>
  );
};
