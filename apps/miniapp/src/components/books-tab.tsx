'use client';

import type { MeOut } from '@shared/index';
import { useState } from 'react';

import {
  Badge,
  Button,
  Card,
  Drawer,
  Field,
  Input,
  Select,
} from '@/components/ui';
import { useCreateBook } from '@/lib/hooks';
import { useT } from '@/lib/strings';

export function BooksTab({ me }: { me: MeOut }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [kind, setKind] = useState(0);
  const [currency, setCurrency] = useState('USD');
  const create = useCreateBook();

  const submit = () => {
    if (!name.trim()) return;
    create.mutate(
      {
        name: name.trim(),
        kind,
        base_currency_code: currency.trim().toUpperCase(),
        default_language: me.user.language,
      },
      {
        onSuccess: () => {
          setOpen(false);
          setName('');
          setKind(0);
          setCurrency('USD');
        },
      }
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t('books-title')}</h1>
        <Button size="sm" onClick={() => setOpen(true)}>
          + {t('books-new')}
        </Button>
      </div>

      {me.books.map((b) => (
        <Card key={b.id} className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="truncate font-medium">{b.name}</p>
            <p className="text-xs text-muted">
              {t(`kind-${b.kind}`)} · {b.base_currency_code}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {b.id === me.active_book.id ? <Badge>●</Badge> : null}
            <Badge>{t(`role-${b.role}`)}</Badge>
          </div>
        </Card>
      ))}

      <Drawer open={open} onClose={() => setOpen(false)} title={t('books-new')}>
        <div className="flex flex-col gap-4">
          <Field label={t('book-name')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t('book-kind')}>
            <Select
              value={kind}
              onChange={(e) => setKind(Number(e.target.value))}
            >
              <option value={0}>{t('kind-0')}</option>
              <option value={1}>{t('kind-1')}</option>
              <option value={2}>{t('kind-2')}</option>
            </Select>
          </Field>
          <Field label={t('book-currency')}>
            <Input
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              maxLength={3}
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
