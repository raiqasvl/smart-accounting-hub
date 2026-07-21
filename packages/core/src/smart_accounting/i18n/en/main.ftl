# English Fluent translations for the bot.
start-welcome = Welcome, { $name }! Tap the button below to open Smart Accounting Hub.
open-app-button = Open Smart Accounting
card-greeting = Hello { $name }, book "{ $book }"
error-auth = Authentication failed. Please open the app again.

# --- shared buttons ---
btn-confirm = ✅ Confirm
btn-back = ◀️ Back
btn-cancel = ✖️ Cancel
btn-close = Close
btn-accept = ✅ Join

# --- shared errors ---
error-no-book = No active book yet. Send /start first.
error-generic = Something went wrong ({ $code }).
error-bad-amount = That doesn't look like a valid amount. Try again, e.g. 1500.50

# --- roles ---
role-owner = owner
role-admin = admin
role-editor = editor
role-viewer = viewer

# --- create book ---
book-name-prompt = What should the new book be called?
book-kind-prompt = What kind of book is it?
book-kind-personal = 👤 Personal
book-kind-family = 👨‍👩‍👧 Family
book-kind-business = 💼 Business
book-currency-prompt = Base currency? Send a 3-letter code, e.g. USD.
book-confirm = Create book "{ $name }" ({ $kind }), base currency { $currency }?
book-created = 📗 Book "{ $name }" created and selected.

# --- create account ---
account-currency-prompt = Which currency? Send a 3-letter code, e.g. USD.
account-kind-prompt = What kind of account?
account-kind-cash = 💵 Cash
account-kind-bank = 🏦 Bank
account-kind-card = 💳 Card
account-kind-brokerage = 📈 Brokerage
account-kind-other = 📦 Other
account-name-prompt = Name for the account?
account-opening-prompt = Opening balance? Send a number, e.g. 500 (or 0).
account-confirm = Create { $currency } account "{ $name }" ({ $kind }), opening { $opening }?
account-created = 💰 Account "{ $name }" created with balance { $balance }.

# --- join via invite ---
invite-confirm = Join book "{ $book }" as { $role }?
invite-joined = 🤝 You joined "{ $book }".
invite-unavailable = This invite can't be used ({ $reason }).

# --- books switcher ---
books-prompt = Pick a book to switch to:
books-row = { $name } ({ $role })
books-switched = 📖 Switched to "{ $name }".
