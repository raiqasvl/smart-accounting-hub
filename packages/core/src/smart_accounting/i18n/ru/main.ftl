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

# --- запись сделки (M3) ---
trade-direction-prompt = Вы покупаете или продаёте?
trade-dir-sell = 🔻 Продажа
trade-dir-buy = 🔺 Покупка
trade-quote-prompt = Какую валюту торгуете? Выберите:
trade-amount-prompt = Сколько { $quote } в сделке? например 1000
trade-rate-prompt = Курс — { $base } за 1 { $quote }? (рыночная подсказка: { $hint }) например 90.3
trade-confirm = { $direction } { $amount } { $quote } по { $rate } { $base }/{ $quote }?
trade-recorded = ✅ Сделка записана. Сумма в базовой валюте: { $base }.

# --- средневзвешенный курс (M3) ---
avg-direction-prompt = Сторона: покупка или продажа?
avg-quote-prompt = Какая валюта?
avg-period-prompt = За какой период?
avg-period-30d = Последние 30 дней
avg-period-month = Этот месяц
avg-period-all = Всё время
avg-result = Средневзвеш. { $direction } { $quote }: { $rate } ({ $count } сделок, { $total } { $quote })
avg-empty = Пока нет сделок { $direction } { $quote } за этот период.
