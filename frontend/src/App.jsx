import { useState } from "react";
import { analyzePdf } from "./api/client";
import FileDropzone from "./components/FileDropzone";
import StatsCards from "./components/StatsCards";
import SheetList from "./components/SheetList";
import RelationshipPanel from "./components/RelationshipPanel";
import TypeBreakdown from "./components/TypeBreakdown";
import QaBox from "./components/QaBox";
import PagePreview from "./components/PagePreview";
import TakeoffReview from "./components/TakeoffReview";

export default function App() {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activePage, setActivePage] = useState(0);

  const handleFile = async (file) => {
    setBusy(true);
    setError("");
    setResult(null);
    setProgress(0);
    try {
      const res = await analyzePdf(file, setProgress);
      setResult(res);
      setActivePage(res.sheets?.[0]?.page ?? 0);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app">
      <div className="header">
        <h1>🔌 MEP Drawing Reader</h1>
        <p>Đọc bản vẽ MEP bằng Vector + Layer CAD + Graph + Rule Engine</p>
      </div>

      <FileDropzone onFile={handleFile} busy={busy} progress={progress} />
      {error && <div className="error">⚠️ {error}</div>}

      {result && (
        <>
          {/* Trọng tâm: Duyệt & Xuất BOQ lên trên cùng */}
          <TakeoffReview
            jobId={result.job_id}
            sheets={result.sheets}
            activePage={activePage}
            onSelect={setActivePage}
          />

          {/* Các phân tích phụ trợ ở dưới */}
          <StatsCards stats={result.stats} />

          <div className="grid-2">
            <TypeBreakdown byType={result.stats.by_type} />
            <QaBox jobId={result.job_id} />
          </div>

          <SheetList
            sheets={result.sheets}
            activePage={activePage}
            onSelect={setActivePage}
          />

          <div className="grid-2">
            <PagePreview
              jobId={result.job_id}
              sheets={result.sheets}
              activePage={activePage}
              onSelect={setActivePage}
              nodes={result.nodes}
            />
            <RelationshipPanel relationships={result.relationships} />
          </div>
        </>
      )}

      {!result && !busy && (
        <p className="muted" style={{ marginTop: 24 }}>
          Tải lên file PDF bản vẽ MEP để trích xuất đối tượng, dựng topology và suy luận quan hệ.
        </p>
      )}
    </div>
  );
}
