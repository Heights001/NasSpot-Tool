import useSWR from "swr";
import type { ForecastResponse } from "../types";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useForecast() {
  const { data, error, isLoading } = useSWR<ForecastResponse>("/forecast", fetcher, {
    refreshInterval: 6 * 60 * 60 * 1000,  // 6h — model only updates daily
    revalidateOnFocus: false,
  });
  return { forecast: data, error, isLoading };
}
