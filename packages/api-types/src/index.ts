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

// M3 DTOs (FX transactions + weighted-average).
export type TransactionOut = components['schemas']['TransactionOut'];
export type TransactionCreateIn = components['schemas']['TransactionCreateIn'];
export type TransactionPatchIn = components['schemas']['TransactionPatchIn'];
export type TransactionPage = components['schemas']['TransactionPage'];
export type WeightedAvgReportOut =
  components['schemas']['WeightedAvgReportOut'];
export type FxRateOut = components['schemas']['FxRateOut'];

// M4 DTOs (categories, movements, balance series).
export type CategoryOut = components['schemas']['CategoryOut'];
export type CategoryCreateIn = components['schemas']['CategoryCreateIn'];
export type CategoryPatchIn = components['schemas']['CategoryPatchIn'];
export type CategoryMoveIn = components['schemas']['CategoryMoveIn'];
export type TransferCreateIn = components['schemas']['TransferCreateIn'];
export type FxConversionCreateIn =
  components['schemas']['FxConversionCreateIn'];
export type AccountBalanceSeriesOut =
  components['schemas']['AccountBalanceSeriesOut'];
