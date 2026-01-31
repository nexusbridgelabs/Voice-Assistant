import { useState, useEffect, useRef, useCallback } from 'react';

export const useAudio = () => {
  const [isListening, setIsListening] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyzerRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const startListening = useCallback(async (onAudioData?: (data: Blob) => void, deviceId?: string) => {
    try {
      const constraints = { 
        audio: { 
            deviceId: deviceId ? { exact: deviceId } : undefined,
            channelCount: 1,
            sampleRate: 16000, // Deepgram prefers 16k
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true
        } 
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = audioContext;

      const analyzer = audioContext.createAnalyser();
      analyzer.fftSize = 256;
      analyzerRef.current = analyzer;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;
      source.connect(analyzer);

      const dataArray = new Uint8Array(analyzer.frequencyBinCount);
      dataArrayRef.current = dataArray;

      // MediaRecorder for streaming audio data
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0 && onAudioData) {
            onAudioData(event.data);
        }
      };

      mediaRecorder.start(100); // Chunk every 100ms

      setIsListening(true);
      analyzeAudio();

    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  }, []);

  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    setIsListening(false);
    setAudioLevel(0);
  }, []);

  const analyzeAudio = () => {
    if (!analyzerRef.current || !dataArrayRef.current) return;

    analyzerRef.current.getByteFrequencyData(dataArrayRef.current);
    
    // Calculate average volume
    let sum = 0;
    for (let i = 0; i < dataArrayRef.current.length; i++) {
      sum += dataArrayRef.current[i];
    }
    const average = sum / dataArrayRef.current.length;
    
    // Normalize to 0-1 range
    const normalizedLevel = Math.min(average / 128, 1);
    setAudioLevel(normalizedLevel);

    animationFrameRef.current = requestAnimationFrame(analyzeAudio);
  };

  useEffect(() => {
    return () => {
      stopListening();
    };
  }, [stopListening]);

  return { isListening, audioLevel, startListening, stopListening, stream: streamRef.current };
};
