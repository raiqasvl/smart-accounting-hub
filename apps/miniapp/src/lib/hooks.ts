'use client';

// TanStack Query hooks over the M2 endpoints. Mutations invalidate the affected query keys so the
// UI reflects writes without manual refetching. Book switch re-mints the JWT (stored by the client)
// and touches everything book-scoped, so it clears the whole cache.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type {
  AccountCreateIn,
  AccountPatchIn,
  BookCreateIn,
  CategoryCreateIn,
  CategoryMoveIn,
  CategoryPatchIn,
  InviteCreateIn,
  TransactionCreateIn,
  TransferCreateIn,
} from '@shared/index';

import {
  createAccount,
  createBook,
  createCategory,
  createInvite,
  createTransaction,
  createTransfer,
  deleteAccount,
  deleteCategory,
  fetchAccountBalance,
  fetchAccounts,
  fetchBooks,
  fetchCategories,
  fetchCurrencies,
  fetchInvites,
  fetchMe,
  fetchTransactions,
  fetchWeightedAvg,
  moveCategory,
  patchAccount,
  patchCategory,
  revokeInvite,
  switchBook,
} from './api-client';

export function useMe() {
  return useQuery({ queryKey: ['me'], queryFn: fetchMe });
}

export function useBooks() {
  return useQuery({ queryKey: ['books'], queryFn: fetchBooks });
}

export function useAccounts(bookId: number, archived?: boolean) {
  return useQuery({
    queryKey: ['accounts', bookId, archived ?? 'all'],
    queryFn: () => fetchAccounts(bookId, archived),
  });
}

export function useCurrencies(bookId: number) {
  return useQuery({
    queryKey: ['currencies', bookId],
    queryFn: () => fetchCurrencies(bookId),
  });
}

export function useInvites(bookId: number) {
  return useQuery({
    queryKey: ['invites', bookId],
    queryFn: () => fetchInvites(bookId),
  });
}

export function useCreateBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: BookCreateIn) => createBook(body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['books'] });
      void qc.invalidateQueries({ queryKey: ['me'] });
    },
  });
}

export function useSwitchBook() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (bookId: number) => switchBook(bookId),
    onSuccess: () => qc.invalidateQueries(),
  });
}

export function useCreateAccount(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AccountCreateIn) => createAccount(bookId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts', bookId] }),
  });
}

export function usePatchAccount(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: AccountPatchIn }) =>
      patchAccount(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts', bookId] }),
  });
}

export function useDeleteAccount(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['accounts', bookId] }),
  });
}

export function useCreateInvite(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: InviteCreateIn) => createInvite(bookId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invites', bookId] }),
  });
}

export function useRevokeInvite(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: number) => revokeInvite(bookId, inviteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['invites', bookId] }),
  });
}

// --- M3: transactions + weighted-average ---

export function useTransactions(bookId: number) {
  return useQuery({
    queryKey: ['trades', bookId],
    queryFn: () => fetchTransactions(bookId),
  });
}

export function useCreateTransaction(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TransactionCreateIn) => createTransaction(bookId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['trades', bookId] });
      void qc.invalidateQueries({ queryKey: ['report', bookId] });
    },
  });
}

export function useWeightedAvg(
  bookId: number,
  quote: string,
  direction: 'buy' | 'sell'
) {
  return useQuery({
    queryKey: ['report', bookId, quote, direction],
    queryFn: () => fetchWeightedAvg(bookId, quote, direction),
    enabled: quote !== '',
  });
}

// --- M4: categories, movements, balance series ---

export function useCategories(bookId: number) {
  return useQuery({
    queryKey: ['categories', bookId],
    queryFn: () => fetchCategories(bookId),
  });
}

export function useCreateCategory(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CategoryCreateIn) => createCategory(bookId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['categories', bookId] }),
  });
}

export function usePatchCategory(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: CategoryPatchIn }) =>
      patchCategory(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['categories', bookId] }),
  });
}

export function useMoveCategory(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: CategoryMoveIn }) =>
      moveCategory(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['categories', bookId] }),
  });
}

export function useDeleteCategory(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['categories', bookId] }),
  });
}

export function useCreateTransfer(bookId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: TransferCreateIn) => createTransfer(bookId, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['trades', bookId] });
      void qc.invalidateQueries({ queryKey: ['balance', bookId] });
    },
  });
}

export function useAccountBalance(bookId: number, accountId: number | null) {
  return useQuery({
    queryKey: ['balance', bookId, accountId],
    queryFn: () => fetchAccountBalance(bookId, accountId as number),
    enabled: accountId !== null,
  });
}
