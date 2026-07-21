// Public surface of @smart-accounting/api-types.
// Re-exports the openapi-typescript output plus convenience aliases for the M1 DTOs.
// Regenerate api.d.ts via `pnpm types:gen` after any API contract change.
export type { components, paths } from './api';

import type { components } from './api';

export type UserOut = components['schemas']['UserOut'];
export type BookOut = components['schemas']['BookOut'];
export type TokenOut = components['schemas']['TokenOut'];
export type MeOut = components['schemas']['MeOut'];
export type AuthTelegramIn = components['schemas']['AuthTelegramIn'];

// M2 DTOs.
export type BookCreateIn = components['schemas']['BookCreateIn'];
export type BookPatchIn = components['schemas']['BookPatchIn'];
export type AccountOut = components['schemas']['AccountOut'];
export type AccountCreateIn = components['schemas']['AccountCreateIn'];
export type AccountPatchIn = components['schemas']['AccountPatchIn'];
export type CurrencyOut = components['schemas']['CurrencyOut'];
export type InviteOut = components['schemas']['InviteOut'];
export type InviteCreateIn = components['schemas']['InviteCreateIn'];
