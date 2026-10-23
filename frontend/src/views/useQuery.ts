import { useCallback, useState } from "react";

type State<T> = { data: T | null; loading: boolean; error: string | null };

/** Run an async request on demand and track its loading/error state. */
export function useQuery<T>(): [State<T>, (request: () => Promise<T>) => void] {
  const [state, setState] = useState<State<T>>({ data: null, loading: false, error: null });
  const run = useCallback((request: () => Promise<T>) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    request()
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((e: unknown) => setState({ data: null, loading: false, error: String(e) }));
  }, []);
  return [state, run];
}
