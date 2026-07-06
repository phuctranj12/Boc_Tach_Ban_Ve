export default function SheetList({ sheets, activePage, onSelect }) {
  return (
    <div className="section">
      <h2>Danh sách Sheet ({sheets.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Trang</th>
            <th>Mã sheet</th>
            <th>Loại</th>
            <th>Tiêu đề</th>
            <th>Đối tượng</th>
            <th>Dây</th>
          </tr>
        </thead>
        <tbody>
          {sheets.map((s) => (
            <tr
              key={s.page}
              className={`sheet-row ${s.page === activePage ? "active" : ""}`}
              onClick={() => onSelect(s.page)}
            >
              <td>{s.page}</td>
              <td>{s.sheet_no || "—"}</td>
              <td>{s.sheet_type}</td>
              <td className="muted">{s.title || "—"}</td>
              <td>{s.object_count}</td>
              <td>{s.wire_segments}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
