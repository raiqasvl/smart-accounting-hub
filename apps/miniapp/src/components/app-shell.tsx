'use client';

// The Mini-App shell: a header with the book picker (switch re-mints the JWT) + a role badge, a
// tab bar, and the active tab's content. Everything book-scoped keys off me.active_book.
import type { MeOut } from '@shared/index';
import { useState } from 'react';

import { AccountsTab } from '@/components/accounts-tab';
import { BooksTab } from '@/components/books-tab';
import { ReportsTab } from '@/components/reports-tab';
import { SettingsTab } from '@/components/settings-tab';
import { TradesTab } from '@/components/trades-tab';
import { Badge, Select, Spinner } from '@/components/ui';
import { useMe, useSwitchBook } from '@/lib/hooks';
import { makeTranslate, StringsProvider, useT } from '@/lib/strings';

type Tab = 'books' | 'accounts' | 'trades' | 'reports' | 'settings';

function ErrorCard({ code }: { code: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <div className="rounded-xl bg-card p-6 text-sm text-fg">
        Something went wrong ({code}).
      </div>
    </div>
  );
}

export function AppShell() {
  const { data: me, isLoading, error } = useMe();
  if (error) {
    const code = error instanceof Error ? error.message : 'unknown_error';
    return <ErrorCard code={code} />;
  }
  if (isLoading || !me) {
    return (
      <div className="min-h-screen">
        <Spinner label="Loading…" />
      </div>
    );
  }
  return (
    <StringsProvider value={makeTranslate(me.user.language)}>
      <Shell me={me} />
    </StringsProvider>
  );
}

function Shell({ me }: { me: MeOut }) {
  const t = useT();
  const [tab, setTab] = useState<Tab>('books');
  const switchBook = useSwitchBook();
  const active = me.active_book;

  const tabs: { id: Tab; label: string }[] = [
    { id: 'books', label: t('tab-books') },
    { id: 'accounts', label: t('tab-accounts') },
    { id: 'trades', label: t('tab-trades') },
    { id: 'reports', label: t('tab-reports') },
    { id: 'settings', label: t('tab-settings') },
  ];

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-3 border-b border-border bg-bg/95 px-4 py-3 backdrop-blur">
        <div className="min-w-0 flex-1">
          <Select
            aria-label={t('switch-book')}
            value={active.id}
            disabled={switchBook.isPending}
            onChange={(e) => switchBook.mutate(Number(e.target.value))}
          >
            {me.books.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </div>
        <Badge>{t(`role-${active.role}`)}</Badge>
      </header>

      <main className="flex-1 px-4 py-4 pb-24">
        {tab === 'books' && <BooksTab me={me} />}
        {tab === 'accounts' && (
          <AccountsTab bookId={active.id} role={active.role} />
        )}
        {tab === 'trades' && (
          <TradesTab
            bookId={active.id}
            role={active.role}
            baseCurrency={active.base_currency_code}
          />
        )}
        {tab === 'reports' && <ReportsTab bookId={active.id} />}
        {tab === 'settings' && (
          <SettingsTab bookId={active.id} role={active.role} />
        )}
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-10 mx-auto flex max-w-md border-t border-border bg-bg">
        {tabs.map((tb) => (
          <button
            key={tb.id}
            onClick={() => setTab(tb.id)}
            className={
              'flex-1 py-3 text-sm font-medium ' +
              (tab === tb.id ? 'text-accent' : 'text-muted')
            }
          >
            {tb.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
