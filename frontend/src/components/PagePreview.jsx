import { pagePreviewUrl } from "../api/client";

const COLORS = {
  switch: "var(--switch)",
  light: "var(--light)",
  socket: "var(--socket)",
  distribution_board: "var(--db)",
  breaker: "var(--breaker)",
  equipment: "var(--equipment)",
};

// Vẽ chấm đối tượng đè lên ảnh render của trang (theo % toạ độ PDF).
// Có thanh điều hướng để lật qua tất cả các trang của bản vẽ gốc.
export default function PagePreview({ jobId, sheets, activePage, onSelect, nodes }) {
  const sheet = sheets.find((s) => s.page === activePage);
  if (!sheet) return null;

  const idx = sheets.findIndex((s) => s.page === activePage);
  const goto = (i) => {
    if (i >= 0 && i < sheets.length) onSelect(sheets[i].page);
  };

  const pageNodes = nodes.filter((n) => n.page === sheet.page);
  const W = sheet.width || 1;
  const H = sheet.height || 1;

  return (
    <div className="section">
      <h2>Bản vẽ gốc — {sheet.sheet_no || ""}</h2>

      <div className="toolbar">
        <button className="btn ghost" onClick={() => goto(idx - 1)} disabled={idx <= 0}>
          ‹ Trước
        </button>
        <span className="muted">
          Trang {idx + 1} / {sheets.length}
        </span>
        <button
          className="btn ghost"
          onClick={() => goto(idx + 1)}
          disabled={idx >= sheets.length - 1}
        >
          Sau ›
        </button>
        <select
          value={activePage}
          onChange={(e) => onSelect(Number(e.target.value))}
        >
          {sheets.map((s) => (
            <option key={s.page} value={s.page}>
              Trang {s.page} — {s.sheet_no} ({s.sheet_type})
            </option>
          ))}
        </select>
      </div>

      <div className="preview-wrap">
        <img src={pagePreviewUrl(jobId, sheet.page, 0.6)} alt={`page ${sheet.page}`} />
        {pageNodes.map((n) => (
          <span
            key={n.id}
            title={`${n.label} (${n.type})`}
            className="dot"
            style={{
              position: "absolute",
              left: `${(n.x / W) * 100}%`,
              top: `${(n.y / H) * 100}%`,
              width: 8,
              height: 8,
              transform: "translate(-50%, -50%)",
              background: COLORS[n.type] || "#fff",
              boxShadow: "0 0 0 1.5px rgba(0,0,0,.6)",
            }}
          />
        ))}
      </div>

      <div className="legend-dots">
        {Object.entries(COLORS).map(([k, c]) => (
          <span key={k}><i className="dot" style={{ background: c }} /> {k}</span>
        ))}
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        {pageNodes.length} đối tượng được trích xuất & định vị trên trang này.
      </p>
    </div>
  );
}
