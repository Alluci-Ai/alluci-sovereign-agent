import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
 plugins: [react()],
 test: {
   environment: 'jsdom',
   globals: true,
   setupFiles: ['./tests/setup.ts'],
   api: { host: '127.0.0.1' },
   include: [
     'features/**/*.test.{ts,tsx}',
     'components/**/*.test.{ts,tsx}',
     'hooks/**/*.test.{ts,tsx}',
     'store/**/*.test.{ts,tsx}',
   ],
   exclude: [
     '**/node_modules/**',
     '**/dist/**',
     '**/e2e/**',
     '**/third-party/**',
   ],
   coverage: {
     provider: 'v8',
     reporter: ['text', 'json', 'html', 'lcov'],
     reportsDirectory: './coverage',
     include: [
       'features/**/*.{ts,tsx}',
       'components/**/*.{ts,tsx}',
       'hooks/**/*.{ts,tsx}',
       'store/**/*.{ts,tsx}',
     ],
     exclude: [
       '**/node_modules/**',
       '**/*.d.ts',
       '**/*.test.{ts,tsx}',
       '**/*.config.ts',
       '**/e2e/**',
       '**/third-party/**',
     ],
     thresholds: {
       lines: 60,
       functions: 60,
       branches: 50,
       statements: 60,
     },
   },
 },
});
