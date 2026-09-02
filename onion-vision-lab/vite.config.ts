import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Frontend on 5174; vision API on 8788. The browser never calls localhost
// directly - it uses the relative /vision-api prefix, which Vite proxies.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5174,
    strictPort: true,
    allowedHosts: ['localhost', '.e2b.app'],
    proxy: {
      '/vision-api': {
        target: 'http://localhost:8788',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/vision-api/, ''),
      },
    },
  },
  preview: {
    host: true,
    port: 5174,
    strictPort: true,
    allowedHosts: ['localhost', '.e2b.app'],
    proxy: {
      '/vision-api': {
        target: 'http://localhost:8788',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/vision-api/, ''),
      },
    },
  },
});
