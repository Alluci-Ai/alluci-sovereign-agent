// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    coverage: {
      provider:   'v8',
      reporter:   ['text', 'html', 'lcov'],
      reportsDirectory: './coverage',
      thresholds: {
        lines:      75,
        functions:  75,
        branches:   70,
        statements: 75,
      },
      include: [
        'features/**/*.{ts,tsx}',
        'components/**/*.{ts,tsx}',
        'hooks/**/*.{ts,tsx}',
        'store/**/*.{ts,tsx}',
      ],
      exclude: [
        '**/*.test.{ts,tsx}',
        '**/*.spec.{ts,tsx}',
        '**/node_modules/**',
        '**/third-party/**',
      ],
    },
  },
});
