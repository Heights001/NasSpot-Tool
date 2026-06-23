// eslint-disable-next-line @typescript-eslint/no-explicit-any
const BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? "";

export async function apiFetch(path: string) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function fetchBoard() {
  return apiFetch("/spot");
}
