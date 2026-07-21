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
  cancel: 'Отмена',
  create: 'Создать',
  loading: 'Загрузка…',
  error: 'Что-то пошло не так ({code}).',
  archived: 'в архиве',
};

const CATALOGUES: Record<string, Dict> = { en: EN, ru: RU };

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
