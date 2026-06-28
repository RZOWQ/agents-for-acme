import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { GoogleAuth } from 'google-auth-library';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 8080;
const targetUrl = process.env.BACKEND_URL || 'http://localhost:8000';
const customerTargetUrl = process.env.CUSTOMER_BACKEND_URL || 'http://localhost:8001';

const auth = new GoogleAuth();
let client;
let customerClient;

// Initialize Google Auth clients
async function getClient() {
  if (!client) {
    client = await auth.getIdTokenClient(targetUrl);
  }
  return client;
}

async function getCustomerClient() {
  if (!customerClient) {
    customerClient = await auth.getIdTokenClient(customerTargetUrl);
  }
  return customerClient;
}

// Request logger middleware
app.use((req, res, next) => {
  console.error(`[Incoming Request] ${req.method} ${req.originalUrl}`);
  next();
});

// Middleware to dynamically fetch and inject the Google OIDC ID token
app.use(async (req, res, next) => {
  const isCustomer = req.originalUrl.startsWith('/customer-apps') || req.originalUrl.startsWith('/customer-run_sse');
  const isMarketing = req.originalUrl.startsWith('/apps') || req.originalUrl.startsWith('/run_sse');

  if (isCustomer || isMarketing) {
    try {
      const activeTargetUrl = isCustomer ? customerTargetUrl : targetUrl;
      console.error(`[Proxy Auth] Fetching token for target: ${activeTargetUrl}`);
      const idTokenClient = isCustomer ? await getCustomerClient() : await getClient();
      const headers = await idTokenClient.getRequestHeaders(activeTargetUrl);
      // Extract Authorization header
      const authHeader = typeof headers.get === 'function' 
        ? headers.get('authorization') 
        : (headers['Authorization'] || headers['authorization']);
        
      if (authHeader) {
        delete req.headers['authorization'];
        delete req.headers['Authorization'];
        req.headers['authorization'] = authHeader;
        console.error('[Proxy Auth] Token injected successfully.');
      } else {
        console.error('[Proxy Auth] No authorization header returned from client.');
      }
    } catch (err) {
      console.error('[Proxy Auth] Error fetching Google OIDC token:', err);
    }
  }
  next();
});

// Proxy Marketing Agent requests to backend (using pathFilter to preserve full req.url path prefix)
app.use(
  createProxyMiddleware({
    target: targetUrl,
    changeOrigin: true,
    buffer: null,
    pathFilter: (path, req) => path.startsWith('/apps') || path.startsWith('/run_sse'),
    on: {
      proxyReq: (proxyReq, req, res) => {
        proxyReq.removeHeader('Authorization');
        proxyReq.removeHeader('authorization');
        proxyReq.removeHeader('X-Serverless-Authorization');
        proxyReq.removeHeader('x-serverless-authorization');
        proxyReq.removeHeader('Origin');
        proxyReq.removeHeader('origin');
        if (req.headers['authorization']) {
          proxyReq.setHeader('authorization', req.headers['authorization']);
        }
        console.error('[Marketing Proxy Request Headers]:', JSON.stringify(proxyReq.getHeaders()));
      }
    }
  })
);

// Proxy Customer Agent requests to backend
app.use(
  createProxyMiddleware({
    target: customerTargetUrl,
    changeOrigin: true,
    buffer: null,
    pathFilter: (path, req) => path.startsWith('/customer-apps') || path.startsWith('/customer-run_sse'),
    pathRewrite: {
      '^/customer-apps': '/apps',
      '^/customer-run_sse': '/run_sse',
    },
    on: {
      proxyReq: (proxyReq, req, res) => {
        proxyReq.removeHeader('Authorization');
        proxyReq.removeHeader('authorization');
        proxyReq.removeHeader('X-Serverless-Authorization');
        proxyReq.removeHeader('x-serverless-authorization');
        proxyReq.removeHeader('Origin');
        proxyReq.removeHeader('origin');
        if (req.headers['authorization']) {
          proxyReq.setHeader('authorization', req.headers['authorization']);
        }
        console.error('[Customer Proxy Request Headers]:', JSON.stringify(proxyReq.getHeaders()));
      }
    }
  })
);

// Serve static React production files
app.use(express.static(path.join(__dirname, 'dist')));

// Fallback for React Router client-side routing
app.get('/*splat', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

app.listen(port, () => {
  console.log(`Frontend server listening on port ${port}, proxying to ${targetUrl} and ${customerTargetUrl}`);
});
