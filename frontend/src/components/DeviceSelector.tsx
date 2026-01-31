import { useState, useEffect } from 'react';
import { Mic } from 'lucide-react';

interface DeviceSelectorProps {
  onDeviceSelect: (deviceId: string) => void;
  currentDeviceId: string | undefined;
}

export const DeviceSelector = ({ onDeviceSelect, currentDeviceId }: DeviceSelectorProps) => {
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const getDevices = async () => {
      try {
        await navigator.mediaDevices.getUserMedia({ audio: true }); // Request permission first
        const dev = await navigator.mediaDevices.enumerateDevices();
        const audioInputs = dev.filter(d => d.kind === 'audioinput');
        setDevices(audioInputs);
        if (audioInputs.length > 0 && !currentDeviceId) {
           // Auto-select first one if none selected
           onDeviceSelect(audioInputs[0].deviceId);
        }
      } catch (e) {
        console.error("Error getting devices", e);
      }
    };
    getDevices();
    
    navigator.mediaDevices.addEventListener('devicechange', getDevices);
    return () => navigator.mediaDevices.removeEventListener('devicechange', getDevices);
  }, []);

  if (devices.length === 0) return null;

  return (
    <div className="absolute top-8 right-24 z-50">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-jarvis-dark/80 border border-jarvis-blue/30 rounded-full text-jarvis-blue text-xs font-mono hover:bg-jarvis-blue/20 transition-all"
      >
        <Mic size={14} />
        {devices.find(d => d.deviceId === currentDeviceId)?.label.slice(0, 15) || 'Select Mic'}...
      </button>
      
      {isOpen && (
        <div className="absolute top-12 right-0 w-64 bg-black/90 border border-jarvis-blue/30 rounded-lg p-2 flex flex-col gap-1 shadow-xl backdrop-blur-md">
            {devices.map(device => (
                <button
                    key={device.deviceId}
                    onClick={() => {
                        onDeviceSelect(device.deviceId);
                        setIsOpen(false);
                    }}
                    className={`text-left px-3 py-2 text-xs font-mono rounded hover:bg-jarvis-blue/20 transition-colors ${currentDeviceId === device.deviceId ? 'text-jarvis-blue bg-jarvis-blue/10' : 'text-gray-400'}`}
                >
                    {device.label || `Microphone ${devices.indexOf(device) + 1}`}
                </button>
            ))}
        </div>
      )}
    </div>
  );
};
