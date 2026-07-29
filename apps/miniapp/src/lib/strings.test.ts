// The EN and RU dictionaries must stay key-for-key identical, so a Russian user never sees an
// English fallback (or a raw key) in the UI.
import { describe, expect, it } from 'vitest';

import { CATALOGUES, makeTranslate } from './strings';

describe('ui strings', () => {
  it('has identical EN and RU key sets', () => {
    const en = Object.keys(CATALOGUES.en).sort();
    const ru = Object.keys(CATALOGUES.ru).sort();
    expect(en.length).toBeGreaterThan(0);
    expect(ru).toEqual(en);
  });

  it('has no empty values', () => {
    for (const [locale, dict] of Object.entries(CATALOGUES)) {
      for (const [key, value] of Object.entries(dict)) {
        expect(value.trim(), `${locale}.${key} is empty`).not.toBe('');
      }
    }
  });

  it('interpolates {vars} and falls back to English', () => {
    const ru = makeTranslate('ru');
    expect(ru('report-samples', { count: 2, total: '11000 USD' })).toContain(
      '2'
    );
    expect(makeTranslate('xx')('tab-books')).toBe(CATALOGUES.en['tab-books']);
  });
});
