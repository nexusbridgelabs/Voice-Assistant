import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket Connected");
      setIsConnected(true);
    };

    ws.onclose = (event) => {
      console.log(`WebSocket Disconnected. Code: ${event.code}, Reason: ${event.reason}`);
      setIsConnected(false);
    };

    ws.onmessage = (event) => {
      setLastMessage(event.data);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  const sendMessage = useCallback((msg: string | ArrayBuffer) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(msg);
    }
  }, []);

  return { isConnected, lastMessage, sendMessage };
};
