/** Search operators of Postgres websearch_to_tsquery, as used by the API. */
export function SearchSyntaxHint({ id }: { id: string }) {
  return (
    <span id={id} className="hint small">
      All words must match. <code>medtech or diagnostics</code> · <code>"cell therapy"</code> ·{" "}
      <code>-consulting</code> excludes a word.
    </span>
  );
}
