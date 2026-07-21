// Tailwind 3 config. Hand-rolled shadcn-pattern tokens (D-M2-1: no shadcn CLI). Colours map to the
// CSS vars set in globals.css, which in turn track Telegram's injected --tg-theme-* palette.

import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        fg: 'var(--fg)',
        card: 'var(--card)',
        muted: 'var(--muted)',
        accent: 'var(--accent)',
        'accent-fg': 'var(--accent-fg)',
        border: 'var(--border)',
        danger: 'var(--danger)',
      },
      borderRadius: {
        xl: '0.875rem',
      },
    },
  },
  plugins: [],
};

export default config;
