// eslint-disable-next-line @typescript-eslint/no-explicit-any
const BASE = (import.meta as any).env?.VITE_API_BASE_URL ?? "";

export async function fetchBoard() {
  const res = await fetch(`${BASE}/spot`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
