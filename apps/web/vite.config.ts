/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// The API is always same-origin (`/api`); in development Vite proxies it to VITE_DEV_API_TARGET.
const apiTarget = process.env['VITE_DEV_API_TARGET'];

export default defineConfig({
  plugins: [react()],
  server: apiTarget ? { proxy: { '/api': { target: apiTarget, changeOrigin: true } } } : {},
  build: { sourcemap: true, target: 'es2022' },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.d.ts', 'src/test/**', 'src/main.tsx', 'src/**/*.test.{ts,tsx}'],
      reporter: ['text-summary', 'lcov'],
      thresholds: { lines: 80, statements: 80, functions: 80, branches: 70 },
    },
  },
});
