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
btn-skip = Skip

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

# --- record trade (M3) ---
trade-direction-prompt = Are you buying or selling?
trade-dir-sell = 🔻 Sell
trade-dir-buy = 🔺 Buy
trade-quote-prompt = Which currency are you trading? Pick one:
trade-amount-prompt = How much { $quote } is in the trade? e.g. 1000
trade-rate-prompt = Rate — { $base } per 1 { $quote }? (market hint: { $hint }) e.g. 90.3
trade-confirm = { $direction } { $amount } { $quote } at { $rate } { $base }/{ $quote }?
trade-recorded = ✅ Trade recorded. Base amount: { $base }.

# --- weighted-average report (M3) ---
avg-direction-prompt = Buy or sell side?
avg-quote-prompt = Which currency?
avg-period-prompt = Over what period?
avg-period-30d = Last 30 days
avg-period-month = This month
avg-period-all = All time
avg-result = Weighted avg { $direction } { $quote }: { $rate } ({ $count } trades, { $total } { $quote })
avg-empty = No { $direction } { $quote } trades in that period yet.

# --- categories (M4) ---
trade-category-prompt = Category? Pick one or skip.
category-none = (no category)

# --- internal transfer (M4) ---
transfer-from-prompt = Move money from which account?
transfer-to-prompt = Move it to which account? (showing { $currency } accounts)
transfer-amount-prompt = How much { $currency }? e.g. 250
transfer-confirm = Move { $amount } { $currency } from "{ $source }" to "{ $target }"?
transfer-done = 🔁 Moved { $amount } { $currency } to "{ $target }".
