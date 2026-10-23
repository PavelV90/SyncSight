import { useCallback, useEffect, useRef, useState } from "react";

export type QueryState<T> = { data: T | null; loading: boolean; error: string | null };
type Request<T> = (signal: AbortSignal) => Promise<T>;

/**
 * Run a request on demand. A new run aborts the previous one (the last request wins),
 * previous data stays visible while loading and after an error, and `retry` repeats
 * the last request.
 */
export function useQuery<T>(): [QueryState<T>, (request: Request<T>) => void, () => void] {
  const [state, setState] = useState<QueryState<T>>({ data: null, loading: false, error: null });
  const controller = useRef<AbortController | null>(null);
  const last = useRef<Request<T> | null>(null);

  const run = useCallback((request: Request<T>) => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    last.current = request;
    setState((s) => ({ ...s, loading: true, error: null }));
    request(current.signal)
      .then((data) => {
        if (!current.signal.aborted) setState({ data, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (current.signal.aborted) return;
        const message = error instanceof Error ? error.message : String(error);
        setState((s) => ({ ...s, loading: false, error: message }));
      });
  }, []);

  const retry = useCallback(() => {
    if (last.current) run(last.current);
  }, [run]);

  useEffect(() => () => controller.current?.abort(), []);
  return [state, run, retry];
}
