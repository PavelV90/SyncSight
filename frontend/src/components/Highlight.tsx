/** Render text with ⟦…⟧ markers (from the API) as <mark>, without injecting HTML. */
export function Highlight({ text }: { text: string }) {
  const parts = text.split(/⟦|⟧/);
  return <>{parts.map((part, i) => (i % 2 === 1 ? <mark key={i}>{part}</mark> : part))}</>;
}
