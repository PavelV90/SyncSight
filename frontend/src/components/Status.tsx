type Props = {
  loading: boolean;
  error: string | null;
  empty: boolean;
  onRetry?: () => void;
  emptyText?: string;
};

/** Loading, error (with Retry) and empty states shared by all views. */
export function Status({ loading, error, empty, onRetry, emptyText = "No results." }: Props) {
  if (error) {
    return (
      <div role="alert" className="status status--error">
        <span>{error}</span>
        {onRetry && (
          <button type="button" onClick={onRetry}>
            Retry
          </button>
        )}
      </div>
    );
  }
  if (loading)
    return (
      <p role="status" className="status">
        Loading…
      </p>
    );
  if (empty) return <p className="status">{emptyText}</p>;
  return null;
}
