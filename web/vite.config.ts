import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // El proyecto vive en /mnt/c (WSL): inotify no detecta cambios ahí de forma
    // confiable, así que HMR se queda pegado sin polling.
    watch: { usePolling: true },
  },
})
