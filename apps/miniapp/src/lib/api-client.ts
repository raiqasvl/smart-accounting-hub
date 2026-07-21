// Typed API client for the Mini-App.
//
// Same-origin calls to /api/v1/* (the Next rewrite proxies them to FastAPI, so no CORS). The JWT
// lives in memory with a sessionStorage mirror; on 401 we clear it and re-post fresh initData
// (D12 refresh model), then retry once. Errors become ApiError (the D24 {error:{code,params}}).
import type { MeOut, TokenOut } from '@shared/index';

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

async function authedFetch(path: string): Promise<Response> {
  let token = loadJwt();
  if (!token) {
    await authenticate();
    token = loadJwt();
  }
  let res = await fetch(path, {
    headers: { Authorization: `Bearer ${token ?? ''}` },
  });
  if (res.status === 401) {
    clearJwt();
    await authenticate();
    token = loadJwt();
    res = await fetch(path, {
      headers: { Authorization: `Bearer ${token ?? ''}` },
    });
  }
  return res;
}

export async function fetchMe(): Promise<MeOut> {
  const res = await authedFetch('/api/v1/me');
  if (!res.ok) throw await toApiError(res);
  return (await res.json()) as MeOut;
}
