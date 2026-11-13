export function wsUrl(path: string): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}${path}`;
}

export async function fetchStatus(): Promise<{ ok: boolean; model_loaded: boolean }> {
  const res = await fetch("/api/status");
  if (!res.ok) throw new Error("status request failed");
  return res.json();
}
