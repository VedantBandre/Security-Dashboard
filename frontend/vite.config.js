import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiProxy = {
  '/login-attempt': 'http://localhost:8000',
  '/events': 'http://localhost:8000',
  '/suspicious': 'http://localhost:8000',
  '/stats': 'http://localhost:8000',
}

export default defineConfig({
  plugins: [react()],
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
})
