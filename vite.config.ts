
import path from 'path';
import { fileURLToPath } from 'url';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// Fix for __dirname not available in ESM environment
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');
  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
      https: env.VITE_USE_SSL === 'true' ? {
        key: path.resolve(__dirname, 'certs/privkey.pem'),
        cert: path.resolve(__dirname, 'certs/fullchain.pem'),
      } : false,
    },
    plugins: [
      react(),
      VitePWA({
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
      // Only expose the daemon URL — API keys stay server-side
      'import.meta.env.VITE_DAEMON_URL': JSON.stringify(env.VITE_DAEMON_URL || 'http://localhost:8000'),
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    }
  };
});
