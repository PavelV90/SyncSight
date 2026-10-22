import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("App", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows API status and version from /api/health", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ok", version: "0.1.0" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("API ok (v0.1.0)")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/health");
  });

  it("reports when the API is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("", { status: 502 })));

    render(<App />);

    expect(await screen.findByText("API unreachable")).toBeInTheDocument();
  });
});
