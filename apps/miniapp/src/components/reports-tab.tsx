'use client';

// Reports tab: the headline weighted-average rate (D16) for a chosen (currency, direction), plus a
// Recharts line of each trade's rate with a reference line at the weighted average.
import { useEffect, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { AccountBalanceChart } from '@/components/account-balance-chart';
import { Card, Field, Select, Spinner } from '@/components/ui';
import { useCurrencies, useTransactions, useWeightedAvg } from '@/lib/hooks';
import { formatMoney, formatRate } from '@/lib/money';
import { useT } from '@/lib/strings';

// Hoisted so they aren't re-created each render (oxlint react-perf).
const CHART_BOX = { height: 200 };
const CHART_MARGIN = { top: 8, right: 8, left: 8, bottom: 0 };
const AXIS_TICK = { fontSize: 10, fill: 'var(--muted)' };
const LINE_DOT = { r: 3 };

export function ReportsTab({ bookId }: { bookId: number }) {
  const t = useT();
  const [direction, setDirection] = useState<'sell' | 'buy'>('sell');
  const [quote, setQuote] = useState('');

  const currencies = useCurrencies(bookId);
  const trades = useTransactions(bookId);
  const report = useWeightedAvg(bookId, quote, direction);

  useEffect(() => {
    if (!quote && currencies.data?.length) setQuote(currencies.data[0].code);
  }, [currencies.data, quote]);

  const points = (trades.data?.items ?? [])
    .filter(
      (tx) => tx.quote_currency_code === quote && tx.direction === direction
    )
    .slice()
    .reverse()
    .map((tx) => ({
      label: new Date(tx.occurred_at).toLocaleDateString(),
      rate: Number(tx.rate),
    }));

  const avg = report.data?.weighted_avg_rate ?? null;

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">{t('reports-title')}</h1>

      <div className="flex gap-2">
        <div className="flex-1">
          <Field label={t('report-direction')}>
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
        </div>
        <div className="flex-1">
          <Field label={t('report-quote')}>
            <Select value={quote} onChange={(e) => setQuote(e.target.value)}>
              {currencies.data?.map((c) => (
                <option key={c.id} value={c.code}>
                  {c.code}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </div>

      <Card>
        {report.isLoading ? <Spinner /> : null}
        {report.data && avg === null ? (
          <p className="py-6 text-center text-sm text-muted">
            {t('report-empty')}
          </p>
        ) : null}
        {avg !== null ? (
          <div className="flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-muted">
              {t('report-avg')}
            </span>
            <span className="text-3xl font-semibold tabular-nums">
              {formatRate(avg)}
            </span>
            <span className="text-xs text-muted">
              {t('report-samples', {
                count: report.data?.sample_count ?? 0,
                total: `${formatMoney(report.data?.sum_amount_quote ?? '0')} ${quote}`,
              })}
            </span>
          </div>
        ) : null}
      </Card>

      {points.length > 0 && avg !== null ? (
        <Card>
          <div style={CHART_BOX}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points} margin={CHART_MARGIN}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={AXIS_TICK} />
                <YAxis width={44} tick={AXIS_TICK} domain={['auto', 'auto']} />
                <Tooltip />
                <ReferenceLine
                  y={Number(avg)}
                  stroke="var(--accent)"
                  strokeDasharray="4 4"
                />
                <Line
                  type="monotone"
                  dataKey="rate"
                  stroke="var(--accent)"
                  dot={LINE_DOT}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ) : null}

      <AccountBalanceChart bookId={bookId} />
    </div>
  );
}
