import type { Metadata, Viewport } from 'next';
import Script from 'next/script';
import type { ReactNode } from 'react';

import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'Smart Accounting Hub',
  description: 'Telegram Mini-App for FX accounting.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

const bodyStyle: React.CSSProperties = {
  margin: 0,
  fontFamily: 'system-ui, -apple-system, sans-serif',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  // telegram-web-app.js injects --tg-theme-* CSS vars onto <html>/<body> before hydration,
  // so those elements legitimately differ from the server HTML — suppress the mismatch warning.
  return (
    <html lang="en" suppressHydrationWarning>
      <body style={bodyStyle} suppressHydrationWarning>
        {/* Official Telegram WebApp bridge — populates window.Telegram.WebApp before hydration. */}
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
