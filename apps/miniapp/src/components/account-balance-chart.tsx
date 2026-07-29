'use client';

// Running balance for one account: opening balance plus every leg that touches it.
import { useEffect, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Card, Field, Select, Spinner } from '@/components/ui';
import { useAccountBalance, useAccounts } from '@/lib/hooks';
import { formatMoney } from '@/lib/money';
import { useT } from '@/lib/strings';

const CHART_BOX = { height: 200 };
const CHART_MARGIN = { top: 8, right: 8, left: 8, bottom: 0 };
const AXIS_TICK = { fontSize: 10, fill: 'var(--muted)' };
const LINE_DOT = { r: 2 };

export function AccountBalanceChart({ bookId }: { bookId: number }) {
  const t = useT();
  const [accountId, setAccountId] = useState<number | null>(null);

  const accounts = useAccounts(bookId, false);
  const series = useAccountBalance(bookId, accountId);

  useEffect(() => {
    if (accountId === null && accounts.data?.length)
      setAccountId(accounts.data[0].id);
  }, [accounts.data, accountId]);

  const points = (series.data?.points ?? []).map((p) => ({
    label: new Date(p.at).toLocaleDateString(),
    balance: Number(p.balance),
  }));

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-base font-semibold">{t('balance-title')}</h2>
      <Field label={t('balance-account')}>
        <Select
          value={accountId ?? ''}
          onChange={(e) => setAccountId(Number(e.target.value))}
        >
          {accounts.data?.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.currency_code})
            </option>
          ))}
        </Select>
      </Field>

      <Card>
        {series.isLoading ? <Spinner /> : null}
        {series.data ? (
          <div className="mb-3 flex flex-col gap-1">
            <span className="text-xs uppercase tracking-wide text-muted">
              {t('balance-current')}
            </span>
            <span className="text-2xl font-semibold tabular-nums">
              {formatMoney(
                series.data.points.length
                  ? series.data.points[series.data.points.length - 1].balance
                  : series.data.opening_balance
              )}{' '}
              {series.data.currency_code}
            </span>
          </div>
        ) : null}
        {points.length > 0 ? (
          <div style={CHART_BOX}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={points} margin={CHART_MARGIN}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={AXIS_TICK} />
                <YAxis width={52} tick={AXIS_TICK} domain={['auto', 'auto']} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="balance"
                  stroke="var(--accent)"
                  dot={LINE_DOT}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-muted">
            {t('balance-empty')}
          </p>
        )}
      </Card>
    </div>
  );
}
