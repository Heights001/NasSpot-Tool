import useSWR from "swr";
import { fetchBoard } from "../lib/api";
import type { SpotBoardResponse } from "../types";

const REFRESH_MS = 30_000;

export function useSpotPrices() {
  const { data, error, isLoading } = useSWR<SpotBoardResponse>(
    "spot-board",
    fetchBoard,
    { refreshInterval: REFRESH_MS, revalidateOnFocus: false }
  );
  return { data, error, isLoading };
}
