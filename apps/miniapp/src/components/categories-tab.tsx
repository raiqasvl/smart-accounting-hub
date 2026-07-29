'use client';

// Categories tab: the ltree tree rendered flat-but-indented (the API already returns rows in
// depth-first path order, and each row carries its depth), plus create / move / archive / delete.
import { useState } from 'react';

import {
  Button,
  Card,
  Drawer,
  Field,
  Input,
  Select,
  Spinner,
} from '@/components/ui';
import {
  useCategories,
  useCreateCategory,
  useDeleteCategory,
  useMoveCategory,
  usePatchCategory,
} from '@/lib/hooks';
import { useT } from '@/lib/strings';

const KINDS = [0, 1, 2];

export function CategoriesTab({
  bookId,
  role,
}: {
  bookId: number;
  role: number;
}) {
  const t = useT();
  const canWrite = role <= 2;
  const [open, setOpen] = useState(false);
  const [moving, setMoving] = useState<number | null>(null);

  const categories = useCategories(bookId);
  const create = useCreateCategory(bookId);
  const patch = usePatchCategory(bookId);
  const move = useMoveCategory(bookId);
  const remove = useDeleteCategory(bookId);

  const [name, setName] = useState('');
  const [kind, setKind] = useState(1);
  const [parentId, setParentId] = useState('');

  const submit = () => {
    if (!name.trim()) return;
    create.mutate(
      {
        name: name.trim(),
        kind,
        parent_id: parentId === '' ? null : Number(parentId),
      },
      {
        onSuccess: () => {
          setOpen(false);
          setName('');
          setParentId('');
        },
      }
    );
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">{t('categories-title')}</h1>
        {canWrite ? (
          <Button size="sm" onClick={() => setOpen(true)}>
            + {t('categories-new')}
          </Button>
        ) : null}
      </div>

      {categories.isLoading ? <Spinner /> : null}
      {categories.data?.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted">
          {t('categories-empty')}
        </p>
      ) : null}

      {categories.data?.map((c) => (
        <Card key={c.id} className="flex items-center justify-between gap-2">
          <span
            className="min-w-0 truncate text-sm"
            style={{ paddingLeft: `${(c.depth - 1) * 16}px` }}
          >
            {c.depth > 1 ? '↳ ' : ''}
            {c.name}
          </span>
          {canWrite ? (
            <div className="flex shrink-0 items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMoving(moving === c.id ? null : c.id)}
              >
                {t('category-move')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  patch.mutate({ id: c.id, body: { archived: true } })
                }
              >
                {t('category-archive')}
              </Button>
              <Button
                variant="danger"
                size="sm"
                onClick={() => remove.mutate(c.id)}
              >
                {t('category-delete')}
              </Button>
            </div>
          ) : null}
          {moving === c.id ? (
            <div className="w-full pt-2">
              <Select
                value=""
                onChange={(e) => {
                  move.mutate({
                    id: c.id,
                    body: {
                      parent_id:
                        e.target.value === '' ? null : Number(e.target.value),
                    },
                  });
                  setMoving(null);
                }}
              >
                <option value="">{t('category-root')}</option>
                {categories.data
                  ?.filter((p) => p.id !== c.id)
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
              </Select>
            </div>
          ) : null}
        </Card>
      ))}

      {remove.isError ? (
        <p className="text-xs text-danger">
          {t('error', {
            code: remove.error instanceof Error ? remove.error.message : '?',
          })}
        </p>
      ) : null}

      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        title={t('categories-new')}
      >
        <div className="flex flex-col gap-4">
          <Field label={t('category-name')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t('category-kind')}>
            <Select
              value={kind}
              onChange={(e) => setKind(Number(e.target.value))}
            >
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {t(`cat-kind-${k}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('category-parent')}>
            <Select
              value={parentId}
              onChange={(e) => setParentId(e.target.value)}
            >
              <option value="">{t('category-root')}</option>
              {categories.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
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
