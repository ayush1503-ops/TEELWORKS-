import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",      // required for the sandbox live preview
    port: 5173,
    strictPort: true,
    allowedHosts: ["localhost", ".e2b.app"],   // sandbox preview proxies on *.e2b.app
  },
});
