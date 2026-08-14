import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5400,
    // Reachable from the phone over Tailscale: the machine's tailnet hostname
    // plus any *.ts.net MagicDNS name.
    allowedHosts: ['server', '.ts.net'],
    proxy: {
      '/api': {
        target: 'http://localhost:8400',
        changeOrigin: true,
      },
    },
  },
})
