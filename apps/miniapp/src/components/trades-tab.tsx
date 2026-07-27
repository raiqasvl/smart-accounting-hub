'use client';

// Trades tab: the FX transaction list + a "Record trade" Drawer. Money renders via big.js (never
// raw NUMERIC scale). Base currency is the book's base; quote is picked from the catalogue.
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
  useCreateTransaction,
  useCurrencies,
  useTransactions,
} from '@/lib/hooks';
import { formatMoney, formatRate } from '@/lib/money';
import { useT } from '@/lib/strings';

export function TradesTab({
  bookId,
  role,
  baseCurrency,
}: {
  bookId: number;
  role: number;
  baseCurrency: string;
}) {
  const t = useT();
  const canWrite = role <= 2;
  const [open, setOpen] = useState(false);

  const trades = useTransactions(bookId);
  const currencies = useCurrencies(bookId);
  const create = useCreateTransaction(bookId);

  const [direction, setDirection] = useState<'sell' | 'buy'>('sell');
  const [quote, setQuote] = useState('');
  const [amount, setAmount] = useState('');
  const [rate, setRate] = useState('');

  useEffect(() => {
    if (!quote && currencies.data?.length) setQuote(currencies.data[0].code);
  }, [currencies.data, quote]);

  const submit = () => {
    if (!quote || !amount.trim() || !rate.trim()) return;
    create.mutate(
      {
        direction,
        base_currency_code: baseCurrency,
        quote_currency_code: quote,
        amount_quote: amount.trim(),
        rate: rate.trim(),
        fee: '0',
        idempotency_key: crypto.randomUUID(),
      },
      {
        onSuccess: () => {
          setOpen(false);
          setAmount('');
          setRate('');
        },
      }
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t('trades-title')}</h1>
        {canWrite ? (
          <Button size="sm" onClick={() => setOpen(true)}>
            + {t('trades-new')}
          </Button>
        ) : null}
      </div>

      {trades.isLoading ? <Spinner /> : null}
      {trades.data?.items.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted">
          {t('trades-empty')}
        </p>
      ) : null}

      {trades.data?.items.map((tx) => (
        <Card key={tx.id} className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-medium">
              {t(`trade-dir-${tx.direction}`)} {formatMoney(tx.amount_quote)}{' '}
              {tx.quote_currency_code}
            </p>
            <p className="text-xs text-muted">
              @ {formatRate(tx.rate)} · {formatMoney(tx.amount_base)}{' '}
              {tx.base_currency_code}
            </p>
          </div>
          <Badge>{tx.quote_currency_code}</Badge>
        </Card>
      ))}

      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        title={t('trades-new')}
      >
        <div className="flex flex-col gap-4">
          <Field label={t('trade-direction')}>
            <Select
              value={direction}
              onChange={(e) =>
                setDirection(e.target.value === 'buy' ? 'buy' : 'sell')
              }
            >
              <option value="sell">{t('trade-dir-sell')}</option>
              <option value="buy">{t('trade-dir-buy')}</option>
            </Select>
          </Field>
          <Field label={t('trade-quote')}>
            <Select value={quote} onChange={(e) => setQuote(e.target.value)}>
              {currencies.data?.map((c) => (
                <option key={c.id} value={c.code}>
                  {c.code}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('trade-amount')}>
            <Input
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </Field>
          <Field label={`${t('trade-rate')} (${baseCurrency}/${quote || '—'})`}>
            <Input
              inputMode="decimal"
              value={rate}
              onChange={(e) => setRate(e.target.value)}
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
              {t('record')}
            </Button>
          </div>
        </div>
      </Drawer>
    </div>
  );
}
