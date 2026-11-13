import { wsUrl } from "./api";

export type WsMessageHandler = (data: Record<string, unknown>) => void;

export interface WsConnection {
  sendBlob: (blob: Blob) => void;
  sendJSON: (obj: Record<string, unknown>) => void;
  close: () => void;
}

export function connect(
  path: string,
  {
    onOpen,
    onMessage,
    onClose,
    onError,
  }: {
    onOpen?: () => void;
    onMessage?: WsMessageHandler;
    onClose?: () => void;
    onError?: () => void;
  } = {},
): WsConnection {
  const ws = new WebSocket(wsUrl(path));
  ws.binaryType = "arraybuffer";

  let pendingJSON: string[] | null = [];

  ws.onopen = () => {
    if (pendingJSON) {
      for (const m of pendingJSON) ws.send(m);
      pendingJSON = null;
    }
    onOpen?.();
  };
  ws.onmessage = (e) => {
    try {
      onMessage?.(JSON.parse(e.data));
    } catch {
      /* ignore */
    }
  };
  ws.onclose = () => onClose?.();
  ws.onerror = () => onError?.();

  return {
    sendBlob: (blob) => {
      if (ws.readyState !== WebSocket.OPEN) return;
      blob.arrayBuffer().then((buf) => {
        if (ws.readyState === WebSocket.OPEN) ws.send(buf);
      });
    },
    sendJSON: (obj) => {
      const msg = JSON.stringify(obj);
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(msg);
      } else if (pendingJSON) {
        pendingJSON.push(msg);
      }
    },
    close: () => ws.close(),
  };
}
