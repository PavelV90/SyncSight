import { useCallback, useEffect, useRef, useState } from "react";

/** `meta` is whatever the caller passed with the request that produced `data` (e.g. its filters). */
export type QueryState<T, M> = {
  data: T | null;
  meta: M | null;
  loading: boolean;
  error: string | null;
};
type Request<T> = (signal: AbortSignal) => Promise<T>;

/**
 * Run a request on demand. A new run aborts the previous one (the last request wins),
 * previous data stays visible while loading and after an error, and `retry` repeats
 * the last request. `meta` only changes together with `data`, so a summary built from it
 * always describes the rows on screen.
 */
export function useQuery<T, M = undefined>(): [
  QueryState<T, M>,
  (request: Request<T>, meta?: M) => void,
  () => void,
] {
  const [state, setState] = useState<QueryState<T, M>>({
    data: null,
    meta: null,
    loading: false,
    error: null,
  });
  const controller = useRef<AbortController | null>(null);
  const last = useRef<{ request: Request<T>; meta?: M } | null>(null);

  const run = useCallback((request: Request<T>, meta?: M) => {
    controller.current?.abort();
    const current = new AbortController();
    controller.current = current;
    last.current = { request, meta };
    setState((s) => ({ ...s, loading: true, error: null }));
    request(current.signal)
      .then((data) => {
        if (!current.signal.aborted)
          setState({ data, meta: meta ?? null, loading: false, error: null });
      })
      .catch((error: unknown) => {
        if (current.signal.aborted) return;
        const message = error instanceof Error ? error.message : String(error);
        setState((s) => ({ ...s, loading: false, error: message }));
      });
  }, []);

  const retry = useCallback(() => {
    if (last.current) run(last.current.request, last.current.meta);
  }, [run]);

  useEffect(() => () => controller.current?.abort(), []);
  return [state, run, retry];
}
