import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  if (command === 'build') {
    const api = env.VITE_API_URL?.trim() || '/api'
    if (api !== '/api' && !/^https?:\/\/[^\s]+$/.test(api)) {
      throw new Error('VITE_API_URL must be /api or an HTTP(S) backend URL.')
    }
    if (process.env.VERCEL && api !== '/api' && !api.startsWith('https://')) {
      throw new Error('Vercel requires /api or an HTTPS VITE_API_URL.')
    }
  }
  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      strictPort: true,
    },
  }
})
