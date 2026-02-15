import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = "ws://localhost:8765/ws";
const RECONNECT_INTERVAL_MS = 3_000;

export interface SubTaskInfo {
  id: number;
  desc: string;
  status: string;
}

export interface StateUpdate {
  type: "state_update";
  node: string;
  thought: string;
  node_status: string;
  current_task_index: number;
  total_tasks: number;
  sub_tasks: SubTaskInfo[];
}

interface UseWebSocketReturn {
  status: "connecting" | "connected" | "disconnected";
  updates: StateUpdate[];
  summary: string | null;
  sendIntent: (intent: string) => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<UseWebSocketReturn["status"]>("connecting");
  const [updates, setUpdates] = useState<StateUpdate[]>([]);
  const [summary, setSummary] = useState<string | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setStatus("connected");

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "state_update") {
          setUpdates((prev) => [...prev, msg as StateUpdate]);
        } else if (msg.type === "result") {
          setSummary(msg.summary);
        }
      } catch {
        /* ignore malformed messages */
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      setTimeout(connect, RECONNECT_INTERVAL_MS);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);

  const sendIntent = useCallback((intent: string) => {
    setUpdates([]);
    setSummary(null);
    wsRef.current?.send(JSON.stringify({ type: "intent", payload: intent }));
  }, []);

  return { status, updates, summary, sendIntent };
}
