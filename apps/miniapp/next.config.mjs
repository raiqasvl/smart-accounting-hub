// Next.js 15 config.
//
// The rewrite makes the API same-origin with the Mini-App (replaces Caddy locally): the browser
// calls /api/v1/* on the Next origin, and Next proxies to the FastAPI dev server. This keeps a
// single tunnel and avoids CORS entirely.

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "http://127.0.0.1:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
