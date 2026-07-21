'use client';

import { useEffect, useState } from 'react';

import {
  Badge,
  Button,
  Card,
  Drawer,
  Field,
  Input,
  Select,
  Spinner,
} from '@/components/ui';
import {
  useAccounts,
  useCreateAccount,
  useCurrencies,
  useDeleteAccount,
  usePatchAccount,
} from '@/lib/hooks';
import { useT } from '@/lib/strings';

const ACCOUNT_KINDS = [0, 1, 2, 3, 4];

export function AccountsTab({
  bookId,
  role,
}: {
  bookId: number;
  role: number;
}) {
  const t = useT();
  const canWrite = role <= 2;
  const canDelete = role === 0;
  const [showArchived, setShowArchived] = useState(false);
  const [open, setOpen] = useState(false);

  const accounts = useAccounts(bookId, showArchived ? undefined : false);
  const currencies = useCurrencies(bookId);
  const create = useCreateAccount(bookId);
  const patch = usePatchAccount(bookId);
  const remove = useDeleteAccount(bookId);

  const [name, setName] = useState('');
  const [currency, setCurrency] = useState('');
  const [kind, setKind] = useState(0);
  const [opening, setOpening] = useState('0');

  useEffect(() => {
    if (!currency && currencies.data?.length)
      setCurrency(currencies.data[0].code);
  }, [currencies.data, currency]);

  const submit = () => {
    if (!name.trim() || !currency) return;
    create.mutate(
      {
        currency_code: currency,
        name: name.trim(),
        kind,
        opening_balance: opening.trim() || '0',
      },
      {
        onSuccess: () => {
          setOpen(false);
          setName('');
          setOpening('0');
          setKind(0);
        },
      }
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t('accounts-title')}</h1>
        {canWrite ? (
          <Button size="sm" onClick={() => setOpen(true)}>
            + {t('accounts-new')}
          </Button>
        ) : null}
      </div>

      <label className="flex items-center gap-2 text-xs text-muted">
        <input
          type="checkbox"
          checked={showArchived}
          onChange={(e) => setShowArchived(e.target.checked)}
        />
        {t('show-archived')}
      </label>

      {accounts.isLoading ? <Spinner /> : null}
      {accounts.data?.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted">
          {t('accounts-empty')}
        </p>
      ) : null}

      {accounts.data?.map((a) => (
        <Card key={a.id} className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-medium">
              {a.name} {a.archived ? <Badge>{t('archived')}</Badge> : null}
            </p>
            <p className="text-xs text-muted">
              {t(`acc-kind-${a.kind}`)} · {a.currency_code}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <span className="text-sm font-semibold tabular-nums">
              {a.opening_balance} {a.currency_code}
            </span>
            {canWrite && !a.archived ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  patch.mutate({ id: a.id, body: { archived: true } })
                }
              >
                {t('account-archive')}
              </Button>
            ) : null}
            {canDelete ? (
              <Button
                variant="danger"
                size="sm"
                onClick={() => remove.mutate(a.id)}
              >
                {t('account-delete')}
              </Button>
            ) : null}
          </div>
        </Card>
      ))}

      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        title={t('accounts-new')}
      >
        <div className="flex flex-col gap-4">
          <Field label={t('account-name')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t('account-currency')}>
            <Select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              {currencies.data?.map((c) => (
                <option key={c.id} value={c.code}>
                  {c.code}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('account-kind')}>
            <Select
              value={kind}
              onChange={(e) => setKind(Number(e.target.value))}
            >
              {ACCOUNT_KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(`acc-kind-${k}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('account-opening')}>
            <Input
              inputMode="decimal"
              value={opening}
              onChange={(e) => setOpening(e.target.value)}
            />
          </Field>
          {create.isError ? (
            <p className="text-xs text-danger">
              {t('error', {
                code:
                  create.error instanceof Error ? create.error.message : '?',
              })}
            </p>
          ) : null}
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="block"
              onClick={() => setOpen(false)}
            >
              {t('cancel')}
            </Button>
            <Button size="block" onClick={submit} disabled={create.isPending}>
              {t('create')}
            </Button>
          </div>
        </div>
      </Drawer>
    </div>
  );
}
