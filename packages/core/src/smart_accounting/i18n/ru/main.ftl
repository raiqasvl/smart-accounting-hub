# Russian Fluent translations for the bot (mirrors en/main.ftl key-for-key).
start-welcome = Добро пожаловать, { $name }! Нажмите кнопку ниже, чтобы открыть Smart Accounting Hub.
open-app-button = Открыть Smart Accounting
card-greeting = Привет, { $name }, книга «{ $book }»
error-auth = Ошибка авторизации. Пожалуйста, откройте приложение снова.

# --- общие кнопки ---
btn-confirm = ✅ Подтвердить
btn-back = ◀️ Назад
btn-cancel = ✖️ Отмена
btn-close = Закрыть
btn-accept = ✅ Присоединиться

# --- общие ошибки ---
error-no-book = Пока нет активной книги. Сначала отправьте /start.
error-generic = Что-то пошло не так ({ $code }).
error-bad-amount = Это не похоже на корректную сумму. Попробуйте ещё раз, например 1500.50

# --- роли ---
role-owner = владелец
role-admin = администратор
role-editor = редактор
role-viewer = наблюдатель

# --- создание книги ---
book-name-prompt = Как назвать новую книгу?
book-kind-prompt = Какого типа книга?
book-kind-personal = 👤 Личная
book-kind-family = 👨‍👩‍👧 Семейная
book-kind-business = 💼 Бизнес
book-currency-prompt = Базовая валюта? Отправьте 3-буквенный код, например USD.
book-confirm = Создать книгу «{ $name }» ({ $kind }), базовая валюта { $currency }?
book-created = 📗 Книга «{ $name }» создана и выбрана.

# --- создание счёта ---
account-currency-prompt = Какая валюта? Отправьте 3-буквенный код, например USD.
account-kind-prompt = Какой тип счёта?
account-kind-cash = 💵 Наличные
account-kind-bank = 🏦 Банк
account-kind-card = 💳 Карта
account-kind-brokerage = 📈 Брокерский
account-kind-other = 📦 Другое
account-name-prompt = Название счёта?
account-opening-prompt = Начальный баланс? Отправьте число, например 500 (или 0).
account-confirm = Создать счёт { $currency } «{ $name }» ({ $kind }), начальный баланс { $opening }?
account-created = 💰 Счёт «{ $name }» создан с балансом { $balance }.

# --- присоединение по приглашению ---
invite-confirm = Присоединиться к книге «{ $book }» как { $role }?
invite-joined = 🤝 Вы присоединились к «{ $book }».
invite-unavailable = Это приглашение нельзя использовать ({ $reason }).

# --- переключение книг ---
books-prompt = Выберите книгу для переключения:
books-row = { $name } ({ $role })
books-switched = 📖 Переключено на «{ $name }».
