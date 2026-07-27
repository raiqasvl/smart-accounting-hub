// Typed API client for the Mini-App.
//
// Same-origin calls to /api/v1/* (the Next rewrite proxies them to FastAPI, so no CORS). The JWT
// lives in memory with a sessionStorage mirror; on 401 we clear it and re-post fresh initData
// (D12 refresh model), then retry once. Errors become ApiError (the D24 {error:{code,params}}).
import type {
  AccountCreateIn,
  AccountOut,
  AccountPatchIn,
  BookCreateIn,
  BookOut,
  CurrencyOut,
  InviteCreateIn,
  InviteOut,
  MeOut,
  TokenOut,
  TransactionCreateIn,
  TransactionOut,
  TransactionPage,
  WeightedAvgReportOut,
} from '@shared/index';

import { getRawInitData } from './telegram';

const JWT_KEY = 'sa_jwt';
let memoryJwt: string | null = null;

function loadJwt(): string | null {
  if (memoryJwt) return memoryJwt;
  if (typeof sessionStorage !== 'undefined')
    memoryJwt = sessionStorage.getItem(JWT_KEY);
  return memoryJwt;
}

function storeJwt(token: string): void {
  memoryJwt = token;
  if (typeof sessionStorage !== 'undefined')
    sessionStorage.setItem(JWT_KEY, token);
}

function clearJwt(): void {
  memoryJwt = null;
  if (typeof sessionStorage !== 'undefined') sessionStorage.removeItem(JWT_KEY);
}

export class ApiError extends Error {
  readonly code: string;
  readonly params: Record<string, unknown>;

  constructor(code: string, params: Record<string, unknown> = {}) {
    super(code);
    this.name = 'ApiError';
    this.code = code;
    this.params = params;
  }
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as {
      error?: { code?: string; params?: Record<string, unknown> };
    };
    return new ApiError(
      body.error?.code ?? `http_${res.status}`,
      body.error?.params ?? {}
    );
  } catch {
    return new ApiError(`http_${res.status}`);
  }
}

async function authenticate(): Promise<TokenOut> {
  const res = await fetch('/api/v1/auth/telegram', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ init_data: getRawInitData() }),
  });
  if (!res.ok) throw await toApiError(res);
  const token = (await res.json()) as TokenOut;
  storeJwt(token.access_token);
  return token;
}

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE';

function buildInit(
  token: string | null,
  method: Method,
  body?: unknown
): RequestInit {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token ?? ''}`,
  };
  const init: RequestInit = { method, headers };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  return init;
}

async function authedFetch(
  path: string,
  method: Method = 'GET',
  body?: unknown
): Promise<Response> {
  let token = loadJwt();
  if (!token) {
    await authenticate();
    token = loadJwt();
  }
  let res = await fetch(path, buildInit(token, method, body));
  if (res.status === 401) {
    clearJwt();
    await authenticate();
    token = loadJwt();
    res = await fetch(path, buildInit(token, method, body));
  }
  return res;
}

async function request<T>(
  path: string,
  method: Method = 'GET',
  body?: unknown
): Promise<T> {
  const res = await authedFetch(path, method, body);
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function fetchMe(): Promise<MeOut> {
  return request<MeOut>('/api/v1/me');
}

export function fetchBooks(): Promise<BookOut[]> {
  return request<BookOut[]>('/api/v1/books');
}

export function createBook(body: BookCreateIn): Promise<BookOut> {
  return request<BookOut>('/api/v1/books', 'POST', body);
}

export async function switchBook(bookId: number): Promise<TokenOut> {
  const token = await request<TokenOut>(
    `/api/v1/books/${bookId}/switch`,
    'POST'
  );
  storeJwt(token.access_token);
  return token;
}

export function fetchAccounts(
  bookId: number,
  archived?: boolean
): Promise<AccountOut[]> {
  const q = archived === undefined ? '' : `?archived=${archived}`;
  return request<AccountOut[]>(`/api/v1/books/${bookId}/accounts${q}`);
}

export function createAccount(
  bookId: number,
  body: AccountCreateIn
): Promise<AccountOut> {
  return request<AccountOut>(`/api/v1/books/${bookId}/accounts`, 'POST', body);
}

export function patchAccount(
  accountId: number,
  body: AccountPatchIn
): Promise<AccountOut> {
  return request<AccountOut>(`/api/v1/accounts/${accountId}`, 'PATCH', body);
}

export function deleteAccount(accountId: number): Promise<void> {
  return request<void>(`/api/v1/accounts/${accountId}`, 'DELETE');
}

export function fetchCurrencies(bookId: number): Promise<CurrencyOut[]> {
  return request<CurrencyOut[]>(`/api/v1/currencies?book_id=${bookId}`);
}

export function fetchInvites(bookId: number): Promise<InviteOut[]> {
  return request<InviteOut[]>(`/api/v1/books/${bookId}/invites`);
}

export function createInvite(
  bookId: number,
  body: InviteCreateIn
): Promise<InviteOut> {
  return request<InviteOut>(`/api/v1/books/${bookId}/invites`, 'POST', body);
}

export function revokeInvite(bookId: number, inviteId: number): Promise<void> {
  return request<void>(`/api/v1/books/${bookId}/invites/${inviteId}`, 'DELETE');
}

// --- M3: transactions + weighted-average report ---

export function fetchTransactions(bookId: number): Promise<TransactionPage> {
  return request<TransactionPage>(`/api/v1/books/${bookId}/transactions`);
}

export function createTransaction(
  bookId: number,
  body: TransactionCreateIn
): Promise<TransactionOut> {
  return request<TransactionOut>(
    `/api/v1/books/${bookId}/transactions`,
    'POST',
    body
  );
}

export function fetchWeightedAvg(
  bookId: number,
  quote: string,
  direction: 'buy' | 'sell'
): Promise<WeightedAvgReportOut> {
  const q = new URLSearchParams({ quote, direction }).toString();
  return request<WeightedAvgReportOut>(
    `/api/v1/books/${bookId}/reports/weighted-avg-rate?${q}`
  );
}
