// Q5-locked: Decimal-as-string for every money field over the wire.
//
// The Mini-App receives `Money` as a string and must NEVER store it as a JS `number`
// for arithmetic — `Number("90.27000000")` immediately drops trailing-zero precision.
//
// Pattern (filled in during M1 alongside the Pydantic Money type):
//
//   import Big from 'big.js';
//
//   export type Money = string;
//
//   export const toBig = (m: Money): Big => new Big(m);
//   export const fromBig = (b: Big, scale: number): Money => b.toFixed(scale);
//
//   export const fmt = (m: Money, locale: string, decimals: number): string =>
//     new Intl.NumberFormat(locale, {
//       minimumFractionDigits: decimals,
//       maximumFractionDigits: decimals,
//     }).format(Number(m));
//   // Note: Number(m) is OK for *display* (UIs cap at <15 sig digits anyway).
//   // It is NOT OK for arithmetic. Use toBig() for that.
//
//   export const add = (a: Money, b: Money): Money => toBig(a).plus(toBig(b)).toString();
//   export const mul = (a: Money, b: Money): Money => toBig(a).times(toBig(b)).toString();
//   export const div = (a: Money, b: Money, dp: number): Money =>
//     toBig(a).div(toBig(b)).toFixed(dp);
//
// `big.js` will be added to apps/miniapp/package.json when the first money-shaped field
// lands in the API contract (M2 with accounts.opening_balance, then M3 with fx_transactions).
