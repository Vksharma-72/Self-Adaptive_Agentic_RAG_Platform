import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // Dev proxy → FastAPI backend; in production FastAPI serves the built SPA
      '/auth': 'http://localhost:8000',
      '/workspaces': 'http://localhost:8000',
      '/users': 'http://localhost:8000',
    },
  },
})
