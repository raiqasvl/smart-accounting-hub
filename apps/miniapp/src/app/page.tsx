'use client';

import { FluentBundle, FluentResource } from '@fluent/bundle';
import { useQuery } from '@tanstack/react-query';

import { ApiError, fetchMe } from '@/lib/api-client';

// M1 greeting strings (mirrors src/i18n/{en,ru}/main.ftl). Inlined so the page needs no .ftl
// file loader; M4 wires the full @fluent/react provider over the .ftl catalogues.
const GREETING_FTL: Record<string, string> = {
  en: 'card-greeting = Hello { $name }, book "{ $book }"',
  ru: 'card-greeting = Привет, { $name }, книга «{ $book }»',
};

function greeting(language: string, name: string, book: string): string {
  const locale = language.startsWith('ru') ? 'ru' : 'en';
  const bundle = new FluentBundle(locale);
  bundle.addResource(new FluentResource(GREETING_FTL[locale]));
  const message = bundle.getMessage('card-greeting');
  if (!message?.value) return `${name} — ${book}`;
  return bundle.formatPattern(message.value, { name, book });
}

const cardStyle: React.CSSProperties = {
  border: '1px solid rgba(0,0,0,0.12)',
  borderRadius: 14,
  padding: '22px 26px',
  boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
  maxWidth: 420,
};

const mainStyle: React.CSSProperties = {
  display: 'flex',
  minHeight: '100vh',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 24,
};

const messageStyle: React.CSSProperties = { margin: 0 };
const titleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: 18,
  fontWeight: 600,
};
const subtitleStyle: React.CSSProperties = {
  margin: '8px 0 0',
  opacity: 0.6,
  fontSize: 13,
};

export default function Home() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
  });

  if (error) {
    const code = error instanceof ApiError ? error.code : 'unknown_error';
    return (
      <main style={mainStyle}>
        <div style={cardStyle}>
          <p style={messageStyle}>Something went wrong ({code}).</p>
        </div>
      </main>
    );
  }

  if (isLoading || !data) {
    return (
      <main style={mainStyle}>
        <div style={cardStyle}>
          <p style={messageStyle}>Loading…</p>
        </div>
      </main>
    );
  }

  const name = data.user.first_name ?? data.user.username ?? 'there';
  const text = greeting(data.user.language, name, data.active_book.name);

  return (
    <main style={mainStyle}>
      <div style={cardStyle}>
        <p style={titleStyle}>{text}</p>
        <p style={subtitleStyle}>{data.active_book.base_currency_code}</p>
      </div>
    </main>
  );
}
