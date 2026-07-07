import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  getReview, saveReview, getReviewStatus, confirmAll, exportUrl, pagePreviewUrl,
} from "../api/client";

const EMPTY_ITEM = {
  panelName: "", roadName: "", loadName: "", power: "", cb: "",
  itemGroup: "Dây & cáp điện", itemName: "Dây/cáp Cu/PVC",
  size: "", cableSpec: "", conduit: "",
};

// ---- Cấu hình cột theo TỪNG loại sơ đồ ----
// Mỗi loại chỉ hiện những cột nó thực sự đọc được (tránh cột rỗng, khó đối chiếu).
//
// Cách thêm/bớt cột:
//   1) Khai báo nhãn + độ rộng mặc định của trường trong ALL_FIELDS.
//   2) Thêm key trường đó vào danh sách của loại tương ứng trong TYPE_FIELDS.
//   3) (tuỳ chọn) đặt nhãn riêng cho một loại trong LABEL_OVERRIDES.
//
// panelName KHÔNG nằm ở đây — đã gom theo tủ ở header nhóm.

// Bảng nhãn + độ rộng mặc định của mọi trường có thể hiển thị.
const ALL_FIELDS = {
  panelCode: ["Mã tủ", 130],
  roadName:  ["Lộ", 70],
  loadName:  ["Tên tải", 210],
  power:     ["Công suất (W)", 90],  // sẵn sàng: bật khi backend trả 'power' theo lộ
  cb:        ["MCCB/RCBO", 170],     // sẵn sàng: bật khi backend trả 'cb' theo lộ
  size:      ["Tiết diện", 80],
  cableSpec: ["Quy cách cáp", 280],
  conduit:   ["Ống luồn", 150],
};

// Cột hiển thị theo loại (diagramType do backend trả về).
const TYPE_FIELDS = {
  busbar_slash: ["roadName", "loadName", "size", "cableSpec", "conduit"],
  panel_table:  ["roadName", "loadName", "size", "cableSpec", "conduit"],
  hotel_db:     ["roadName", "loadName", "size", "cableSpec", "conduit"],
  mep_tray:     ["roadName", "loadName", "size", "cableSpec", "conduit"],
};

// Loại chưa cấu hình -> dùng bộ cột mặc định này.
const DEFAULT_FIELDS = ["roadName", "loadName", "size", "cableSpec", "conduit"];

// Nhãn riêng cho loại đặc thù (mep_tray = thang–máng cáp, không phải cáp lộ).
const LABEL_OVERRIDES = {
  mep_tray: {
    roadName:  "Hệ thống",
    loadName:  "Tên hệ thống",
    size:      "Kích thước",
    cableSpec: "Cao độ",
    conduit:   "Tuyến / Ref",
  },
};

// -> [key, label, width] cho loại sơ đồ đang xem.
function fieldsFor(type) {
  const keys = TYPE_FIELDS[type] || DEFAULT_FIELDS;
  const ov = LABEL_OVERRIDES[type] || {};
  return keys.map((k) => {
    const [label, width] = ALL_FIELDS[k];
    return [k, ov[k] || label, width];
  });
}

const NO_PANEL = "(không rõ tủ)";

// Độ phân giải render ảnh bản vẽ: cao -> nét khi phóng to.
const PREVIEW_SCALE = 2.5;
const ZOOM_MIN = 1;      // 100% = vừa khít bề ngang khung
const ZOOM_MAX = 8;
const clampZoom = (z) => Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z));

export default function TakeoffReview({ jobId, sheets, activePage, onSelect }) {
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [statusMap, setStatusMap] = useState({});
  const [onlyConfirmed, setOnlyConfirmed] = useState(true);
  const [zoom, setZoom] = useState(1);

  const idx = sheets.findIndex((s) => s.page === activePage);

  // cột hiển thị theo loại sơ đồ đang xem
  const fields = fieldsFor(review?.diagramType);

  const refreshStatus = useCallback(async () => {
    try {
      const st = await getReviewStatus(jobId);
      const m = {};
      st.forEach((s) => { m[s.page] = s; });
      setStatusMap(m);
    } catch (_) {}
  }, [jobId]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setDirty(false);
    setZoom(1);
    pendingAnchor.current = null;
    if (panRef.current) { panRef.current.scrollLeft = 0; panRef.current.scrollTop = 0; }
    getReview(jobId, activePage)
      .then((d) => alive && setReview(d))
      .catch(() => alive && setReview(null))
      .finally(() => alive && setLoading(false));
    refreshStatus();
    return () => { alive = false; };
  }, [jobId, activePage, refreshStatus]);

  // Làm ấm trang kế (trước/sau): gọi sẵn API + preload ảnh để đổi trang gần như tức thì.
  useEffect(() => {
    if (!sheets?.length || idx < 0) return;
    const t = setTimeout(() => {
      [idx + 1, idx - 1]
        .filter((i) => i >= 0 && i < sheets.length)
        .forEach((i) => {
          const pg = sheets[i].page;
          getReview(jobId, pg).catch(() => {});   // làm ấm cache backend
          new Image().src = pagePreviewUrl(jobId, pg, PREVIEW_SCALE);  // preload ảnh
        });
    }, 400);  // chờ trang hiện tại tải xong trước
    return () => clearTimeout(t);
  }, [jobId, idx, sheets]);

  // map tên tủ -> thông tin (công suất) để hiện ở header nhóm
  const panelMap = useMemo(
    () => Object.fromEntries((review?.panels || []).map((p) => [p.name, p])),
    [review]
  );

  // gom item theo tủ (giữ thứ tự xuất hiện), kèm chỉ số gốc để sửa
  const groups = useMemo(() => {
    if (!review) return [];
    const m = new Map();
    review.items.forEach((it, i) => {
      const key = it.panelName?.trim() || NO_PANEL;
      if (!m.has(key)) m.set(key, []);
      m.get(key).push(i);
    });
    return [...m.entries()];
  }, [review]);

  const setItems = (items) => { setReview((r) => ({ ...r, items })); setDirty(true); };
  const updateCell = (i, field, value) =>
    setItems(review.items.map((it, j) => (j === i ? { ...it, [field]: value } : it)));
  const delRow = (i) => setItems(review.items.filter((_, j) => j !== i));
  const addRowTo = (panel) =>
    setItems([...review.items, { ...EMPTY_ITEM, panelName: panel === NO_PANEL ? "" : panel }]);
  const renamePanel = (oldName, newName) =>
    setItems(review.items.map((it) =>
      (it.panelName?.trim() || NO_PANEL) === oldName ? { ...it, panelName: newName } : it));

  const save = async (confirmed) => {
    setSaving(true);
    try {
      await saveReview(jobId, activePage, {
        diagramType: review.diagramType, panelName: review.panelName,
        panels: review.panels || [],
        items: review.items,
        confirmed: confirmed ?? statusMap[activePage]?.confirmed ?? false,
      });
      setDirty(false);
      await refreshStatus();
      if (confirmed) setReview((r) => ({ ...r, confirmed: true }));
    } finally { setSaving(false); }
  };

  const confirmAndNext = async () => {
    await save(true);
    if (idx < sheets.length - 1) onSelect(sheets[idx + 1].page);
  };
  const goto = (i) => { if (i >= 0 && i < sheets.length) onSelect(sheets[i].page); };
  const confirmedCount = Object.values(statusMap).filter((s) => s.confirmed).length;

  const [confirmingAll, setConfirmingAll] = useState(false);
  const doConfirmAll = async () => {
    if (!window.confirm("Xác nhận TẤT CẢ trang có sơ đồ bóc tách được? (giữ nguyên các chỉnh sửa đã lưu)")) return;
    setConfirmingAll(true);
    try {
      const r = await confirmAll(jobId);
      await refreshStatus();
      const cur = await getReview(jobId, activePage);
      setReview(cur);
      setDirty(false);
      alert(`Đã xác nhận ${r.confirmed_pages} trang.`);
    } catch (e) {
      alert("Lỗi: " + e.message);
    } finally {
      setConfirmingAll(false);
    }
  };

  const triggerDownload = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const download = async (fmt) => {
    try {
      const res = await fetch(exportUrl(jobId, fmt, onlyConfirmed));
      if (!res.ok) throw new Error("HTTP " + res.status);
      if (fmt === "json") {
        const text = await res.text();
        let arr = [];
        try { arr = JSON.parse(text); } catch (_) {}
        if (!arr.length) {
          alert(onlyConfirmed
            ? "Chưa có trang nào được xác nhận để xuất. Hãy bấm 'Xác nhận' từng trang, hoặc bỏ chọn 'Chỉ xuất trang đã xác nhận'."
            : "Chưa có dữ liệu đã lưu để xuất. Hãy 'Lưu nháp' hoặc 'Xác nhận' trang trước.");
          return;
        }
        triggerDownload(new Blob([text], { type: "application/json" }), `BOQ_${jobId}.json`);
      } else {
        const blob = await res.blob();
        triggerDownload(blob, `BOQ_${jobId}.xlsx`);
      }
    } catch (e) {
      alert("Xuất thất bại: " + e.message);
    }
  };

  // --- Zoom neo theo 1 điểm: điểm đó đứng yên trên màn hình khi phóng/thu ---
  const panRef = useRef(null);
  const pendingAnchor = useRef(null);
  // Giữ zoom hiện tại trong ref để handler wheel (deps []) không bị đọc giá trị cũ.
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;

  // Sau khi ảnh đổi kích thước (zoom thay đổi), chỉnh scroll để giữ điểm neo cố định.
  useLayoutEffect(() => {
    const el = panRef.current;
    const a = pendingAnchor.current;
    if (!el || !a) return;
    const k = zoom / a.z0;
    el.scrollLeft = a.cx * k - a.vx;
    el.scrollTop = a.cy * k - a.vy;
    pendingAnchor.current = null;
  }, [zoom]);

  // Zoom về giá trị mới, neo tại toạ độ màn hình (clientX/Y). Mặc định: tâm khung.
  const zoomTo = (target, clientX, clientY) => {
    const el = panRef.current;
    if (!el) return;
    const cur = zoomRef.current;
    const nz = clampZoom(target);
    if (nz === cur) return;
    const rect = el.getBoundingClientRect();
    const vx = (clientX ?? rect.left + rect.width / 2) - rect.left;
    const vy = (clientY ?? rect.top + rect.height / 2) - rect.top;
    // toạ độ điểm neo trong nội dung (ở mức zoom hiện tại)
    pendingAnchor.current = { cx: el.scrollLeft + vx, cy: el.scrollTop + vy, vx, vy, z0: cur };
    setZoom(nz);
  };

  // Wheel của React là passive -> phải gắn native listener mới preventDefault được.
  useEffect(() => {
    const el = panRef.current;
    if (!el) return;
    const handler = (e) => {
      e.preventDefault();                     // lăn chuột = zoom, không cần giữ Ctrl
      const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
      zoomTo(zoomRef.current * factor, e.clientX, e.clientY);
    };
    el.addEventListener("wheel", handler, { passive: false });
    return () => el.removeEventListener("wheel", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resetZoom = () => {
    const el = panRef.current;
    setZoom(1);
    if (el) { el.scrollLeft = 0; el.scrollTop = 0; }
    pendingAnchor.current = null;
  };

  // kéo-thả để di chuyển ảnh khi đã zoom
  const drag = useRef(null);
  const onDown = (e) => {
    const el = panRef.current;
    drag.current = { x: e.clientX, y: e.clientY, sl: el.scrollLeft, st: el.scrollTop };
    el.style.cursor = "grabbing";
  };
  const onMove = (e) => {
    if (!drag.current) return;
    const el = panRef.current;
    el.scrollLeft = drag.current.sl - (e.clientX - drag.current.x);
    el.scrollTop = drag.current.st - (e.clientY - drag.current.y);
  };
  const endDrag = () => {
    drag.current = null;
    if (panRef.current) panRef.current.style.cursor = "grab";
  };

  return (
    <div className="section full-bleed">
      <h2>Duyệt & Xuất BOQ</h2>

      <div className="toolbar">
        <button className="btn ghost" onClick={() => goto(idx - 1)} disabled={idx <= 0}>‹ Trước</button>
        <span className="muted">Trang {idx + 1} / {sheets.length}</span>
        <button className="btn ghost" onClick={() => goto(idx + 1)} disabled={idx >= sheets.length - 1}>Sau ›</button>
        {statusMap[activePage]?.confirmed
          ? <span className="badge supplies">✓ Đã xác nhận</span>
          : <span className="badge breaker">Chưa xác nhận</span>}
        {dirty && <span className="badge breaker">● Chưa lưu</span>}
        <span style={{ flex: 1 }} />
        <span className="muted">{confirmedCount}/{sheets.length} trang đã xác nhận</span>
        <button className="btn ghost" onClick={doConfirmAll} disabled={confirmingAll}>
          {confirmingAll ? "Đang xác nhận…" : "✓ Xác nhận tất cả"}
        </button>
      </div>

      <div className="split">
        {/* trái: bản vẽ zoom được */}
        <div className="split-left-wrap">
          <div className="zoom-bar">
            <button className="btn ghost" onClick={() => zoomTo(zoom / 1.25)}>−</button>
            <span className="muted" style={{ minWidth: 46, textAlign: "center" }}>{Math.round(zoom * 100)}%</span>
            <button className="btn ghost" onClick={() => zoomTo(zoom * 1.25)}>+</button>
            <button className="btn ghost" onClick={resetZoom}>Reset</button>
            <span className="muted" style={{ fontSize: 11 }}>(lăn chuột để zoom, kéo để di chuyển)</span>
          </div>
          <div
            className="split-left"
            ref={panRef}
            onMouseDown={onDown}
            onMouseMove={onMove}
            onMouseUp={endDrag}
            onMouseLeave={endDrag}
          >
            <img
              src={pagePreviewUrl(jobId, activePage, PREVIEW_SCALE)}
              alt={`page ${activePage}`}
              draggable={false}
              style={{ width: `${zoom * 100}%` }}
            />
          </div>
        </div>

        {/* phải: bảng gom theo tủ */}
        <div className="split-right">
          {loading && <p className="muted">Đang tải…</p>}
          {review && (
            <>
              <div className="muted" style={{ marginBottom: 8 }}>
                {review.diagramType || "—"} · {review.items.length} lộ · {groups.length} tủ
                {review.source === "extracted" && " · (bóc tự động, chưa lưu)"}
              </div>
              {review.panels?.some((p) => p.kind !== "sub") && (
                <div className="panel-info">
                  {review.panels.filter((p) => p.kind !== "sub").map((p) => (
                    <span className="panel-chip" key={p.name}>
                      <b>{p.name}</b>
                      {p.power && <> · P {Number(p.power).toLocaleString()}W</>}
                      {p.ptt && <> · Ptt {Number(p.ptt).toLocaleString()}W</>}
                      {p.kdt && <> · Kđt {p.kdt}</>}
                    </span>
                  ))}
                </div>
              )}
              <div className="edit-table-wrap">
                <table className="edit-table">
                  <thead>
                    <tr>
                      {fields.map(([k, label]) => <th key={k}>{label}</th>)}
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {groups.map(([panel, idxs]) => (
                      <PanelGroup
                        key={panel}
                        panel={panel}
                        info={panelMap[panel]}
                        idxs={idxs}
                        items={review.items}
                        fields={fields}
                        onCell={updateCell}
                        onDel={delRow}
                        onAdd={() => addRowTo(panel)}
                        onRename={(name) => renamePanel(panel, name)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="toolbar" style={{ marginTop: 10 }}>
                <button className="btn ghost" onClick={() => addRowTo("")}>+ Thêm dòng (tủ mới)</button>
                <button className="btn ghost" onClick={() => save(false)} disabled={saving}>
                  {saving ? "Đang lưu…" : "Lưu nháp"}
                </button>
                <button className="btn" onClick={confirmAndNext} disabled={saving}>
                  Xác nhận & trang sau ›
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="export-bar">
        <label className="muted" style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input type="checkbox" checked={onlyConfirmed} onChange={(e) => setOnlyConfirmed(e.target.checked)} />
          Chỉ xuất trang đã xác nhận
        </label>
        <span style={{ flex: 1 }} />
        <button className="btn ghost" onClick={() => download("json")}>⬇ Xuất JSON</button>
        <button className="btn" onClick={() => download("xlsx")}>⬇ Xuất Excel (BOQ)</button>
      </div>
    </div>
  );
}

function PanelGroup({ panel, info, idxs, items, fields, onCell, onDel, onAdd, onRename }) {
  const colCount = fields.length + 1;
  // state cục bộ để gõ mượt; chỉ áp dụng đổi tên khi blur (tránh remount mất focus)
  const [name, setName] = useState(panel);
  useEffect(() => { setName(panel); }, [panel]);
  const commit = () => { if (name.trim() && name !== panel) onRename(name.trim()); };
  return (
    <>
      <tr className="group-head">
        <td colSpan={colCount}>
          <span className="group-icon">🗄</span>
          <input
            className="group-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onBlur={commit}
            onKeyDown={(e) => e.key === "Enter" && e.target.blur()}
            title="Đổi tên tủ (áp dụng cả nhóm) — Enter để lưu"
          />
          <span className="muted">· {idxs.length} lộ</span>
          {info?.power && <span className="badge supplies">P {Number(info.power).toLocaleString()}W</span>}
          {info?.ptt && <span className="muted">· Ptt {Number(info.ptt).toLocaleString()}W</span>}
          {info?.kdt && <span className="muted">· Kđt {info.kdt}</span>}
          <button className="btn ghost group-add" onClick={onAdd}>+ dòng</button>
        </td>
      </tr>
      {idxs.map((i) => (
        <tr key={i}>
          {fields.map(([k, , w]) => (
            <td key={k}>
              <input style={{ width: w }} value={items[i][k] || ""} onChange={(e) => onCell(i, k, e.target.value)} />
            </td>
          ))}
          <td><button className="row-del" onClick={() => onDel(i)} title="Xoá dòng">✕</button></td>
        </tr>
      ))}
    </>
  );
}
