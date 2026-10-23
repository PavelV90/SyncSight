type Props = { loading: boolean; error: string | null; empty: boolean };

export function Status({ loading, error, empty }: Props) {
  if (loading) return <p role="status">Loading…</p>;
  if (error) return <p role="alert">Request failed: {error}</p>;
  if (empty) return <p role="status">No results.</p>;
  return null;
}
