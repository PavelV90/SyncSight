import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => {
  cleanup();
});

// jsdom has no scrolling; the app calls window.scrollTo when opening and closing profiles
window.scrollTo = () => {};
