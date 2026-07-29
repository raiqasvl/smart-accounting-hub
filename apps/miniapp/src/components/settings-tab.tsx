'use client';

import { useState } from 'react';

import { CategoriesTab } from '@/components/categories-tab';
import { Badge, Button, Card, Field, Select, Spinner } from '@/components/ui';
import { useCreateInvite, useInvites, useRevokeInvite } from '@/lib/hooks';
import { useT } from '@/lib/strings';

const INVITABLE_ROLES = [1, 2, 3]; // admin, editor, viewer (never owner)

export function SettingsTab({
  bookId,
  role,
}: {
  bookId: number;
  role: number;
}) {
  const t = useT();
  const canInvite = role <= 1; // owner / admin
  const invites = useInvites(bookId);
  const create = useCreateInvite(bookId);
  const revoke = useRevokeInvite(bookId);
  const [newRole, setNewRole] = useState(2);
  const [copied, setCopied] = useState<number | null>(null);

  const copy = async (id: number, link: string) => {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(id);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      /* clipboard unavailable outside a secure context */
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <h1 className="text-lg font-semibold">{t('settings-title')}</h1>

      {!canInvite ? (
        <p className="py-8 text-center text-sm text-muted">
          {t('invites-empty')}
        </p>
      ) : (
        <>
          <Card className="flex flex-col gap-3">
            <h2 className="text-sm font-semibold">{t('invite-new')}</h2>
            <Field label={t('invite-role')}>
              <Select
                value={newRole}
                onChange={(e) => setNewRole(Number(e.target.value))}
              >
                {INVITABLE_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {t(`role-${r}`)}
                  </option>
                ))}
              </Select>
            </Field>
            <Button
              size="block"
              disabled={create.isPending}
              onClick={() =>
                create.mutate({ role: newRole, ttl_minutes: 1440 })
              }
            >
              + {t('invite-new')}
            </Button>
          </Card>

          <h2 className="mt-2 text-sm font-semibold">{t('invites-title')}</h2>
          {invites.isLoading ? <Spinner /> : null}
          {invites.data?.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">
              {t('invites-empty')}
            </p>
          ) : null}

          {invites.data?.map((inv) => (
            <Card key={inv.id} className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <Badge>{t(`role-${inv.role}`)}</Badge>
                <span className="text-xs text-muted">
                  {new Date(inv.expires_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() => void copy(inv.id, inv.deep_link)}
                >
                  {copied === inv.id ? t('invite-copied') : t('invite-copy')}
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => revoke.mutate(inv.id)}
                >
                  {t('invite-revoke')}
                </Button>
              </div>
            </Card>
          ))}
        </>
      )}

      <div className="mt-6 border-t border-border pt-6">
        <CategoriesTab bookId={bookId} role={role} />
      </div>
    </div>
  );
}
