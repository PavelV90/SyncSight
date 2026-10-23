type Props = {
  items: string[];
  label?: (item: string) => string;
  warn?: (item: string) => boolean;
};

/** Compact tags for multi-valued cells; warnings get an icon and red border. */
export function Chips({ items, label = (i) => i, warn = () => false }: Props) {
  if (!items.length) return <span className="muted">–</span>;
  return (
    <span className="chips">
      {items.map((item) => (
        <span key={item} className={warn(item) ? "chip chip--warning" : "chip"}>
          {warn(item) && <span aria-hidden="true">⚠ </span>}
          {label(item)}
        </span>
      ))}
    </span>
  );
}
