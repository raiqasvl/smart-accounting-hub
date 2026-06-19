// Mini-App entry page (`/`).
//
// Per plan §1.6 (M1):
//   1. Reads Telegram.WebApp.initData via @telegram-apps/sdk-react.
//   2. POSTs to {NEXT_PUBLIC_API_BASE_URL}/auth/telegram with {init_data}.
//   3. Stores returned JWT in memory + sessionStorage; sets up TanStack Query Authorization header.
//   4. Calls GET /me to load the user + active book.
//   5. Renders one shadcn <Card> at MVP: "Hello {first_name}, book '{book.name}'".
//
// M2 expands this into a tabbed dashboard: Books · Accounts · Trades · Reports · Settings.
//
// 'use client' — Mini-App is fully client-side after initial hydration.
