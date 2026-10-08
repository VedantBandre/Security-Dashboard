# Security Dashboard frontend

React + Vite frontend for the Django API. See the [project README](../README.md)
for backend setup, sample events, and the API reference.

Use Node.js 24.15+ (24.x), or 22.22.2+ (22.x) and npm:

```bash
npm ci
npm run dev
```

Vite normally serves the dashboard at `http://localhost:5173` and proxies API
requests to `http://localhost:8000`. Both servers must be running.

Set `VITE_API_BASE` in `.env.local` to use a different backend. Restart the dev
server after changing it; production builds embed the value at build time.

```bash
npm run lint
npm test
npm run build
npm run preview
```

Build output is in `dist`. Preview uses the same local API proxy as development.
A hosted build needs its own API reverse proxy or a configured `VITE_API_BASE`.
