import useSWR from "swr";
import { IntelResponse } from "../types";

const fetcher = (url: string): Promise<IntelResponse> =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`Intel fetch ${r.status}`);
    return r.json();
  });

export function useIntel() {
  const { data, error, isLoading } = useSWR<IntelResponse>("/intel", fetcher, {
    refreshInterval: 5 * 60 * 1000,
    revalidateOnFocus: false,
  });
  return { intel: data ?? null, intelError: error, intelLoading: isLoading };
}
