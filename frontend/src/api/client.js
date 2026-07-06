// Lớp gọi API tới backend FastAPI.
const BASE = "/api";

export async function analyzePdf(file, onProgress) {
  const form = new FormData();
  form.append("file", file);
  // dùng XHR để có progress upload
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}/analyze`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        let msg = "Lỗi phân tích";
        try {
          msg = JSON.parse(xhr.responseText).detail || msg;
        } catch (_) {}
        reject(new Error(msg));
      }
    };
    xhr.onerror = () => reject(new Error("Không kết nối được backend"));
    xhr.send(form);
  });
}

export async function askQuestion(jobId, q) {
  const res = await fetch(`${BASE}/results/${jobId}/qa?q=${encodeURIComponent(q)}`);
  if (!res.ok) throw new Error("Lỗi QA");
  return res.json();
}

export function pagePreviewUrl(jobId, page, scale = 0.5) {
  return `${BASE}/results/${jobId}/page/${page}/preview?scale=${scale}`;
}

export async function extractSld(jobId, page) {
  const res = await fetch(`${BASE}/results/${jobId}/sld?page=${page}`);
  if (!res.ok) throw new Error("Lỗi bóc tách sơ đồ nguyên lý");
  return res.json();
}

// --- Human-in-the-loop review ---
export async function getReview(jobId, page) {
  const res = await fetch(`${BASE}/results/${jobId}/review/${page}`);
  if (!res.ok) throw new Error("Lỗi tải dữ liệu duyệt");
  return res.json();
}

export async function saveReview(jobId, page, payload) {
  const res = await fetch(`${BASE}/results/${jobId}/review/${page}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Lỗi lưu dữ liệu");
  return res.json();
}

export async function getReviewStatus(jobId) {
  const res = await fetch(`${BASE}/results/${jobId}/review`);
  if (!res.ok) throw new Error("Lỗi tải trạng thái duyệt");
  return res.json();
}

export async function confirmAll(jobId) {
  const res = await fetch(`${BASE}/results/${jobId}/review/confirm-all`, { method: "POST" });
  if (!res.ok) throw new Error("Lỗi xác nhận tất cả");
  return res.json();
}

export function exportUrl(jobId, fmt, confirmed = false) {
  return `${BASE}/results/${jobId}/export.${fmt}?confirmed=${confirmed}`;
}
