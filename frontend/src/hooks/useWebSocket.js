import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Custom hook for WebSocket connection to game backend
 * Handles real-time game events with automatic reconnection and heartbeat
 */
export const useWebSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected"); // 'disconnected', 'connecting', 'connected', 'error'
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const [lastMessage, setLastMessage] = useState(null);
  const [gameState, setGameState] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const heartbeatIntervalRef = useRef(null);
  const pingTimeoutRef = useRef(null);
  const eventHandlersRef = useRef({});
  const manualCloseRef = useRef(false);

  // Reconnection settings
  const MAX_RECONNECT_ATTEMPTS = 10;
  const BASE_DELAY = 1000; // 1 second
  const MAX_DELAY = 30000; // 30 seconds
  const PING_INTERVAL = 30000; // 30 seconds
  const PONG_TIMEOUT = 10000; // 10 seconds

  // Clear all timers
  const clearTimers = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }
    if (pingTimeoutRef.current) {
      clearTimeout(pingTimeoutRef.current);
      pingTimeoutRef.current = null;
    }
  }, []);

  // Start heartbeat/ping mechanism
  const startHeartbeat = useCallback(() => {
    clearTimers();

    heartbeatIntervalRef.current = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "heartbeat" }));

        // Set pong timeout
        pingTimeoutRef.current = setTimeout(() => {
          console.warn("[WebSocket] Ping timeout - connection may be dead");
          // Force reconnection
          if (wsRef.current) {
            wsRef.current.close();
          }
        }, PONG_TIMEOUT);
      }
    }, PING_INTERVAL);
  }, [clearTimers, PING_INTERVAL, PONG_TIMEOUT]);

  // Reconnect with exponential backoff
  const scheduleReconnect = useCallback(() => {
    if (manualCloseRef.current) {
      return; // Don't reconnect if manually closed
    }

    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      console.error("[WebSocket] Max reconnect attempts reached");
      setConnectionStatus("error");
      return;
    }

    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (max)
    const delay = Math.min(
      BASE_DELAY * Math.pow(2, reconnectAttempts),
      MAX_DELAY
    );
    console.log(
      `[WebSocket] Reconnecting in ${delay}ms (attempt ${
        reconnectAttempts + 1
      }/${MAX_RECONNECT_ATTEMPTS})`
    );

    setConnectionStatus("disconnected");

    reconnectTimeoutRef.current = setTimeout(() => {
      setReconnectAttempts((prev) => prev + 1);
      connect();
    }, delay);
  }, [reconnectAttempts, MAX_RECONNECT_ATTEMPTS, BASE_DELAY, MAX_DELAY]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log("[WebSocket] Already connected");
      return;
    }

    clearTimers();
    setConnectionStatus("connecting");

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("[WebSocket] Connected successfully");
        setIsConnected(true);
        setConnectionStatus("connected");
        setReconnectAttempts(0); // Reset counter on successful connection
        startHeartbeat();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[WebSocket] Message:", data);

          // Reset ping timeout on any message (acts as pong)
          if (pingTimeoutRef.current) {
            clearTimeout(pingTimeoutRef.current);
            pingTimeoutRef.current = null;
          }

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
        setConnectionStatus("error");
      };

      ws.onclose = (event) => {
        console.log("[WebSocket] Disconnected", event.code, event.reason);
        setIsConnected(false);
        clearTimers();

        // Attempt to reconnect unless manually closed
        if (!manualCloseRef.current) {
          scheduleReconnect();
        }
      };
    } catch (err) {
      console.error("[WebSocket] Connection error:", err);
      setConnectionStatus("error");
      scheduleReconnect();
    }
  }, [url, clearTimers, startHeartbeat, scheduleReconnect]);

  // Disconnect (manual close - won't auto-reconnect)
  const disconnect = useCallback(() => {
    manualCloseRef.current = true;
    clearTimers();
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionStatus("disconnected");
  }, [clearTimers]);

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
    manualCloseRef.current = false;
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    connectionStatus, // 'disconnected', 'connecting', 'connected', 'error'
    reconnectAttempts,
    lastMessage,
    gameState,
    sendMessage,
    on,
    off,
    reconnect: connect,
    disconnect,
  };
};

export default useWebSocket;
