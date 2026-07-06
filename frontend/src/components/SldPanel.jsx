import { useEffect, useState } from "react";
import { extractSld } from "../api/client";

// Bóc tách cáp & ống luồn từ Sơ đồ nguyên lý (SLD) của trang đang chọn.
export default function SldPanel({ jobId, page }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    setData(null);
    extractSld(jobId, page)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [jobId, page]);

  const json = data ? JSON.stringify(data.items, null, 2) : "";

  const copy = () => {
    navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const download = () => {
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sld_trang_${page}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const TYPE_LABEL = {
    busbar_slash: "Kiểu A — Busbar + vạch chéo",
    panel_table: "Kiểu B — Bảng/ma trận tủ điện",
    unknown: "Chưa nhận diện được loại sơ đồ",
  };

  return (
    <div className="section">
      <h2>Bóc tách Sơ đồ nguyên lý — Cáp & Ống luồn</h2>

      {loading && <p className="muted">Đang bóc tách…</p>}
      {error && <div className="error">⚠️ {error}</div>}

      {data && data.items.length === 0 && (
        <p className="muted">
          Trang này không có sơ đồ nguyên lý bóc tách được
          {data.diagramType ? ` (${TYPE_LABEL[data.diagramType] || data.diagramType})` : ""}.
        </p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="toolbar">
            <span className="badge equipment">{TYPE_LABEL[data.diagramType] || data.diagramType}</span>
            {data.panelName && <span className="badge distribution_board">{data.panelName}</span>}
            <span className="muted">{data.items.length} lộ/tải</span>
            <span style={{ flex: 1 }} />
            <button className="btn ghost" onClick={copy}>
              {copied ? "✓ Đã copy" : "Copy JSON"}
            </button>
            <button className="btn ghost" onClick={download}>Tải .json</button>
          </div>

          <div style={{ maxHeight: 420, overflow: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>Tủ</th>
                  <th>Lộ</th>
                  <th>Tải</th>
                  <th>Tiết diện</th>
                  <th>Ống luồn</th>
                  <th>Cáp đầy đủ</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it, i) => (
                  <tr key={i}>
                    <td className="muted">{it.panelName}</td>
                    <td><strong>{it.roadName}</strong></td>
                    <td>{it.loadName}</td>
                    <td>{it.size || <span className="muted">—</span>}</td>
                    <td className="muted">{it.conduit}</td>
                    <td className="muted" style={{ fontSize: 12 }}>{it.cableSpec}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
