// vite.config.ts — RE-APPLIED FIX

import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import { readFileSync } from 'node:fs';

const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'));

// Fix for __dirname not available in ESM environment
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: false,
        },
        '/health': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'http://127.0.0.1:8000',
          ws: true,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('error', (err) => console.log('proxy error', err));
            proxy.on('proxyReq', () => console.log('proxyReq'));
            proxy.on('proxyReqWs', () => console.log('proxyReqWs', new Date().toISOString()));
            proxy.on('proxyRes', () => console.log('proxyRes'));
          }
        }
      },
    },
    plugins: [
      react(),
      VitePWA({
        selfDestroying: true,
        registerType: 'autoUpdate',
        manifest: {
          name: 'Alluci Sovereign Agent',
          short_name: 'Alluci',
          description: 'Sovereign AI Executive Assistant',
          theme_color: '#0B7A8A',
          background_color: '#0A1628',
          display: 'standalone',
          start_url: '/',
          icons: [
            {
              src: '/icon-192.png',
              sizes: '192x192',
              type: 'image/png'
            },
            {
              src: '/icon-512.png',
              sizes: '512x512',
              type: 'image/png'
            }
          ]
        },
        workbox: {
          globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
          runtimeCaching: [{
            urlPattern: /^\/api\//,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              networkTimeoutSeconds: 10,
            }
          }]
        }
      })
    ],
    define: {
      // In dev and same-origin prod, empty string enables relative path proxying.
      // If a separate CDN/Load Balancer is used, override via environment.
      'import.meta.env.VITE_DAEMON_URL': JSON.stringify(env.VITE_DAEMON_URL || ''),
      __APP_VERSION__: JSON.stringify(pkg.version),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    }
  };
});
