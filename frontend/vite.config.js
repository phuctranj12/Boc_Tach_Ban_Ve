import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Cấu hình cổng qua biến môi trường để chạy NHIỀU DỰ ÁN cùng lúc mà không trùng:
//   FRONTEND_PORT : cổng dev server của giao diện (mặc định 5173)
//   BACKEND_PORT  : cổng backend FastAPI mà /api sẽ proxy tới (mặc định 8000)
// Ví dụ: FRONTEND_PORT=5174 BACKEND_PORT=8001 npm run dev
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const frontendPort = Number(env.FRONTEND_PORT || process.env.FRONTEND_PORT || 5173);
  const backendPort = Number(env.BACKEND_PORT || process.env.BACKEND_PORT || 8001);

  return {
    plugins: [react()],
    server: {
      host: true,          // lắng nghe mọi địa chỉ -> máy khác trong LAN truy cập được
      port: frontendPort,
      strictPort: true,    // báo lỗi ngay nếu cổng bận, thay vì âm thầm nhảy cổng khác
      proxy: {
        // proxy chạy trên máy host nên trỏ localhost tới đúng cổng backend của dự án này
        "/api": `http://localhost:${backendPort}`,
      },
    },
  };
});
