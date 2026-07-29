'use client';

// Lightweight UI strings for the Mini-App (en/ru). A full @fluent/react provider is deferred; this
// small typed dictionary + {var} interpolation covers the M2 shell without extra machinery.
import { createContext, useContext } from 'react';

type Dict = Record<string, string>;

const EN: Dict = {
  'tab-books': 'Books',
  'tab-accounts': 'Accounts',
  'tab-settings': 'Settings',
  'books-title': 'Your books',
  'books-new': 'New book',
  'book-name': 'Name',
  'book-kind': 'Kind',
  'book-currency': 'Base currency',
  'kind-0': 'Personal',
  'kind-1': 'Family',
  'kind-2': 'Business',
  'accounts-title': 'Accounts',
  'accounts-new': 'New account',
  'accounts-empty': 'No accounts yet. Add one to start.',
  'account-name': 'Name',
  'account-currency': 'Currency',
  'account-kind': 'Kind',
  'account-opening': 'Opening balance',
  'account-archive': 'Archive',
  'account-delete': 'Delete',
  'acc-kind-0': 'Cash',
  'acc-kind-1': 'Bank',
  'acc-kind-2': 'Card',
  'acc-kind-3': 'Brokerage',
  'acc-kind-4': 'Other',
  'show-archived': 'Show archived',
  'settings-title': 'Settings',
  'invites-title': 'Invites',
  'invites-empty': 'No pending invites.',
  'invite-role': 'Role',
  'invite-new': 'Invite member',
  'invite-copy': 'Copy link',
  'invite-copied': 'Copied!',
  'invite-revoke': 'Revoke',
  'role-0': 'Owner',
  'role-1': 'Admin',
  'role-2': 'Editor',
  'role-3': 'Viewer',
  'switch-book': 'Switch book',
  'tab-trades': 'Trades',
  'tab-reports': 'Reports',
  'trades-title': 'Trades',
  'trades-new': 'Record trade',
  'trades-empty': 'No trades yet. Record your first.',
  'trades-export': 'Export CSV',
  'trade-direction': 'Direction',
  'trade-quote': 'Currency',
  'trade-amount': 'Amount',
  'trade-rate': 'Rate',
  'trade-dir-sell': 'Sell',
  'trade-dir-buy': 'Buy',
  'reports-title': 'Weighted-average rate',
  'report-direction': 'Direction',
  'report-quote': 'Currency',
  'report-avg': 'Weighted average',
  'report-samples': '{count} trades · {total}',
  'report-empty': 'No trades for this selection yet.',
  'trade-category': 'Category',
  'category-none': 'No category',
  'categories-title': 'Categories',
  'categories-new': 'New category',
  'categories-empty': 'No categories yet.',
  'category-name': 'Name',
  'category-kind': 'Kind',
  'category-parent': 'Parent',
  'category-root': '— top level —',
  'category-move': 'Move',
  'category-archive': 'Archive',
  'category-delete': 'Delete',
  'cat-kind-0': 'Income',
  'cat-kind-1': 'Expense',
  'cat-kind-2': 'Both',
  'balance-title': 'Account balance',
  'balance-account': 'Account',
  'balance-current': 'Current balance',
  'balance-empty': 'No movements on this account yet.',
  record: 'Record',
  cancel: 'Cancel',
  create: 'Create',
  loading: 'Loading…',
  error: 'Something went wrong ({code}).',
  archived: 'archived',
};

const RU: Dict = {
  'tab-books': 'Книги',
  'tab-accounts': 'Счета',
  'tab-settings': 'Настройки',
  'books-title': 'Ваши книги',
  'books-new': 'Новая книга',
  'book-name': 'Название',
  'book-kind': 'Тип',
  'book-currency': 'Базовая валюта',
  'kind-0': 'Личная',
  'kind-1': 'Семейная',
  'kind-2': 'Бизнес',
  'accounts-title': 'Счета',
  'accounts-new': 'Новый счёт',
  'accounts-empty': 'Пока нет счетов. Добавьте первый.',
  'account-name': 'Название',
  'account-currency': 'Валюта',
  'account-kind': 'Тип',
  'account-opening': 'Начальный баланс',
  'account-archive': 'В архив',
  'account-delete': 'Удалить',
  'acc-kind-0': 'Наличные',
  'acc-kind-1': 'Банк',
  'acc-kind-2': 'Карта',
  'acc-kind-3': 'Брокерский',
  'acc-kind-4': 'Другое',
  'show-archived': 'Показать архив',
  'settings-title': 'Настройки',
  'invites-title': 'Приглашения',
  'invites-empty': 'Нет активных приглашений.',
  'invite-role': 'Роль',
  'invite-new': 'Пригласить участника',
  'invite-copy': 'Копировать ссылку',
  'invite-copied': 'Скопировано!',
  'invite-revoke': 'Отозвать',
  'role-0': 'Владелец',
  'role-1': 'Администратор',
  'role-2': 'Редактор',
  'role-3': 'Наблюдатель',
  'switch-book': 'Сменить книгу',
  'tab-trades': 'Сделки',
  'tab-reports': 'Отчёты',
  'trades-title': 'Сделки',
  'trades-new': 'Записать сделку',
  'trades-empty': 'Пока нет сделок. Запишите первую.',
  'trades-export': 'Экспорт CSV',
  'trade-direction': 'Направление',
  'trade-quote': 'Валюта',
  'trade-amount': 'Сумма',
  'trade-rate': 'Курс',
  'trade-dir-sell': 'Продажа',
  'trade-dir-buy': 'Покупка',
  'reports-title': 'Средневзвешенный курс',
  'report-direction': 'Направление',
  'report-quote': 'Валюта',
  'report-avg': 'Средневзвешенный',
  'report-samples': '{count} сделок · {total}',
  'report-empty': 'Пока нет сделок для этого выбора.',
  'trade-category': 'Категория',
  'category-none': 'Без категории',
  'categories-title': 'Категории',
  'categories-new': 'Новая категория',
  'categories-empty': 'Пока нет категорий.',
  'category-name': 'Название',
  'category-kind': 'Тип',
  'category-parent': 'Родитель',
  'category-root': '— верхний уровень —',
  'category-move': 'Переместить',
  'category-archive': 'В архив',
  'category-delete': 'Удалить',
  'cat-kind-0': 'Доход',
  'cat-kind-1': 'Расход',
  'cat-kind-2': 'Оба',
  'balance-title': 'Баланс счёта',
  'balance-account': 'Счёт',
  'balance-current': 'Текущий баланс',
  'balance-empty': 'По этому счёту пока нет движений.',
  record: 'Записать',
  cancel: 'Отмена',
  create: 'Создать',
  loading: 'Загрузка…',
  error: 'Что-то пошло не так ({code}).',
  archived: 'в архиве',
};

// Exported so a test can assert EN/RU key parity (see strings.test.ts).
export const CATALOGUES: Record<string, Dict> = { en: EN, ru: RU };

export type Translate = (
  key: string,
  vars?: Record<string, string | number>
) => string;

export function makeTranslate(language: string): Translate {
  const dict = CATALOGUES[language.startsWith('ru') ? 'ru' : 'en'] ?? EN;
  return (key, vars) => {
    let text = dict[key] ?? EN[key] ?? key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        text = text.replace(`{${k}}`, String(v));
      }
    }
    return text;
  };
}

const StringsContext = createContext<Translate>(makeTranslate('en'));

export const StringsProvider = StringsContext.Provider;

export function useT(): Translate {
  return useContext(StringsContext);
}
