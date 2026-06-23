import useSWR from "swr";
import type { SignalsResponse } from "../types";
import { apiFetch } from "../lib/api";

export function useSignals() {
  const { data, error } = useSWR<SignalsResponse>(
    "/signals",
    (url: string) => apiFetch(url),
    { refreshInterval: 5 * 60 * 1000, revalidateOnFocus: false }
  );
  return { signals: data ?? null, error };
}
