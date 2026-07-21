// Telegram WebApp helpers — thin wrappers over the official window.Telegram.WebApp global
// (injected by telegram-web-app.js, loaded in the root layout). Server-side / non-Telegram
// contexts return safe fallbacks. (The @telegram-apps SDK replaces this in M2 if needed.)

interface TelegramWebApp {
  initData: string;
  initDataUnsafe?: { user?: { language_code?: string; first_name?: string } };
  ready: () => void;
  expand?: () => void;
}

function webApp(): TelegramWebApp | undefined {
  if (typeof window === 'undefined') return undefined;
  return (window as unknown as { Telegram?: { WebApp?: TelegramWebApp } })
    .Telegram?.WebApp;
}

/** Raw initData query string to POST to /auth/telegram (server verifies the HMAC). */
export function getRawInitData(): string {
  const data = webApp()?.initData;
  if (!data) {
    throw new Error(
      'Telegram initData unavailable — open this inside Telegram.'
    );
  }
  return data;
}

/** Pre-auth locale hint from Telegram (the authoritative language comes later from /me). */
export function getLanguageCode(): string {
  return webApp()?.initDataUnsafe?.user?.language_code ?? 'en';
}

export function telegramReady(): void {
  const app = webApp();
  app?.ready();
  app?.expand?.();
}
