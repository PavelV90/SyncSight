import { useEffect, useState } from "react";

type Health = { status: string; version: string };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<Health>;
      })
      .then(setHealth)
      .catch(() => setFailed(true));
  }, []);

  let status = "Checking API…";
  if (failed) status = "API unreachable";
  else if (health) status = `API ${health.status} (v${health.version})`;

  return (
    <main>
      <h1>SyncSight</h1>
      <p>Swiss company intelligence</p>
      <p role="status">{status}</p>
    </main>
  );
}
