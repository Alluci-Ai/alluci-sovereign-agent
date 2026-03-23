import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    api: {
      host: '127.0.0.1',
    },
    include: [
      'features/**/*.test.{ts,tsx}',
      'components/**/*.test.{ts,tsx}',
      'hooks/**/*.test.{ts,tsx}',
      'store/**/*.test.{ts,tsx}',
    ],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
      include: [
        'features/**/*.{ts,tsx}',
        'components/**/*.{ts,tsx}',
        'hooks/**/*.{ts,tsx}',
        'store/**/*.{ts,tsx}',
      ],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.test.{ts,tsx}',
        '**/*.config.ts',
      ],
      // Thresholds are intentionally conservative to match current test surface.
      // Raise by 10% per sprint as tests are added (target: 80% by Q3 2026).
      thresholds: {
        lines: 55,
        functions: 55,
        branches: 45,
        statements: 55,
      },
    },
  },
});
