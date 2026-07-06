import { useRef, useState } from "react";

export default function FileDropzone({ onFile, busy, progress }) {
  const [drag, setDrag] = useState(false);
  const inputRef = useRef(null);

  const pick = (files) => {
    const f = files?.[0];
    if (f && f.name.toLowerCase().endsWith(".pdf")) onFile(f);
  };

  return (
    <div
      className={`dropzone ${drag ? "drag" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files); }}
    >
      <div className="icon">📐</div>
      <h3>{busy ? "Đang phân tích bản vẽ…" : "Kéo & thả file PDF vào đây"}</h3>
      <div className="hint">hoặc bấm để chọn file • chỉ nhận .pdf</div>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        style={{ display: "none" }}
        onChange={(e) => pick(e.target.files)}
      />
      {busy && (
        <div className="progress">
          <div style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  );
}
