import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Matches backend CORS_ORIGINS and FRONTEND_SSO_REDIRECT_URL in .env
    port: 5180,
    strictPort: true,
  },
})
