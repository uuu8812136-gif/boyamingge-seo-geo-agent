type Column<T> = {
  key: string;
  title: string;
  render?: (row: T) => React.ReactNode;
};

type Props<T> = {
  columns: Column<T>[];
  rows: T[];
  emptyText?: string;
  rowKey?: (row: T, index: number) => string | number;
};

export default function AdminTable<T extends Record<string, unknown>>({
  columns,
  rows,
  emptyText = '暂无数据',
  rowKey,
}: Props<T>) {
  if (rows.length === 0) {
    return (
      <div className="admin-empty">
        <span className="admin-empty-icon" aria-hidden>—</span>
        <p>{emptyText}</p>
      </div>
    );
  }

  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={rowKey ? rowKey(row, idx) : idx}
              style={{ '--row-delay': `${Math.min(idx, 12) * 35}ms` } as React.CSSProperties}
            >
              {columns.map((col) => (
                <td key={col.key}>
                  {col.render ? col.render(row) : String(row[col.key] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
