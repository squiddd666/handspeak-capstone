type OnMessage = (data: any) => void;
type OnOpen = () => void;
type OnClose = () => void;

export function connectRealtime(
  onMessage: OnMessage,
  onOpen?: OnOpen,
  onClose?: OnClose,
  opts?: { autoReconnect?: boolean; maxBackoffMs?: number },
) {
  const autoReconnect = opts?.autoReconnect ?? true;
  const maxBackoffMs = opts?.maxBackoffMs ?? 30000;
  let ws: WebSocket | null = null;
  let closedByUser = false;
  let attempts = 0;

  const buildUrl = () => {
    try {
      const env = (import.meta as any).env || {};
      if (env.VITE_WS_URL) return env.VITE_WS_URL;
    } catch {}
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${location.hostname}:8000/ws/decode`;
  };

  const connect = () => {
    const url = buildUrl();
    console.debug('WS connecting to', url, 'attempt', attempts);
    ws = new WebSocket(url);
    ws.onopen = () => {
      attempts = 0;
      console.debug('WS connected');
      onOpen && onOpen();
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        console.debug('WS message', data);
        onMessage(data);
      } catch (e) {
        console.debug('WS raw message', ev.data);
        onMessage(ev.data);
      }
    };
    ws.onerror = (e) => console.debug('WS error', e);
    ws.onclose = (ev) => {
      console.debug('WS closed', ev.code, ev.reason);
      onClose && onClose();
      ws = null;
      if (!closedByUser && autoReconnect) {
        attempts += 1;
        const delay = Math.min(1000 * Math.pow(2, attempts), maxBackoffMs);
        console.debug('WS reconnect attempt in', delay, 'ms');
        setTimeout(connect, delay);
      }
    };
  };

  connect();

  return {
    close() {
      closedByUser = true;
      try { ws?.close(); } catch {}
    },
    send(data: any) {
      try { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data)); } catch {}
    }
  };
}

export default { connectRealtime };
