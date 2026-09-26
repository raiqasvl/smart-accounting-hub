// Next.js 15 config.
//
// The rewrite makes the API same-origin with the Mini-App in local dev (Caddy does it in
// production): the browser calls /api/v1/* on the Next origin and Next proxies to FastAPI. This
// keeps a single tunnel and avoids CORS entirely — the API has no CORS middleware.
//
// API_PROXY_TARGET is read when `next build` runs, not per request: rewrites are compiled into
// .next/routes-manifest.json. The container build sets it to the API's alias on the shared edge
// network, because 127.0.0.1 inside the Mini-App container is the Mini-App itself. In production
// Caddy routes /api/v1/* before a request reaches Next, so this is only the fallback.
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
