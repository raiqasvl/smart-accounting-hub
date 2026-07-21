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
