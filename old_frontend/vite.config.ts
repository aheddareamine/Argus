import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      '/graph':     'http://localhost:8000',
      '/incidents': 'http://localhost:8000',
      '/demo':      'http://localhost:8000',
      '/sync':      'http://localhost:8000',
      '/health':    'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
});
