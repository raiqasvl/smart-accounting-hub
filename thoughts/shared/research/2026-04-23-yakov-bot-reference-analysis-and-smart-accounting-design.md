# Reference Bot Analysis + Smart Accounting Hub Design Research

**Date:** 2026-04-23
**Author:** Claude (Opus 4.7, 1M ctx) via `/ralph_research` (adapted — no Linear)
**Scope:** Deep reverse-engineering of the reference bot at
`research/Yakov_tg_bot/`, gap analysis against user requirements, and an
opinionated set of stack/architecture options for the new **Smart Accounting
Hub** bot + Telegram Mini App.
**Status:** Research complete — initial intake locked (see §0.3); ready
for planning.

---

## 0. Executive Summary

### 0.1 The Critical Finding — The Reference Bot Is Not What You Think It Is

> **The `Yakov_tg_bot` reference has no FX/currency transaction tracking and
> no statement feature at all.** It has zero accounting domain logic.
> The "statement without an average rate" you described cannot have come
> from this codebase.

What the reference actually is: a **Ukrainian-language personal assistant
bot** (by `github.com/yakov-bakhmatov`-style naming — actually
`github.com/Yevhenii...`, exact owner irrelevant) that exposes:

1. Weather forecast (`/weather`) — screenshot of sinoptik.ua + OWM fallback
2. **Live** crypto prices (`/crypto`) — CoinMarketCap + owner-only Binance
3. **Live** FX rates (`/currency`) — scrapes minfin.com.ua + PrivatBank API
4. Russian military casualty scraper (`/ruloss`)
5. Free-text UAH↔USD converter
6. Date-difference calculator
7. Daily repeat-action scheduler (`/rep_action`) — re-fires any of 1–4 at
   a chosen `HH:MM`
8. Settings ConversationHandler (`/settings`) — city, timezone, watchlists
9. Feedback + owner-reply flow
10. Telegram Payments sandbox "tip the dev" (`/tip_developer`)
11. Owner-only broadcast (`/message_users`)

There is **no** place where a user records "sold 1000 USD at 90.0"; no table
for transactions; no aggregation query anywhere in the CRUD layer; no
statement-building function. What you are calling "a statement" is most
likely the output of `/currency` — a block of current scraped buy/sell
rates from minfin / PrivatBank. See
[src/utils/currency_utils.py:11-35](research/Yakov_tg_bot/src/utils/currency_utils.py#L11-L35).

**Implication:** you are not adding one feature to a bot that already
tracks transactions. You are building an accounting bot from scratch, and
the reference is useful chiefly for:

- Framework scaffolding patterns (python-telegram-bot v20 async +
  SQLAlchemy async + Alembic + Postgres + Docker Compose)
- External-integration patterns (scraping, API clients, error classes)
- Example ConversationHandler state machines
- A baseline DB schema for users, preferences, watchlists

If the user is actually referring to **a different** reference bot, we need
its repo/username to analyze it — please confirm. The rest of this
document assumes the Yakov bot is a **structural** reference only.

### 0.2 Top-Line Recommendations

1. **Start fresh**, do not fork the Yakov codebase. Borrow patterns, not
   code. The Yakov code has zero tests, synchronous `requests` inside async
   handlers (blocks the event loop), outdated pins (2023), hardcoded
   Ukrainian UI strings, and no typed config.
2. **Python 3.12+ / FastAPI + aiogram 3 / SQLAlchemy 2.x async + Postgres
   + Redis** for the backend bot + Mini App API. See §5 for rationale and
   alternatives.
3. **Telegram Mini App** (WebApp) built with **Next.js 15 + TypeScript**
   served from the same backend container or a separate static origin,
   authenticated via `initData` HMAC — see §6.
4. Domain model starts with:
   `users, accounts, currencies, fx_transactions, categories, tags,
    rates_snapshot` — see §4 for full ERD.
5. Ship the weighted-average-rate view (`SUM(amount*rate)/SUM(amount)`,
   grouped per user × currency × direction) as a first-class feature:
   both as bot command `/avg` and as a Mini App dashboard card.
6. Treat this as **two products in one repo** (monorepo): `bot/` +
   `miniapp/` + `shared/`. Turborepo or plain pnpm workspaces + Poetry /
   uv for Python.

### 0.3 Locked Decisions (2026-04-23 intake)

These were confirmed by the user in chat after the initial draft of this
document. They override anything in §3, §4, §5, §6, §7 below where there
is a conflict; the body of the document remains as-is for context.

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| D1 | Reference bot identity | **Resolved (2026-04-23 follow-up):** Yakov is the *structural* reference only. The new product is built from scratch and the explicit goal is *"made something better"*. | Proceed as in §0.1 — borrow patterns (FSM scaffolding, exception classes, `BOT_COMMANDS` registry, freetext converter UX) but write our own code. |
| D2 | Audience scope | **Resolved (2026-04-23 follow-up):** **Both** family **and** business books at MVP. | Schema is **book-scoped** (see §4). `books.kind ∈ {personal, family, business}`. Role matrix in §4.0.1 applies to all kinds; business-specific affordances (e.g., richer audit log, multi-seat invoicing) deferred to Phase 2. Bot UX needs a "current book" concept and a quick book switcher. |
| D3 | Languages at launch | **EN + RU** (no UA at launch, despite Yakov being UA). | All seed strings + UI strings in EN/RU. `users.language` enum: `en` or `ru` only. `currencies` table localized name columns: drop `name_uk`, keep `name_en` + `name_ru`. Category seeds in EN+RU. |
| D4 | Primary market | **Multi-market** (not UAH-centric). | Default base currency per book is user-selectable, not hard-coded UAH. Rate sources prioritized: ECB (broad fiat), Open Exchange Rates / Frankfurter (fallback), CoinGecko (crypto). NBU/PrivatBank become optional regional sources, not the spine. |
| D5 | Monetization & timeline | **Undefined ("idk")** — defer. | No paywall in MVP. Build with the *option* of subscription/seat-based pricing (per-book seat counts) without committing to it; do not architect around free-only. |
| D6 | Package manager | **pnpm** | Locks `pnpm-workspace.yaml`. CI uses `pnpm install --frozen-lockfile`. |
| D7 | Repo architecture | **Turborepo** monorepo | Adds `turbo.json` with `dev`, `build`, `test`, `lint`, `typecheck` pipelines. Affected-graph caching for CI. |
| D8 | Backend stack | Python 3.12+, **aiogram 3.x**, **FastAPI**, **SQLAlchemy 2.x async + asyncpg + PostgreSQL 16**, **Alembic** (committed migrations), **Redis 7**, **arq** | Locked. |
| D9 | Frontend stack | **Next.js 15 (App Router)** + **TypeScript** + **TanStack Query** + **shadcn/ui + Tailwind** + **Recharts** | Locked. Mini App served at a public HTTPS origin behind the team's reverse proxy. |
| D10 | Deployment | **`docker-compose` on the user's own server** | No Fly.io / Railway / Hetzner-managed in this round. Need: TLS termination (Caddy or Nginx + certbot), backups (pg_dump cron + offsite), basic monitoring (uptime + logs). systemd unit similar to `tg_bot.service` is acceptable for boot. Single-host MVP; multi-host out of scope. |

**Status:** D1 and D2 resolved 2026-04-23. The blocking design questions are
all settled — the plan document can start. Three lower-impact items remain
open in §7.2 (cash/bank granularity, bank-statement import sources, MVP
timeline) but none of them block planning.

---

## 1. Reference Bot — Architecture Inventory

All file paths in this section are relative to
`research/Yakov_tg_bot/`.

### 1.1 Tech stack (as shipped)

| Layer | Choice | Notes |
|-------|--------|-------|
| Runtime | Python 3.11 (Dockerfile) / 3.10+ per README | Pinned 2023 |
| Bot framework | `python-telegram-bot==20.6` (async) | Uses built-in `JobQueue` (wraps APScheduler) |
| ORM | `SQLAlchemy==2.0.22` async | `asyncpg` driver |
| Migrations | `alembic==1.12.1` async env | 6 revisions applied (per `initial_dump.sql`); source files not checked in |
| DB | PostgreSQL 15 (docker-compose) | `postgres:15-alpine` |
| Scheduler | PTB `JobQueue` | No standalone APScheduler instance despite `APScheduler` in `requirements.txt` |
| HTTP | `requests` (sync) everywhere | Blocks the asyncio loop during each call |
| HTML parsing | `beautifulsoup4` + `lxml` | For minfin.com.ua + index.minfin.com.ua |
| Crypto market data | `python-binance==1.0.19` (sync) + CoinMarketCap REST | Owner-only for Binance |
| Logging | `loguru==0.7.2` + stdlib intercept | Single stderr sink, no rotation |
| Deployment | Dockerfile + docker-compose + Heroku `Procfile` + systemd unit | Webhook path exists (Heroku); default is polling |
| Secrets | `.env` only | No vault, no secret manager |
| Tests | **none** | No `tests/`, no `pytest.ini` |
| CI/CD | **none** | No workflows, no linters, no pre-commit |

### 1.2 Repo layout

```
Yakov_tg_bot/
├── Dockerfile                 # python:3.11, CMD ["python3", "src/main.py"]
├── docker-compose.yaml        # postgres + tg-bot on `backend` net
├── Procfile                   # web: python src/main.py  (Heroku)
├── tg_bot.service             # systemd wrapping docker-compose
├── requirements.txt           # 2023-era pins
├── initial_dump.sql           # pg_dump: schema + seed data (alembic_version=0006)
├── alembic/                   # async env.py; versions/ not tracked in snapshot
├── alembic.ini                # sqlalchemy.url set from DB_URL at runtime
└── src/
    ├── main.py                # Application builder, handler registration, webhook-vs-polling switch
    ├── config.py              # Typed-ish Config class, loguru setup, BOT_COMMANDS registry
    ├── setup.py               # Runs `alembic upgrade head` then seeds Currency + CryptoCurrency
    ├── commands/              # 11 top-level command handlers (one file each)
    ├── handlers/              # error handler, catch-all, regex-matched freetext (UAH<->USD, date diff)
    ├── crud/                  # 6 files: user, city, currency, crypto_currency, feedback, repeated_action
    ├── models/
    │   ├── base.py            # shared MetaData + declarative_base
    │   ├── errors.py          # domain exception classes per integration
    │   └── tables/            # 9 ORM tables (see §1.4)
    └── utils/                 # db, env, time, message, currency, weather, binance, cmc, repeated_action
```

### 1.3 Application wiring — `src/main.py`

- [`main.py:34-39`](research/Yakov_tg_bot/src/main.py#L34-L39) builds the
  PTB `Application` with `defaults(Config.BOT_DEFAULTS)` (timezone
  `Europe/Kyiv`).
- [`main.py:42`](research/Yakov_tg_bot/src/main.py#L42) runs `check_db()`
  — a **sync** SQLAlchemy connect (`+asyncpg` stripped from the URL) that
  calls `sys.exit(1)` on failure.
- Handler registration order (lines 47–73): commands → freetext handlers
  → one-time startup job (`register_actions_callback`) → payments → global
  error handler → catch-all `filters.ALL`.
- Webhook vs polling:
  ```python
  if Config.WEBHOOK_FLAG:
      application.run_webhook(listen="0.0.0.0", port=Config.BOT_PORT,
                              webhook_url=Config.BOT_LINK)
  else:
      application.run_polling()
  ```
  Toggle via `WEBHOOK_FLAG` env (int cast to bool). Webhook mode
  explicitly documented in `config.py:38` as "Currently unsupported".

### 1.4 Data model (complete list)

9 tables — all of them are for **user identity, preferences, or
feedback**. There is **no transactional table**.

| Table | Purpose | Notable columns |
|-------|---------|-----------------|
| `user` | Telegram identity + prefs | `id` (Telegram ID, not autoinc), `city_id` FK, `timezone_offset`, `active`, `language_code` (stored, never read) |
| `city` | Resolved cities | `owm_id`, `lat/lon`, `sinoptik_url`, `timezone_offset` |
| `currency` | Fiat catalog | `name` (e.g. "usd"), `symbol` (emoji) |
| `currency_watchlist` | M:N user↔currency | composite PK |
| `crypto_currency` | CMC catalog | `id`=CMC id, `abbr` |
| `crypto_currency_watchlist` | M:N user↔crypto | composite PK |
| `feedback` | User messages to owner | `read_flag`, `timestamp` |
| `feedback_reply` | Owner reply messages | `feedback_id` FK |
| `repeated_action` | Daily scheduled action | `action` (string), `execution_time` (TIME) |

Seed data (from `initial_dump.sql` + `setup.py`):
- `currency`: usd(🇺🇸), eur(🇪🇺), pln(🇵🇱), gbp(🇬🇧) — **4 rows only**
- `crypto_currency`: BTC, ETH, BNB, SOL, XRP, DOGE — **6 rows only**

### 1.5 ConversationHandler patterns

Five `ConversationHandler` flows, all keyboard-driven (inline only, no
persistent reply keyboards):

- `/settings` — 5 states: SETTINGS_START, CITY_SETTINGS, TIMEZONE_SETTINGS,
  CRYPTO_SETTINGS, CURR_SETTINGS. Timeout 300s.
- `/feedback` — 1-shot text capture.
- `/reply_to_<id>` — owner-only reply flow with "confirm / edit / cancel".
- `/rep_action` — add / list / delete daily actions. Includes a ±30 min
  collision check.
- `/message_users` — owner broadcast with confirm/edit.

All share a module-level `cancel` / `cancel_keyboard` /
`cancel_back_keyboard` (`src/handlers/canel_conversation.py`) — a small
but clean reuse pattern worth copying.

### 1.6 Scheduling

- No standalone `AsyncIOScheduler`. Everything goes through PTB
  `application.job_queue` (which itself wraps APScheduler).
- On startup, `job_queue.run_once(register_actions_callback, when=1)` reads
  all rows from `repeated_action` and re-registers each as
  `run_daily(..., time=row.execution_time, chat_id=row.user_id,
  name=str(row.id))`. Source:
  [`src/utils/repeated_action_utils.py:34-42`](research/Yakov_tg_bot/src/utils/repeated_action_utils.py#L34-L42).
- User-triggered add/delete flows mutate both the DB and the live job
  queue ([`commands/repeated_action.py:296, 230-231`](research/Yakov_tg_bot/src/commands/repeated_action.py#L230-L296)).

### 1.7 External integrations (all **blocking** calls inside async)

| Source | Endpoint | Used by | Failure mode |
|--------|----------|---------|--------------|
| PrivatBank | `api.privatbank.ua/p24api/pubinfo?coursid={5,11}` | `/currency`, freetext converter | `Privat24APIError` → user-friendly reply |
| minfin.com.ua | HTML scrape `/ua/currency/` | `/currency`, freetext converter | `MinFinFetchError`, `MinFinParseError` |
| index.minfin.com.ua | HTML scrape `/ua/russian-invading/casualties/` | `/ruloss` | reply "Ситуація..." |
| OpenWeatherMap | `/geo/1.0/direct`, `/data/2.5/weather`, `/data/2.5/onecall` | `/weather`, `/settings` | `CityFetchError`, `WeatherFetchError` |
| Sinoptik | URL-validate only (HTTP 200 check) | `/settings` city setup | `SinoptikURLFetchError` |
| ScreenshotOne | `api.screenshotone.com/take` | `/weather` (primary) | falls through to OWM text |
| CoinMarketCap | `pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest` | `/crypto` | `None` → user reply |
| Binance | `python-binance` sync client | `/crypto` (owner only) | `BinanceAPIError` |

All of these are `requests.get(...)` — synchronous, blocking the event
loop during each request. This is a **known anti-pattern** in PTB async
applications and a direct thing we will **not** replicate.

### 1.8 Observability

- Loguru configured in `Config.__init__` / class body at
  [`config.py:70-98`](research/Yakov_tg_bot/src/config.py#L70-L98).
- Single stderr sink, **no rotation, no file sink**, no external log
  shipping.
- Stdlib `logging` is intercepted and piped into loguru via
  `InterceptLogsHandler`.
- The `error_handler`
  ([`handlers/error.py:17-72`](research/Yakov_tg_bot/src/handlers/error.py#L17-L72))
  DMs the full traceback to `OWNER_ID` as three Markdown code blocks.
  Useful in dev, **not acceptable in production** — any user input that
  triggers an exception leaks into the owner's chat.

### 1.9 Environment variables (17 total)

Full list preserved in the data-layer/infra agent report (see
[`.env.example`](research/Yakov_tg_bot/.env.example)). Highlights:
`BOT_TOKEN, OWNER_ID, CMC_API_TOKEN, SCREENSHOT_API_TOKEN, OWM_API_TOKEN,
BINANCE_API_TOKEN, BINANCE_API_PRIVAT_TOKEN, DB_URL, DEBUG_FLAG,
WEBHOOK_FLAG, BOT_LINK, PORT, DEVELOPER_GH_PROFILE, BOT_GH_REPO`.

Notable hardcoded values: `CREATOR_ID = 514328460` and a **sandbox
Telegram Payments provider token** `'632593626:TEST:sandbox_i29859238551'`
are committed as literals in `config.py` / `commands/tips.py`.

---

## 2. The "Average Rate" Gap — Re-framed

### 2.1 What the feature *would have to do*

Given N transactions in a given currency, with amount `a_i` and rate
`r_i`, output the weighted average rate:

```
avg_rate = Σ(a_i * r_i) / Σ(a_i)
```

Separately per direction (buy vs sell) and/or per counter-currency pair,
with optional filters (date range, counter-account, tag, category).

### 2.2 Why the reference cannot do it

- No `transactions` (or equivalent) table exists
  ([`src/models/tables/`](research/Yakov_tg_bot/src/models/tables/))
- No CRUD function aggregates anything
  ([`src/crud/`](research/Yakov_tg_bot/src/crud/) — no `SUM`, no `AVG`,
  no `GROUP BY` in any file)
- `/currency` reads live external rates; it never touches user data
  ([`src/commands/currency.py:33-39`](research/Yakov_tg_bot/src/commands/currency.py#L33-L39)).

### 2.3 What "a statement" probably was (hypothesis)

The most likely candidate for what the user remembers as a "statement" is
either:

1. The output of `/currency` (a live-rates snapshot) — it renders nicely
   and can be mistaken for a statement.
2. The **Binance funding wallet summary** (owner-only, not visible to
   users) which iterates coin balances, multiplies by USDT price, and
   totals.
   [`utils/binance_utils.py:25-48`](research/Yakov_tg_bot/src/utils/binance_utils.py#L25-L48)
3. A **different bot** altogether (please confirm).

### 2.4 Recommended first-class features for the new product

- Log a transaction in ≤3 taps from the Mini App:
  `direction | amount | rate | counter-account | date | note/tags`.
- Per-currency weighted-average rate, with direction filter.
- Per-currency P&L vs current market rate (pulls live rate from NBU or
  user-configured source).
- Per-pair history (e.g. UAH↔USD) with rolling 7/30/90-day average.
- CSV / XLSX / PDF export.

---

## 3. Proposed Product Scope

The goal is a **Smart Accounting Hub** — positioned to beat the reference
not by having more features in the same category, but by actually solving
the accounting problem the reference doesn't even attempt.

### 3.1 MVP (Phase 1)

1. Onboarding via bot `/start`, Telegram-identity-based auth.
2. Multi-account support: a user can have `cash`, `bank`, `card`,
   `crypto-exchange` accounts, each in a specific currency.
3. FX transactions: user records either `FX_BUY` or `FX_SELL` between
   two accounts at a given rate on a given date. The `amount` is in the
   source currency; `rate` is expressed per user convention (e.g. UAH/USD).
4. **Weighted-average rate** view — the differentiating feature.
5. Monthly statement per account / per currency.
6. Settings: base currency, default rate source, timezone, language
   (UA/EN/RU at minimum).

### 3.2 Phase 2 (What makes it "superior and unique")

- **Telegram Mini App** as the primary UI. Bot remains for quick-add
  (typing `+100 USD at 40.5` as a freetext shortcut — inspired by the
  Yakov inline converter pattern at
  [`handlers/currency_converter.py:10-11`](research/Yakov_tg_bot/src/handlers/currency_converter.py#L10-L11))
  and notifications.
- **Categorization** of transactions (income / expense / transfer /
  investment), tags, and sub-category rules.
- **Budgets & envelopes** per category × month, with progress bars.
- **Live rate integration** from multiple sources (NBU, ECB, monobank,
  PrivatBank, Binance) — cache in Redis with TTL, serve to the mini app.
- **Rate-alert subscriptions** ("tell me when USD > 42"), reusing the
  `repeated_action` pattern but event-based via Celery / arq / FastAPI
  background tasks.
- **OCR-based receipt import** (Telegram photo → parsed receipt → one-tap
  confirm).
- **LLM-assisted categorization** of free-text notes.
- **Export**: CSV / XLSX / 1C exchange format / Google Sheets sync.
- **Shared books** (two users can own a joint "family" book).
- **Charts & dashboards** in the mini app: pie by category, line of
  balance over time, FX P&L, candlestick on your personal rate history
  overlaid with NBU.

### 3.3 Phase 3 (stretch, only if Phase 1+2 land)

- Open-banking imports (monobank, PrivatBank, revolut) where APIs exist.
- End-to-end encryption of notes and amounts (client-side key, derived
  from Telegram WebApp `initData`).
- Small B2B pivot — a business can use "books" for simple bookkeeping.

---

## 4. Proposed Domain Model (First Cut)

Textual ERD. All monetary amounts are `NUMERIC(20, 8)` — never `FLOAT`.
All monetary rows carry their own currency; there is no implicit base
currency.

> **Updated by D2 (2026-04-23 intake):** the schema is now **book-scoped**,
> not user-scoped. A `book` is the unit of ownership for accounts /
> transactions / categories / tags. Users join books via `book_members`
> with roles. A user has a `default_book_id` so the bot/mini-app can land
> them in their last-used book.
>
> The pre-D2 schema (in earlier drafts) had `user_id` on `accounts`,
> `transactions`, etc. Those are replaced by `book_id` below; ownership
> of the book is tracked in `books.owner_id` / `book_members.role`.

```
users
  id BIGINT PRIMARY KEY                  -- = telegram.User.id
  tg_username VARCHAR(64) NULL
  tg_first_name VARCHAR(64) NOT NULL
  tg_last_name  VARCHAR(64) NULL
  language CHAR(2) NOT NULL DEFAULT 'en' -- en | ru   (D3)
  timezone_offset INT NOT NULL DEFAULT 0
  default_book_id BIGINT NULL REFERENCES books(id) ON DELETE SET NULL
  is_active BOOLEAN NOT NULL DEFAULT TRUE
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()

books                                    -- D2: ownership unit
  id BIGSERIAL PRIMARY KEY
  owner_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE
  name TEXT NOT NULL
  kind TEXT NOT NULL                     -- personal | family | business
  base_currency_code CHAR(3) NOT NULL REFERENCES currencies(code)   -- D4: per-book, no global default
  default_language CHAR(2) NOT NULL DEFAULT 'en'                    -- en | ru
  archived BOOLEAN NOT NULL DEFAULT FALSE
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
  INDEX (owner_id)

book_members                             -- D2: role-based access
  book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE
  role TEXT NOT NULL                     -- owner | admin | editor | viewer
  invited_at TIMESTAMPTZ NOT NULL DEFAULT now()
  accepted_at TIMESTAMPTZ NULL
  PRIMARY KEY (book_id, user_id)
  INDEX (user_id)

book_invites                             -- D2: deep-link invitations
  id BIGSERIAL PRIMARY KEY
  book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE
  invited_by BIGINT NOT NULL REFERENCES users(id)
  token TEXT NOT NULL UNIQUE             -- short, deep-link friendly
  role TEXT NOT NULL                     -- admin | editor | viewer
  expires_at TIMESTAMPTZ NOT NULL
  consumed_by BIGINT NULL REFERENCES users(id)
  consumed_at TIMESTAMPTZ NULL
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()

currencies
  code CHAR(3) PRIMARY KEY               -- ISO 4217 where possible, plus 'USDT', 'BTC'
  kind TEXT NOT NULL                     -- fiat | crypto
  symbol VARCHAR(8) NOT NULL
  decimals SMALLINT NOT NULL DEFAULT 2
  name_en TEXT NOT NULL
  name_ru TEXT NOT NULL                  -- D3: drop name_uk

accounts
  id BIGSERIAL PRIMARY KEY
  book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE   -- D2: book-scoped
  name TEXT NOT NULL
  currency_code CHAR(3) NOT NULL REFERENCES currencies(code)
  kind TEXT NOT NULL                     -- cash | bank | card | crypto | other
  opening_balance NUMERIC(20,8) NOT NULL DEFAULT 0
  archived BOOLEAN NOT NULL DEFAULT FALSE
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  UNIQUE(book_id, name)
  INDEX (book_id, archived)

fx_transactions                          -- the core aggregatable table
  id BIGSERIAL PRIMARY KEY
  book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE   -- D2
  created_by_user_id BIGINT NOT NULL REFERENCES users(id)          -- audit
  direction TEXT NOT NULL                -- buy | sell
  -- "Bought 1000 USD for UAH at 40.50" →
  --   base_account = UAH account (money left), quote_account = USD account (money arrived),
  --   base_currency_code='UAH', quote_currency_code='USD',
  --   amount_quote=1000, rate=40.50, amount_base=40500 (derived, stored for audit/speed)
  base_account_id  BIGINT NOT NULL REFERENCES accounts(id)
  quote_account_id BIGINT NOT NULL REFERENCES accounts(id)
  base_currency_code  CHAR(3) NOT NULL REFERENCES currencies(code)
  quote_currency_code CHAR(3) NOT NULL REFERENCES currencies(code)
  amount_quote NUMERIC(20,8) NOT NULL CHECK (amount_quote > 0)
  rate         NUMERIC(20,8) NOT NULL CHECK (rate > 0)
  amount_base  NUMERIC(20,8) NOT NULL CHECK (amount_base > 0)
  fee          NUMERIC(20,8) NOT NULL DEFAULT 0
  fee_currency_code CHAR(3) NULL REFERENCES currencies(code)
  occurred_at TIMESTAMPTZ NOT NULL
  note TEXT NULL
  source TEXT NOT NULL DEFAULT 'manual'  -- manual | import | ocr | api
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
  CHECK (base_currency_code <> quote_currency_code)
  INDEX (book_id, occurred_at DESC)
  INDEX (book_id, quote_currency_code, direction, occurred_at DESC)

transactions                             -- non-FX income/expense/transfer
  id BIGSERIAL PRIMARY KEY
  book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE   -- D2
  created_by_user_id BIGINT NOT NULL REFERENCES users(id)          -- audit
  account_id BIGINT NOT NULL REFERENCES accounts(id)
  counter_account_id BIGINT NULL REFERENCES accounts(id)           -- transfers
  kind TEXT NOT NULL                     -- income | expense | transfer | adjustment
  category_id BIGINT NULL REFERENCES categories(id)
  amount NUMERIC(20,8) NOT NULL CHECK (amount <> 0)
  currency_code CHAR(3) NOT NULL REFERENCES currencies(code)
  occurred_at TIMESTAMPTZ NOT NULL
  note TEXT NULL
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
  INDEX (book_id, occurred_at DESC)

categories
  id BIGSERIAL PRIMARY KEY
  book_id BIGINT NULL REFERENCES books(id) ON DELETE CASCADE       -- NULL = system catalog
  parent_id BIGINT NULL REFERENCES categories(id)
  kind TEXT NOT NULL                     -- income | expense
  slug TEXT NOT NULL
  name_en TEXT NOT NULL
  name_ru TEXT NOT NULL                  -- D3
  emoji TEXT NULL
  UNIQUE(book_id, slug)

tags
  id BIGSERIAL PRIMARY KEY
  book_id BIGINT NOT NULL REFERENCES books(id) ON DELETE CASCADE   -- D2
  name TEXT NOT NULL
  UNIQUE(book_id, name)

transaction_tags
  transaction_id BIGINT REFERENCES transactions(id) ON DELETE CASCADE
  tag_id         BIGINT REFERENCES tags(id)         ON DELETE CASCADE
  PRIMARY KEY(transaction_id, tag_id)

fx_transaction_tags
  fx_transaction_id BIGINT REFERENCES fx_transactions(id) ON DELETE CASCADE
  tag_id            BIGINT REFERENCES tags(id)            ON DELETE CASCADE
  PRIMARY KEY(fx_transaction_id, tag_id)

rate_snapshots                           -- periodic cache of external rates
  id BIGSERIAL PRIMARY KEY
  source TEXT NOT NULL                   -- D4: ecb | openexchangerates | frankfurter | coingecko | nbu | privat24 | binance
  base_currency_code  CHAR(3) NOT NULL
  quote_currency_code CHAR(3) NOT NULL
  buy  NUMERIC(20,8) NULL
  sell NUMERIC(20,8) NULL
  mid  NUMERIC(20,8) NULL                -- some sources give a single mid rate
  fetched_at TIMESTAMPTZ NOT NULL
  UNIQUE(source, base_currency_code, quote_currency_code, fetched_at)
  INDEX (source, base_currency_code, quote_currency_code, fetched_at DESC)

rate_alerts
  id BIGSERIAL PRIMARY KEY
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE   -- alerts are personal, not book-scoped
  base_currency_code CHAR(3) NOT NULL
  quote_currency_code CHAR(3) NOT NULL
  operator TEXT NOT NULL                 -- gt | lt | gte | lte
  threshold NUMERIC(20,8) NOT NULL
  source TEXT NOT NULL
  active BOOLEAN NOT NULL DEFAULT TRUE
  last_fired_at TIMESTAMPTZ NULL
```

### 4.0.1 Role matrix (D2)

| Role | View | Create txn | Edit/del txn | Manage accounts/categories | Invite members | Delete book |
|------|------|------------|--------------|----------------------------|----------------|-------------|
| owner  | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| admin  | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| editor | ✓ | ✓ | ✓ (own only) | — | — | — |
| viewer | ✓ | — | — | — | — | — |

### 4.1 The weighted-average-rate query

```sql
-- params:
--   $1 = book_id
--   $2 = optional start (inclusive), NULL = no lower bound
--   $3 = optional end   (exclusive), NULL = no upper bound
SELECT
  quote_currency_code AS currency,
  direction,
  SUM(amount_quote)                           AS total_amount,
  SUM(amount_quote * rate) / SUM(amount_quote) AS weighted_avg_rate
FROM fx_transactions
WHERE book_id = $1
  AND ($2::timestamptz IS NULL OR occurred_at >= $2)
  AND ($3::timestamptz IS NULL OR occurred_at <  $3)
GROUP BY quote_currency_code, direction
ORDER BY quote_currency_code, direction;
```

Authorization is enforced **before** this query: the API resolves the
caller's `book_id` from the path/JWT claim and verifies a row in
`book_members(book_id, user_id)` with role ≥ `viewer`. The covering index
`(book_id, quote_currency_code, direction, occurred_at DESC)` makes this a
single indexed aggregate, fast enough for interactive use. If volumes grow,
cover with a daily materialized view `mv_daily_fx_avg` keyed by
`(book_id, quote_currency_code, direction, day)`.

---

## 5. Recommended Technical Stack

I'll list **recommended** and **alternatives with rationale**. No single
"right answer" — this section is the tradeoff menu.

### 5.1 Bot framework

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **aiogram 3.x** | Idiomatic async, clean DI, FSM, filters are typed, excellent docs, active project | Smaller ecosystem than PTB | ✅ **Recommended** |
| python-telegram-bot 21.x | Familiar (reference uses it); builtin JobQueue | `ConversationHandler` is awkward for complex flows; `Application` monolith | Acceptable fallback |
| pyrogram / telethon | Full MTProto (userbot capability) | Overkill for a bot; different auth model | ❌ No |
| grammY (TypeScript) | Excellent if you wanted to unify with the Mini App | Forces whole bot to TS; harder numeric/DB story | Only if you want TS bot |

**Rationale:** aiogram 3 models callback_data with typed classes, has
first-class FSM storage backed by Redis, and supports Telegram WebApp
integration out of the box. The Yakov bot's ConversationHandler state
explosion (see §1.5) is exactly what FSM cleans up.

### 5.2 Backend web API (for the Mini App)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **FastAPI** | Pydantic v2, async-native, auto OpenAPI, lines up 1:1 with aiogram stack | — | ✅ **Recommended** |
| Litestar | Newer, even more modular | Smaller community | Fine alternative |
| Django + DRF + Ninja | "Batteries" incl. admin | Async story is still mixed | Only if you want Django admin |

### 5.3 Persistence

- **PostgreSQL 16+** — Numeric math, partial indexes, materialized views,
  JSONB for flexible per-user settings.
- **SQLAlchemy 2.x async + asyncpg** — same stack the reference uses.
  2.x style (`select()`/`Mapped[…]` declarative). No ORM scope-creep:
  write aggregate queries in explicit SQL.
- **Alembic** with **autogenerate reviewed manually**. The Yakov repo
  stores only `initial_dump.sql`, not migration files — do not copy that
  practice; commit migrations.
- **Redis 7** — FSM state, rate-snapshot cache, rate-limiting, Celery/arq
  broker.

### 5.4 Background jobs

- **arq** (lightweight, aiogram/FastAPI-friendly, Redis-backed) for:
  periodic rate fetching, rate-alert dispatch, OCR, email/export.
- Alternative: **Celery** if you foresee heterogeneous workers or pre-fork
  CPU workloads (PDF/OCR).
- Avoid building on PTB's `JobQueue` (as Yakov does) — it couples
  scheduling to the bot process and dies on restart unless re-registered
  (see
  [`utils/repeated_action_utils.py:34-42`](research/Yakov_tg_bot/src/utils/repeated_action_utils.py#L34-L42)).

### 5.5 Mini App (frontend)

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Next.js 15 (App Router) + TS + TanStack Query** | Full RSC/SSR, great DX, easy Telegram `initData` auth on route handlers | SSR is overkill for a mini app served inside Telegram | ✅ **Recommended** — use `output: 'export'` or `app router` with SSR off for mini app |
| Vite + React + TanStack Query | Simpler, smaller bundle | Have to wire routing yourself | Fine for lean team |
| SvelteKit | Smaller bundles, great TTI | Smaller ecosystem | Only if team prefers Svelte |

Use the [`@twa-dev/sdk`](https://github.com/twa-dev/SDK) wrapper for
Telegram WebApp JS, and verify `initData` on the backend (HMAC-SHA256 of
`data_check_string` keyed by bot token). Issue an httpOnly JWT after
verification.

### 5.6 UI kit

- **shadcn/ui + Tailwind** — high iteration velocity, matches Telegram's
  native dark/light theming via CSS variables; the Telegram WebApp object
  exposes `themeParams` we can map directly to shadcn tokens.
- Charts: **Recharts** or **ECharts**. Recharts is friendlier on RSC;
  ECharts has better finance primitives (candlesticks). We can start with
  Recharts and swap as needed.

### 5.7 Observability & quality

- **structlog** (or `loguru`, if you prefer the reference's choice) with
  JSON logs to stdout; ship via Vector/Fluent Bit to whichever destination.
- **Sentry** for both Python and JS — free tier is enough at start.
- **pytest + pytest-asyncio + respx + factory-boy** for backend; **Vitest
  + Playwright** for frontend.
- **ruff (lint + format)** + **mypy strict** (or pyright) on Python.
  **Biome** or **eslint + prettier** for TS.
- **pre-commit** gating `ruff`, `mypy --strict`, `eslint`, `prettier`,
  `sqlfluff`.

### 5.8 Deployment (D10: docker-compose on user's own server)

- **Single docker-compose.yml** for both dev and prod (with overrides via
  `docker-compose.prod.yml`).
- Services: `postgres` + `redis` + `backend` (FastAPI + aiogram in one
  container; webhook mode in prod) + `worker` (arq) + `miniapp` (Next.js
  standalone build) + `caddy` (TLS termination + reverse proxy +
  automatic Let's Encrypt).
- Bind volumes for: `pgdata`, `redisdata`, `caddy_data` (cert cache),
  `caddy_config`, `backend_logs`.
- **Boot**: `systemd` unit similar to the reference's
  [`tg_bot.service`](research/Yakov_tg_bot/tg_bot.service) — `Restart=always`,
  `ExecStart=docker compose -f /srv/sah/docker-compose.yml up -d`,
  `ExecStop=docker compose -f /srv/sah/docker-compose.yml stop`. Use
  `User=deploy` (not `root`).
- **Backups**: nightly `pg_dump --format=custom` cron writing to
  `/srv/sah/backups/`, mirrored to an offsite store (rclone → S3 / B2 /
  Backblaze) with a 30-day retention.
- **Monitoring**: Sentry (Python + JS) for errors. Uptime: lightweight
  external probe (UptimeRobot / better-stack free tier) hitting
  `/healthz`. Dashboards: optional `grafana + prometheus + node_exporter`
  in a second compose file if you want host metrics.
- **Logs**: `docker compose logs` is fine to start; promote to Loki +
  Promtail or a simple `journalctl`-shipped aggregator if volume warrants.
- **Webhook in prod**, polling in dev. The webhook URL is a Caddy
  reverse-proxy route to `backend:8000/webhook/<secret_path>`.

> Cloud-hosted alternatives (Fly.io / Railway / Hetzner-managed) are
> explicitly **out of scope** per D10. The doc keeps them in earlier drafts
> for context only — do not pursue them.

---

## 6. Repository Organization (Proposed) — D6 + D7

Locked: **pnpm** as JS package manager, **Turborepo** as the monorepo
build/cache orchestrator. Python lives outside the Turborepo task graph
(it has its own toolchain) but the root `turbo.json` exposes
`backend:dev` / `backend:test` as passthrough tasks so `pnpm dev` /
`pnpm test` boots/tests everything.

```
smart-accounting-hub/
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       ├── backend.yml         # ruff + mypy + pytest
│       ├── frontend.yml        # biome + vitest + typecheck
│       └── e2e.yml             # playwright in Docker
├── docker-compose.yml          # postgres + redis + backend + worker + miniapp + caddy  (D10)
├── docker-compose.prod.yml     # prod overrides: webhook envs, no source mounts, prod build targets
├── Caddyfile                   # TLS + reverse proxy, mini-app at https://app.example.com, webhook at https://api.example.com
├── CLAUDE.md                   # existing
├── README.md                   # existing
├── turbo.json                  # D7: pipelines (build, dev, test, lint, typecheck) with affected-graph cache
├── pnpm-workspace.yaml         # D6: pnpm workspaces — packages: ['miniapp', 'shared/*']
├── package.json                # root scripts only (turbo run dev/build/test/...)
├── pyproject.toml              # uv workspace root for backend/
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/versions/       # COMMITTED migration files
│   ├── src/
│   │   ├── app/
│   │   │   ├── main.py         # FastAPI + aiogram entrypoints
│   │   │   ├── config.py       # pydantic-settings
│   │   │   ├── db.py           # engine/session factories
│   │   │   ├── deps.py
│   │   │   ├── domain/         # pure-Python domain types (no ORM here)
│   │   │   ├── models/         # SQLAlchemy ORM
│   │   │   ├── repos/          # async repositories
│   │   │   ├── services/       # use-cases (e.g. record_fx_transaction)
│   │   │   ├── api/            # FastAPI routers (/miniapp/**, /webhook/**)
│   │   │   ├── bot/
│   │   │   │   ├── dispatcher.py
│   │   │   │   ├── handlers/   # aiogram Routers, one per feature
│   │   │   │   ├── keyboards/
│   │   │   │   ├── states.py   # FSM states
│   │   │   │   └── middlewares/
│   │   │   ├── workers/        # arq tasks (fetch rates, alerts)
│   │   │   ├── integrations/   # http clients: nbu, ecb, monobank, privat24, binance
│   │   │   └── observability/
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/    # testcontainers-postgres
│   │       └── e2e/
├── miniapp/
│   ├── package.json
│   ├── Dockerfile
│   ├── next.config.ts
│   ├── src/
│   │   ├── app/                # Next.js App Router
│   │   ├── features/           # feature folders (dashboard, fx-log, accounts, ...)
│   │   ├── lib/                # api client, telegram-initdata hook
│   │   ├── components/
│   │   └── styles/
│   └── tests/                  # vitest + playwright
├── shared/
│   ├── openapi/                # generated JSON + TS client
│   └── types/                  # hand-written shared TS types (ISO codes, enums)
├── thoughts/                   # already present — follow trading-diary format
├── research/                   # existing references (Yakov_tg_bot, etc.)
└── scripts/
    ├── dev.sh
    ├── seed.py
    └── load-rates.py
```

**Why monorepo**: shared types generated from FastAPI's OpenAPI, single
Git history, atomic PRs that span bot/miniapp (many features need both).

### 6.1 Turborepo task graph (D7)

```jsonc
// turbo.json (sketch)
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build":     { "dependsOn": ["^build", "openapi:gen"], "outputs": [".next/**", "dist/**"] },
    "dev":       { "cache": false, "persistent": true },
    "test":      { "dependsOn": ["build"], "outputs": ["coverage/**"] },
    "lint":      { },
    "typecheck": { "dependsOn": ["openapi:gen"] },
    "openapi:gen": { "outputs": ["shared/openapi/**", "shared/types/api.ts"] }
  }
}
```

`shared/` is consumed as a workspace package by `miniapp/`. The OpenAPI
client is regenerated by a script that hits the running FastAPI app's
`/openapi.json` (in CI: spin up backend in a service container, dump
spec, run `openapi-typescript`).

---

## 7. Risks, Open Questions, Constraints

### 7.1 Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | We're anchoring to the wrong reference (user describes a feature absent from Yakov code) | Ask the user to confirm / provide alternate reference |
| R2 | Scope creep — Mini App + bot + accounting + budgets + rate alerts is a lot for a solo freelance delivery | Phase explicitly (see §3.1–3.3); land Phase 1 before any Phase 2 work |
| R3 | Rate-source scraping (minfin.com.ua) is fragile, same as reference (`MinFinParseError` exists for a reason) | Prefer **APIs** (NBU open API, ECB, monobank) over scrapers; keep scrapers behind a pluggable `RateSource` interface so they can be swapped |
| R4 | Telegram initData auth is easy to get wrong (timing attacks, replay) | Use a vetted implementation (e.g. `tma-init-data-python`); verify HMAC + `auth_date` freshness (≤24h); rotate bot token rotates everything |
| R5 | Storing money as `FLOAT` in PG is still a common mistake | Enforce `NUMERIC(20,8)` everywhere, codify in base type alias, covered by schema tests |
| R6 | Async handlers calling sync `requests` (Yakov's pattern) silently degrades throughput | Standardize on `httpx.AsyncClient` with per-source retry + timeout |
| R7 | Telegram Mini App is not available in all regions/clients | Bot must remain usable without the mini app; every mini-app feature needs a bot fallback (or a "please open in TG mobile" message) |
| R8 | PII & financial data in Telegram means GDPR-adjacent obligations even for a solo app | At minimum: explicit privacy policy, `/delete_me` export + purge flow, encryption at rest on PG, backups encrypted |

### 7.2 Open questions — status after 2026-04-23 intake

✅ resolved · ⚠️ partial · ❌ still open

| # | Question | Status | Answer / next action |
|---|----------|--------|----------------------|
| 1 | Reference identity (Yakov vs other) | ✅ | Yakov is the structural reference only; build something better from scratch (D1, 2026-04-23). |
| 2 | Target audience | ✅ | Personal + family + business books at MVP (D2, 2026-04-23). Role matrix per §4.0.1. |
| 3 | Languages | ✅ | EN + RU (D3). |
| 4 | Base currency / market | ✅ | Multi-market (D4); per-book base currency. Rate sources: ECB / Open Exchange Rates / Frankfurter / CoinGecko primary; NBU / PrivatBank / monobank as optional regional plugins. |
| 5 | Cash vs bank granularity | ❌ | **Open.** Default plan: separate `accounts.kind ∈ {cash, bank, card, crypto, other}`; user can add as many accounts of each kind as they like. |
| 6 | Rate source priority | ⚠️ | Implied by D4 (ECB/OXR primary). User has not explicitly named priorities. |
| 7 | Import sources (bank statements) | ❌ | **Open.** Default plan for MVP: CSV import only; bank-specific connectors in Phase 2. |
| 8 | Hosting & budget | ✅ | docker-compose on user's own server (D10). |
| 9 | Monetization | ⚠️ | "idk" (D5). Defer; do not architect around free-only. |
| 10 | Timeline | ❌ | **Open.** Drives whether we can attempt Phase 2 features. |

**Planning is unblocked.** Items 5, 7, 10 are non-blocking — the plan can
adopt the default assumptions stated above and let the user override
during the plan review.

### 7.3 Dependencies / external constraints

- Telegram Bot API limits: 30 msg/sec globally, 1 msg/sec per chat. Not a
  problem at MVP scale.
- Telegram WebApp supports **only HTTPS origins**; the mini app has to
  live on a real TLS-enabled domain (Caddy / Fly.io handles this for
  free).
- `python-telegram-bot` vs `aiogram` migration is **not** trivial — pick
  upfront.
- No automated tests in the Yakov reference means we cannot mechanically
  port behavior; any pattern copied must be hand-verified.

---

## 8. Non-obvious Things Worth Copying From the Reference

Not all of Yakov is bad. Things worth mirroring:

- The **`setup.py` → `alembic upgrade head` + seed** bootstrap script
  pattern. Clean first-run UX.
  ([`src/setup.py`](research/Yakov_tg_bot/src/setup.py))
- The **shared cancel conversation module**
  ([`src/handlers/canel_conversation.py`](research/Yakov_tg_bot/src/handlers/canel_conversation.py))
  — one cancel callback for every ConversationHandler. In aiogram we'd
  express this as a middleware or a common FSM filter.
- The **`BOT_COMMANDS` registry with `for_admin` flag**
  ([`src/config.py:54-65`](research/Yakov_tg_bot/src/config.py#L54-L65))
  used by `/help` to hide admin commands. Nice small pattern.
- **Per-integration domain exceptions**
  ([`src/models/errors.py`](research/Yakov_tg_bot/src/models/errors.py))
  — replicate with a base `ExternalServiceError` and subclasses, map to
  user-facing translated strings centrally.
- The **freetext UAH↔USD converter** (regex-matched
  [`handlers/currency_converter.py:10-11`](research/Yakov_tg_bot/src/handlers/currency_converter.py#L10-L11))
  is a delightful UX pattern: user types `100 usd` → instant reply.
  Reuse shape: `+100 USD @ 40.5` → logs a transaction; `?100 USD` →
  converts at current rate.
- **ConversationHandler timeouts** (300s) — aiogram has FSM TTL; keep the
  300s default.

Things **not** to copy:

- Sync `requests` inside async handlers.
- Hardcoded Ukrainian strings (build i18n infrastructure from day 1).
- Forwarding raw tracebacks to the owner's DMs (PII leak risk).
- Uncommitted Alembic migrations.
- Committed sandbox tokens (`commands/tips.py`).
- No tests, no CI.

---

## 9. Recommended Next Steps (Plan for the Plan)

> Status 2026-04-23: D1 and D2 resolved. Planning unblocked. Items 5/7/10
> in §7.2 stay open and will be addressed inside the plan with explicit
> default assumptions for the user to review.

1. **Produce a Plan document** at
   `thoughts/shared/plans/2026-04-XX-mvp-scope-and-milestones.md`
   breaking Phase 1 into 2-week milestones, given the §0.3 locked stack.
2. **Bootstrap the monorepo** per §6 with:
   - **uv** workspace for `backend/`
   - **pnpm** workspace + **Turborepo** for `miniapp/` + `shared/`
   - Ruff + Mypy strict + Pre-commit
   - Biome (or eslint+prettier) + Vitest
   - `docker-compose.yml` with postgres + redis + backend + worker +
     miniapp + caddy
   - Empty FastAPI app + empty aiogram dispatcher + empty Next.js app
     that all boot green with `pnpm dev` (delegating backend to uv).
3. **Spike the hardest risk first: Telegram initData auth + book-membership
   resolution.** End-to-end test: open mini app in a headless Telegram
   WebApp simulator → extract initData → POST `/api/auth/tma` → receive
   JWT carrying `user_id` + `default_book_id` claim → call
   `GET /api/books/{book_id}/fx-transactions` and have the API enforce
   `book_members(book_id, user_id)`. Until this is solid, nothing else is
   worth building.
4. **Ship the weighted-average-rate view as the first vertical slice** —
   `books` + `accounts` + `fx_transactions` tables + repo + service +
   FastAPI endpoint (`GET /api/books/{book_id}/fx/avg-rate`) + bot command
   `/avg` + mini-app card. This is the single differentiator vs the
   reference, and proves the stack end-to-end.

---

## Appendix A — Files referenced (canonical paths)

- [research/Yakov_tg_bot/README.md](research/Yakov_tg_bot/README.md)
- [research/Yakov_tg_bot/requirements.txt](research/Yakov_tg_bot/requirements.txt)
- [research/Yakov_tg_bot/Dockerfile](research/Yakov_tg_bot/Dockerfile)
- [research/Yakov_tg_bot/docker-compose.yaml](research/Yakov_tg_bot/docker-compose.yaml)
- [research/Yakov_tg_bot/Procfile](research/Yakov_tg_bot/Procfile)
- [research/Yakov_tg_bot/tg_bot.service](research/Yakov_tg_bot/tg_bot.service)
- [research/Yakov_tg_bot/initial_dump.sql](research/Yakov_tg_bot/initial_dump.sql)
- [research/Yakov_tg_bot/alembic.ini](research/Yakov_tg_bot/alembic.ini)
- [research/Yakov_tg_bot/alembic/env.py](research/Yakov_tg_bot/alembic/env.py)
- [research/Yakov_tg_bot/src/main.py](research/Yakov_tg_bot/src/main.py)
- [research/Yakov_tg_bot/src/config.py](research/Yakov_tg_bot/src/config.py)
- [research/Yakov_tg_bot/src/setup.py](research/Yakov_tg_bot/src/setup.py)
- [research/Yakov_tg_bot/src/commands/](research/Yakov_tg_bot/src/commands/) (11 files)
- [research/Yakov_tg_bot/src/handlers/](research/Yakov_tg_bot/src/handlers/) (5 files)
- [research/Yakov_tg_bot/src/crud/](research/Yakov_tg_bot/src/crud/) (6 files)
- [research/Yakov_tg_bot/src/models/tables/](research/Yakov_tg_bot/src/models/tables/) (9 files)
- [research/Yakov_tg_bot/src/utils/](research/Yakov_tg_bot/src/utils/) (10 files)

## Appendix B — Stack summary card (post-2026-04-23 lock)

```
Language            : Python 3.12+ / TypeScript 5+
Bot framework       : aiogram 3.x                     (D8)
Web API             : FastAPI + pydantic v2           (D8)
ORM + DB            : SQLAlchemy 2.x async + asyncpg + PostgreSQL 16  (D8)
Migrations          : Alembic (committed)             (D8)
Cache / FSM / Queue : Redis 7                         (D8)
Background jobs     : arq                             (D8)
Frontend            : Next.js 15 (App Router) + TS    (D9)
Data fetching       : TanStack Query + OpenAPI codegen
UI                  : shadcn/ui + Tailwind; Recharts (initial)         (D9)
Logging             : structlog → JSON → stdout
Error tracking      : Sentry (Python + JS)
Tests (Py)          : pytest + pytest-asyncio + respx + testcontainers
Tests (TS)          : Vitest + Playwright
Lint / Format (Py)  : ruff + mypy --strict
Lint / Format (TS)  : Biome (or eslint + prettier)
Package mgmt        : uv (Python) + pnpm (JS)         (D6)
Monorepo            : Turborepo                       (D7)
Containers          : Docker + docker-compose
Deploy              : docker-compose on user's own server + Caddy TLS  (D10)
Languages (UI)      : EN + RU                         (D3)
Markets             : Multi (per-book base currency)  (D4)
Audience            : Personal + family + business (book-scoped)        (D2)
```
