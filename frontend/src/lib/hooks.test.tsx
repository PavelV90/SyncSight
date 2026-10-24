import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useQuery } from "./useQuery";
import { useSort } from "./useSort";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useQuery", () => {
  it("lets the last request win and aborts the one it replaces", async () => {
    const { result } = renderHook(() => useQuery<string, number>());
    const first = deferred<string>();
    const second = deferred<string>();
    let firstSignal!: AbortSignal;

    act(() => result.current[1]((signal) => ((firstSignal = signal), first.promise), 1));
    act(() => result.current[1](() => second.promise, 2));
    await act(async () => second.resolve("second"));
    await act(async () => first.resolve("first"));

    expect(firstSignal.aborted).toBe(true);
    expect(result.current[0]).toMatchObject({ data: "second", meta: 2, loading: false });
  });

  it("keeps data after an error and retries the last request", async () => {
    const { result } = renderHook(() => useQuery<string, number>());
    await act(async () => result.current[1](() => Promise.resolve("ok"), 1));
    await act(async () => result.current[1](() => Promise.reject(new Error("HTTP 500")), 2));

    expect(result.current[0]).toMatchObject({ data: "ok", meta: 1, error: "HTTP 500" });

    let calls = 0;
    await act(async () =>
      result.current[1](
        () => (++calls === 1 ? Promise.reject(new Error("x")) : Promise.resolve("again")),
        3,
      ),
    );
    await act(async () => result.current[2]());
    expect(result.current[0]).toMatchObject({ data: "again", meta: 3, error: null });
  });
});

describe("useSort", () => {
  const rows = [
    { n: "b", v: 2 },
    { n: "", v: null },
    { n: "a", v: 10 },
  ];

  it("sorts numbers and text, keeps empty values last and resets", () => {
    const { result } = renderHook(() =>
      useSort(rows, { name: (r) => r.n, value: (r) => r.v }, { key: "value", dir: "desc" }),
    );
    expect(result.current.sorted.map((r) => r.v)).toEqual([10, 2, null]);

    act(() => result.current.toggle("name"));
    expect(result.current.sorted.map((r) => r.n)).toEqual(["a", "b", ""]);

    act(() => result.current.reset());
    expect(result.current.sortKey).toBe("value");
  });
});
