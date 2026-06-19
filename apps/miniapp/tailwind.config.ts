// Tailwind 3 config. shadcn/ui colour tokens land here in M1 after `npx shadcn@latest init`.
// Per plan §1.6 (M1) — content globs cover src/**/*.{ts,tsx}.

import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      // shadcn/ui theme tokens injected by `npx shadcn@latest init` in M1.
    },
  },
  plugins: [],
};

export default config;
