import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Preserve the browser Host so Django can validate same-origin CSRF requests.
const apiProxy = Object.fromEntries([
  '/login-attempt', '/events', '/suspicious', '/auth', '/users',
  '/findings', '/investigations', '/stats',
].map(path => [path, { target: 'http://127.0.0.1:8000', changeOrigin: false }]))

export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
})
