import { defineConfig } from 'vite'
export default defineConfig({ base: process.env.VITE_BASE_PATH || '/shiva.github.io/portal/', build: { outDir: 'dist' } })
