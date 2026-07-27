// Money display helpers. Wire values are decimal strings (D23); arithmetic/formatting goes through
// big.js so we never lose precision to JS floats. Display-only — never send these back as numbers.
import Big from 'big.js';

// Format a decimal-string amount for display, trimming the NUMERIC(20,8) trailing zeros to `dp`.
export function formatMoney(value: string, dp = 2): string {
  try {
    return new Big(value).toFixed(dp);
  } catch {
    return value;
  }
}

// A rate can carry more significant digits than a balance; default to 4dp.
export function formatRate(value: string | null | undefined, dp = 4): string {
  if (value === null || value === undefined) return '—';
  try {
    return new Big(value).toFixed(dp);
  } catch {
    return value;
  }
}
