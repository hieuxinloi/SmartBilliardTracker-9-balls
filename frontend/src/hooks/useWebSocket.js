import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Custom hook for WebSocket connection to game backend
 * Handles real-time game events: collisions, fouls, turn changes, game end
 */
export const useWebSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [gameState, setGameState] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const eventHandlersRef = useRef({});

  // Connect to WebSocket
  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WebSocket] Connected");
        setIsConnected(true);

        // Start heartbeat
        const heartbeatInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "heartbeat" }));
          }
        }, 30000); // Every 30 seconds

        ws.heartbeatInterval = heartbeatInterval;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[WebSocket] Message:", data);

          setLastMessage(data);

          // Update game state if present
          if (data.game_state) {
            setGameState(data.game_state);
          }

          // Call event-specific handlers
          const eventType = data.event || data.type;
          if (eventType && eventHandlersRef.current[eventType]) {
            eventHandlersRef.current[eventType](data);
          }
        } catch (err) {
          console.error("[WebSocket] Parse error:", err);
        }
      };

      ws.onerror = (error) => {
        console.error("[WebSocket] Error:", error);
      };

      ws.onclose = () => {
        console.log("[WebSocket] Disconnected");
        setIsConnected(false);

        // Clear heartbeat
        if (ws.heartbeatInterval) {
          clearInterval(ws.heartbeatInterval);
        }

        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log("[WebSocket] Reconnecting...");
          connect();
        }, 3000);
      };
    } catch (err) {
      console.error("[WebSocket] Connection error:", err);
    }
  }, [url]);

  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Send message
  const sendMessage = useCallback((message) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("[WebSocket] Not connected, cannot send message");
    }
  }, []);

  // Register event handler
  const on = useCallback((eventType, handler) => {
    eventHandlersRef.current[eventType] = handler;
  }, []);

  // Unregister event handler
  const off = useCallback((eventType) => {
    delete eventHandlersRef.current[eventType];
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    gameState,
    sendMessage,
    on,
    off,
    reconnect: connect,
  };
};

export default useWebSocket;
