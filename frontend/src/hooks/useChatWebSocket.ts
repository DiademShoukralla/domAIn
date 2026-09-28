import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessageIn, ChatResponse, IncomingFrame } from "../types/chat";
import { isChatResponse, isChatStatusUpdate } from "../types/chat";

interface UseChatWebSocketOptions {
  enabled: boolean;
  onStatus: (frame: IncomingFrame) => void;
  onError: (message: string) => void;
}

function websocketUrl(): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/chat/ws`;
}

export function useChatWebSocket({ enabled, onStatus, onError }: UseChatWebSocketOptions) {
  const socketRef = useRef<WebSocket | null>(null);
  const onStatusRef = useRef(onStatus);
  const onErrorRef = useRef(onError);
  const pendingTurnRef = useRef<{
    resolve: (response: ChatResponse) => void;
    reject: (error: Error) => void;
  } | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    onStatusRef.current = onStatus;
  }, [onStatus]);

  useEffect(() => {
    onErrorRef.current = onError;
  }, [onError]);

  useEffect(() => {
    if (!enabled) {
      setConnected(false);
      return;
    }

    const socket = new WebSocket(websocketUrl());
    socketRef.current = socket;

    socket.addEventListener("open", () => {
      setConnected(true);
    });

    socket.addEventListener("close", () => {
      setConnected(false);
      pendingTurnRef.current?.reject(new Error("Chat connection closed."));
      pendingTurnRef.current = null;
    });

    socket.addEventListener("error", () => {
      onErrorRef.current("Chat connection failed. Sign in again or refresh the page.");
    });

    socket.addEventListener("message", (event) => {
      try {
        const frame = JSON.parse(String(event.data)) as IncomingFrame;
        if (isChatStatusUpdate(frame)) {
          onStatusRef.current(frame);
          return;
        }
        if (isChatResponse(frame)) {
          pendingTurnRef.current?.resolve(frame);
          pendingTurnRef.current = null;
        }
      } catch {
        onErrorRef.current("Received an invalid chat frame from the server.");
        pendingTurnRef.current?.reject(new Error("Received an invalid chat frame from the server."));
        pendingTurnRef.current = null;
      }
    });

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [enabled]);

  const sendMessage = useCallback((payload: ChatMessageIn): Promise<ChatResponse> => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error("Chat is not connected."));
    }
    if (pendingTurnRef.current) {
      return Promise.reject(new Error("A message is already in flight."));
    }

    return new Promise((resolve, reject) => {
      pendingTurnRef.current = { resolve, reject };
      socket.send(JSON.stringify(payload));
    });
  }, []);

  return {
    connected,
    sendMessage,
  };
}
