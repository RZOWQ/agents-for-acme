import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

try {
  const app = express();
  app.use(
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      pathFilter: (path, req) => path.startsWith('/apps') || path.startsWith('/run_sse'),
      on: {
        proxyReq: (proxyReq, req, res) => {
          proxyReq.setHeader('authorization', 'Bearer test');
        }
      }
    })
  );
  console.log('Successfully initialized http-proxy-middleware with on.proxyReq!');
  process.exit(0);
} catch (err) {
  console.error('Failed to initialize:', err);
  process.exit(1);
}
