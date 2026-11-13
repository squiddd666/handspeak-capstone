export async function fetchJSON(path: string, init?: RequestInit) {
  // Prefer window.SignSpeak helper if available
  // @ts-ignore
  if (typeof window !== 'undefined' && (window as any).SignSpeak?.queryAPI) {
    // @ts-ignore
    return (window as any).SignSpeak.queryAPI(path, init);
  }
  const res = await fetch(path, init);
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export function startDecoding() {
  return fetchJSON('/start', { method: 'POST' });
}

export function stopDecoding() {
  return fetchJSON('/stop', { method: 'POST' });
}

export function getDecodedText() {
  return fetchJSON('/text');
}

export function predict(landmarks: any) {
  return fetchJSON('/predict', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ landmarks }) });
}

export function connectRealtime(
  onMessage: (data: any) => void,
  onOpen?: () => void,
  onClose?: () => void,
  opts?: { autoReconnect?: boolean; reconnectIntervalMs?: number },
) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${location.host}/ws/decode`;
  let ws: WebSocket | null = null;
  let closedByUser = false;
  const autoReconnect = opts?.autoReconnect ?? true;
  const reconnectIntervalMs = opts?.reconnectIntervalMs ?? 2000;

  function create() {
    console.debug('connectRealtime create', wsUrl);
    ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      console.debug('ws open', wsUrl);
      onOpen && onOpen();
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        onMessage(data);
      } catch (e) {
        onMessage(ev.data);
      }
    };
    ws.onerror = (e) => console.error('ws error', e);
    ws.onclose = () => {
      console.debug('ws closed');
      onClose && onClose();
      ws = null;
      if (!closedByUser && autoReconnect) {
        setTimeout(() => create(), reconnectIntervalMs);
      }
    };
  }

  create();

  return {
    close() {
      closedByUser = true;
      try {
        ws?.close();
      } catch {}
    },
    send(data: any) {
      try {
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data));
      } catch {}
    },
  };
}

export default { fetchJSON, startDecoding, stopDecoding, getDecodedText, predict, connectRealtime };
