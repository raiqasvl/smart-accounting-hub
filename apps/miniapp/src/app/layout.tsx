// Root layout for the Telegram Mini-App.
//
// Per plan §1.6 (M1) and §4.4 (M4 i18n):
//   - <html lang> is hydrated client-side from initDataUnsafe.user.language_code (defaults 'en').
//   - Calls Telegram.WebApp.ready() in a 'use client' boundary at mount.
//   - Mounts:
//       <QueryClientProvider>     TanStack Query client with staleTime 30s
//       <FluentLocalizationProvider> Fluent bundle for the active locale (en/ru)
//       <ThemeProvider>           shadcn theme tokens
//   - Loads Tailwind global stylesheet.
//   - Sets viewport so the WebApp fills the Telegram WebView correctly.
