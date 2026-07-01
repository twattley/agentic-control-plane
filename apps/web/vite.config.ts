import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5400,
    proxy: {
      '/api': {
        target: 'http://localhost:8400',
        changeOrigin: true,
      },
    },
  },
})
