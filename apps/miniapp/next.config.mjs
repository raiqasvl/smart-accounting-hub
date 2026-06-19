// Next.js 15 config.
//
// Per plan §1.6 (M1) and §3.6 / §4.3 (M3/M4):
//   - `output: 'standalone'` so we can copy a minimal Node bundle into a slim Docker image
//     in M5 production deploy.
//   - Allowed dev origins for Telegram WebView (so iframing works locally).
//   - `experimental.typedRoutes` once we settle on the route map (M3).
//
// No code yet — M1 will populate this.

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
};

export default nextConfig;
