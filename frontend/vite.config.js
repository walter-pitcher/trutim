import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: false, // Preserve Host so backend builds correct media URLs (e.g. for avatars)
      },
      '/media': {
        target: 'http://localhost:8002',
        changeOrigin: false,
      },
      '/ws': { target: 'ws://localhost:8002', ws: true },
    },
  },
})
