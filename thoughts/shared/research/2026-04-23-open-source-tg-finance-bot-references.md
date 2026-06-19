# Open-Source Telegram Finance / Accounting Bot References — Survey

**Date:** 2026-04-23
**Author:** Claude (Opus 4.7, 1M ctx)
**Reason:** User declared the prior `Yakov_tg_bot` reference inadequate
("a broken link") and asked for a curated list of better open-source
references — Telegram bots and Mini Apps for accounting / personal
finance / FX bookkeeping. This doc gathers candidates and ranks them by
fit to our requirements (D2 multi-user/family/business books, D3 EN+RU,
D4 multi-currency / FX, D8/D9 stack overlap, D10 self-hosted).
**Status:** Survey complete — pick a primary structural reference and a
secondary one before planning starts.

---

## TL;DR — Recommended primary references

| Rank | Repo | Why pick | Why not |
|------|------|----------|---------|
| 1 | **FinWave-App** (org) — [github.com/FinWave-App](https://github.com/FinWave-App) | Exact architecture we want: backend + Telegram bot + Nuxt frontend + nginx + deploy scripts, multi-currency (incl. crypto), hierarchical categories, multi-language, MIT. Mature, modular, recently updated (2025). | Java/Gradle, not Python — port patterns, not code. Bot itself last touched Aug 2024 (less active than backend/frontend). |
| 2 | **TGlimmer/telegram-bookkeeping-bot** — [github.com/TGlimmer/telegram-bookkeeping-bot](https://github.com/TGlimmer/telegram-bookkeeping-bot) | Explicit multi-group / multi-account ("多群多账单") + real-time exchange rates. Closest match to our D2 (shared books) + D4 (multi-currency). Go, MIT. | **The multi-account variant is NOT open-source** (only single-account is) — the public repo is a teaser. Documentation is Chinese. |
| 3 | **mamashin/tg-bot-fastapi-aiogram** — [github.com/mamashin/tg-bot-fastapi-aiogram](https://github.com/mamashin/tg-bot-fastapi-aiogram) | Template that matches our **exact** stack: FastAPI + aiogram. No domain code, but a clean scaffolding head start. | Not a finance bot — pure template. Use for bootstrapping, not for domain reference. |

For **scaffolding** I'd lift patterns from #3, for **architecture** study #1, and for the "shared book + multi-currency UX" idea I'd browse #2.

---

## 1. Survey Method

- 4 parallel WebSearches covering:
  - personal-finance / expense-tracker bots (Python)
  - accounting / bookkeeping / multi-user
  - aiogram + FastAPI projects
  - Telegram Mini App finance projects
- 1 WebSearch for FX-specific / multi-currency / weighted-avg bots
- 6 WebFetches against the most promising repos to confirm tech stack,
  features, license, activity
- All findings captured here verbatim with links so the user can verify.

---

## 2. Candidate Comparison Matrix

Sorted in **rough order of relevance** to our requirements. ⭐ = GitHub stars; "MU" = multi-user; "MC" = multi-currency; "FX" = explicit FX-transaction handling; "MA" = mini-app exists; "EN/RU" = doc language.

| # | Repo | Stack | ⭐ | MU | MC | FX | MA | Doc | License | Last Active | Best For |
|---|------|-------|---|----|----|-----|-----|-----|---------|-------------|----------|
| 1 | [FinWave-App](https://github.com/FinWave-App) (org) | Java + Nuxt 3 + Telegram bot + nginx | 5–8 per repo | ✓ | ✓ (incl. crypto) | partial | ✓ (frontend) | EN | MIT | 2025-09 (backend) | **Architecture & domain reference** |
| 2 | [TGlimmer/telegram-bookkeeping-bot](https://github.com/TGlimmer/telegram-bookkeeping-bot) | Go | 13 | ✓ multi-group | ✓ live rates | partial | ✗ | ZH | MIT | low activity | Multi-tenant UX ideas |
| 3 | [alexey-goloburdin/telegram-finance-bot](https://github.com/alexey-goloburdin/telegram-finance-bot) | Python + SQLite + Docker | **442** | env-var ID gate only | ✗ | ✗ | ✗ | RU | not specified | low | Most-watched Python ref; tutorial repo |
| 4 | [muety/telegram-expense-bot](https://github.com/muety/telegram-expense-bot) | Node.js + MongoDB | 69 | ✓ | ✗ | ✗ | ✗ | EN | MIT | 2024-12 (archived) | Self-hosted ops patterns (rate limiting, Prometheus, polling/webhook toggle) |
| 5 | [mamashin/tg-bot-fastapi-aiogram](https://github.com/mamashin/tg-bot-fastapi-aiogram) | FastAPI + aiogram | low | n/a (template) | n/a | n/a | n/a | EN | varies | recent | **Scaffolding template (our stack)** |
| 6 | [archiesir/aiogram_bot_template](https://github.com/archiesir/aiogram_bot_template) | aiogram + aiogram-dialog + FastAPI + SQLAlchemy + asyncpg + Docker + PG | low | n/a | n/a | n/a | n/a | EN | varies | recent | Even closer template (aiogram-dialog is great for FSM) |
| 7 | [mesuutt/ledger-cli-telegram-bot](https://github.com/mesuutt/ledger-cli-telegram-bot) | Go + ledger-cli | 12 | ✗ | inherits ledger-cli's MC/FX semantics | ledger-cli native | ✗ | EN | MIT | low | If we ever back the data model with **ledger-cli text journals** instead of SQL |
| 8 | [ltsaiete/dev.finance-telegram-miniapp](https://github.com/ltsaiete/dev.finance-telegram-miniapp) | TS + Node + Vercel; `/server` + `/web` split | 0 | ✗ | ✗ | ✗ | **✓ Mini App** | EN/PT | GPL-3.0 | recent | **Mini-app reference architecture** (Vercel/Next-style split) |
| 9 | [IdanSHR/IncomeExpenseTracking](https://github.com/IdanSHR/IncomeExpenseTracking) | Node + Express + MongoDB + node-cron | 0 | unclear | ✓ (currency picker) | ✗ | ✗ | EN | MIT | low | Personal+business positioning |
| 10 | [pavelmakis/telexpense](https://github.com/pavelmakis/telexpense) | Python + Google Sheets | low | ✓ | ✓ (in sheet) | ✗ | ✗ | EN | varies | recent | Google Sheets backend pattern |
| 11 | [sickmz/microw](https://github.com/sickmz/microw) | Python + local xlsx + Google Sheets sync | low | ✗ | ✗ | ✗ | ✗ | EN | varies | recent | xlsx UX inspiration |
| 12 | [nhduong/fibot](https://github.com/nhduong/fibot) | Python + SQLite | low | ✓ | ✗ | ✗ | ✗ | EN | varies | low | Simple Python scaffolding |
| 13 | [cenoff/Money-Bot](https://github.com/cenoff/Money-Bot) | aiogram + SQLite | low | ✓ | ✗ | ✗ | ✗ | EN/RU | varies | recent | Pure-aiogram example |
| 14 | [loginchik/Money-Tracker-TG-Bot](https://github.com/loginchik/Money-Tracker-TG-Bot) | aiogram | low | ✓ | ✗ | ✗ | ✗ | EN | varies | recent | Categories + sub-categories + limits |
| 15 | [dagedarr/telegram-budget](https://github.com/dagedarr/telegram-budget) | aiogram + Flask webhook | low | ✓ | ✗ | ✗ | ✗ | RU | varies | recent | aiogram + webhook deploy pattern |
| 16 | [edoardob90/finance-tracker-bot](https://github.com/edoardob90/finance-tracker-bot) | Python + Google Sheets | low | ✓ | ✗ | ✗ | ✗ | EN | varies | low | Sheets-backed reporting |
| 17 | [masudur-rahman/expense-tracker-bot](https://github.com/masudur-rahman/expense-tracker-bot) | Go + PDF reports | low | ✓ | ✗ | ✗ | ✗ | EN | varies | low | PDF-export pattern |
| 18 | [savandriy/baratto](https://github.com/savandriy/baratto) | Python | low | ✗ | ✓ live | ✓ rate-shopping | ✗ | EN | varies | low | UX for finding optimal exchange rates |
| 19 | [jasursadikov/telegram-currency-converter-bot](https://github.com/jasursadikov/telegram-currency-converter-bot) | C# / .NET | low | ✗ | ✓ inline | ✗ | ✗ | EN | varies | low | Inline-bot UX for currency conversion |
| 20 | [GABAnich/locash](https://github.com/GABAnich/locash) | Python | low | ✗ | ? | ? | ✗ | EN | varies | low | Niche; quickly-readable codebase |
| 21 | [robdevops/finbot](https://github.com/robdevops/finbot) | Python | low | ✓ | ✓ via Sharesight | ✗ | ✗ | EN | varies | low | Sharesight + Yahoo-Finance integration |
| 22 | [lyskouski/app-finance](https://github.com/lyskouski/app-finance) (Fingrom) | Flutter | high | ✓ | ✓ | ✓ | n/a (mobile) | EN | varies | recent | Domain model & UX (full-fat fintech app) |

> Note: ⭐ counts and "Last Active" are best-effort from the WebFetch
> snapshot at 2026-04-23 and may be stale. Verify on GitHub before
> committing.

---

## 3. Detailed Notes on the Top 3

### 3.1 FinWave-App — [github.com/FinWave-App](https://github.com/FinWave-App)

The most architecturally relevant reference. 11 repositories under one
org, all MIT-licensed, demonstrating the full stack pattern we are aiming
for.

| Repo | Purpose | Lang | Stars | Last Updated |
|------|---------|------|-------|--------------|
| [FinWave-Backend](https://github.com/FinWave-App/FinWave-Backend) | Java REST API for budgeting | Java | 5 | 2025-04-08 |
| [FinWave-Frontend](https://github.com/FinWave-App/FinWave-Frontend) | Nuxt 3 frontend | Vue | 8 | 2025-01-16 |
| [FinWave-Telegram-Bot](https://github.com/FinWave-App/FinWave-Telegram-Bot) | Telegram bot client of the API | Java | 3 | 2024-08-29 |
| [FinWave-Java-API](https://github.com/FinWave-App/FinWave-Java-API) | Java REST API wrapper (used by the bot) | Java | 1 | 2024-08-18 |
| [FinWave-Deploy](https://github.com/FinWave-App/FinWave-Deploy) | Shell deploy scripts | Shell | 5 | 2025-01-13 |
| [FinWave-Nginx](https://github.com/FinWave-App/FinWave-Nginx) | Nginx Docker config | Dockerfile | 1 | 2024-08-17 |
| [FinWave-Site](https://github.com/FinWave-App/FinWave-Site) | Marketing site | Vue | 1 | 2024-08-16 |
| [Telegram-Abstractions-Tools](https://github.com/FinWave-App/Telegram-Abstractions-Tools) | Java TG library | Java | 1 | 2025-09-30 |
| [Reactive-Configs-Tool](https://github.com/FinWave-App/Reactive-Configs-Tool) | Reactive config files | Java | 1 | 2025-03-26 |

Documented features:
- Multi-currency including crypto with custom decimal precision
- Multiple accounts per user
- Hierarchical categories (tree structure)
- Multi-language UI
- Automated/recurring transactions
- CSV import/export

**Verdict:** read this carefully for architecture and feature parity.
Reimplement in our stack. The `FinWave-Telegram-Bot` repo is small
(20 commits, 3 stars) so the bot UX is the weakest link of the trio —
we can do a **better** bot UX while matching its backend feature set.

### 3.2 TGlimmer/telegram-bookkeeping-bot — [github.com/TGlimmer/telegram-bookkeeping-bot](https://github.com/TGlimmer/telegram-bookkeeping-bot)

The **only** project I found that explicitly markets itself as
multi-group / multi-account with live exchange rates — exactly our D2 +
D4 combination.

Caveats:
- Repo is in **Go**.
- Documentation is in Chinese.
- The README explicitly says **the multi-account version is not
  open-source**; the open-source repo is a single-account preview, with
  the multi-account flavor as a hosted bot at `@FreeJzBot`.
- The author warns of fraudulent forks claiming to offer the multi-account
  version.

**Verdict:** read for **UX patterns** (how do you present "multiple books
inside one bot"?). Don't expect to lift code.

### 3.3 mamashin/tg-bot-fastapi-aiogram — [github.com/mamashin/tg-bot-fastapi-aiogram](https://github.com/mamashin/tg-bot-fastapi-aiogram)

Empty domain template, but exact stack overlap (FastAPI + aiogram). Use
for bootstrapping.

A close alternative is
[archiesir/aiogram_bot_template](https://github.com/archiesir/aiogram_bot_template)
which adds **aiogram-dialog** (a clean FSM/dialog library) + SQLAlchemy
async + asyncpg + Postgres + Docker — even closer to our final shape.

---

## 4. Notable Adjacent References (not bots, but worth knowing)

- [lyskouski/app-finance](https://github.com/lyskouski/app-finance)
  (Fingrom) — Flutter cross-platform finance app, **rich domain model**
  for accounts / transactions / FX / categories. Read its data model
  and feature set even though it's not a bot.
- [telegram-mini-apps](https://github.com/telegram-mini-apps) — official
  org with templates / SDKs / docs for the Mini App platform itself.
- [telegram-mini-apps-dev/awesome-telegram-mini-apps](https://github.com/telegram-mini-apps-dev/awesome-telegram-mini-apps)
  — curated list; useful for finding more mini-app references.
- [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade) — not an
  accounting bot but the gold standard for Python+TG architecture
  (modular, plugin-driven, well-tested). Worth a tour.
- [Endogen/OpenCryptoBot](https://github.com/Endogen/OpenCryptoBot) —
  large reference for "many commands, modular handlers" pattern.

---

## 5. Recommendation

Adopt **two** references for the project:

1. **Architecture / feature parity:** [FinWave-App](https://github.com/FinWave-App)
   — read all four repos (backend, frontend, telegram-bot, deploy) end
   to end before we cut our schema in stone. They've already solved the
   hierarchical-category + multi-currency + crypto-precision problems.
2. **Code-level scaffolding:** [archiesir/aiogram_bot_template](https://github.com/archiesir/aiogram_bot_template)
   *or* [mamashin/tg-bot-fastapi-aiogram](https://github.com/mamashin/tg-bot-fastapi-aiogram)
   — start from one of these for our `backend/` package shape, then
   layer FinWave's domain model on top.

Optional drop-ins:
- Skim [TGlimmer](https://github.com/TGlimmer/telegram-bookkeeping-bot)
  for "shared books in TG" UX ideas.
- Skim [telegram-mini-apps-dev/awesome-telegram-mini-apps](https://github.com/telegram-mini-apps-dev/awesome-telegram-mini-apps)
  for Mini-App examples.

---

## 6. Action Items

- [ ] User picks primary structural reference (FinWave is my pick).
- [ ] User picks scaffolding template (archiesir or mamashin).
- [ ] Drop these into `research/` alongside `Yakov_tg_bot/` so future
      passes can grep all of them in one place. Suggested layout:

```
research/
├── Yakov_tg_bot/                          # existing, keep for context
├── FinWave-Backend/                       # git clone --depth=1
├── FinWave-Frontend/                      # git clone --depth=1
├── FinWave-Telegram-Bot/                  # git clone --depth=1
├── FinWave-Deploy/                        # git clone --depth=1
└── aiogram-fastapi-template/              # git clone --depth=1 of the chosen template
```

- [ ] Then revisit the open §7.2 items (5/7/10) and start the plan doc.

---

## Sources

- [pavelmakis/telexpense](https://github.com/pavelmakis/telexpense)
- [muety/telegram-expense-bot](https://github.com/muety/telegram-expense-bot)
- [sickmz/microw](https://github.com/sickmz/microw)
- [edoardob90/finance-tracker-bot](https://github.com/edoardob90/finance-tracker-bot)
- [masudur-rahman/expense-tracker-bot](https://github.com/masudur-rahman/expense-tracker-bot)
- [ythosa/minuki](https://github.com/ythosa/minuki)
- [dagedarr/telegram-budget](https://github.com/dagedarr/telegram-budget)
- [felixxvo7/Telegram-Finance-Tracker-and-Budget-Visualization-System](https://github.com/felixxvo7/Telegram-Finance-Tracker-and-Budget-Visualization-System)
- [alexey-goloburdin/telegram-finance-bot](https://github.com/alexey-goloburdin/telegram-finance-bot)
- [nhduong/fibot](https://github.com/nhduong/fibot)
- [TGlimmer/telegram-bookkeeping-bot](https://github.com/TGlimmer/telegram-bookkeeping-bot)
- [Patr1k10/HomeBookkeepingInTelegram](https://github.com/Patr1k10/HomeBookkeepingInTelegram)
- [albertodeago/despesas-bot](https://github.com/albertodeago/despesas-bot)
- [IdanSHR/IncomeExpenseTracking](https://github.com/IdanSHR/IncomeExpenseTracking)
- [R3D4NG3L/PersonalExpenseReport](https://github.com/R3D4NG3L/PersonalExpenseReport)
- [cenoff/Money-Bot](https://github.com/cenoff/Money-Bot)
- [mamashin/tg-bot-fastapi-aiogram](https://github.com/mamashin/tg-bot-fastapi-aiogram)
- [ilyarolf/AiogramShopBot](https://github.com/ilyarolf/AiogramShopBot)
- [loginchik/Money-Tracker-TG-Bot](https://github.com/loginchik/Money-Tracker-TG-Bot)
- [archiesir/aiogram_bot_template](https://github.com/archiesir/aiogram_bot_template)
- [lyskouski/app-finance](https://github.com/lyskouski/app-finance) (Fingrom)
- [telegram-mini-apps](https://github.com/telegram-mini-apps)
- [ltsaiete/dev.finance-telegram-miniapp](https://github.com/ltsaiete/dev.finance-telegram-miniapp)
- [GABAnich/locash](https://github.com/GABAnich/locash)
- [FinWave-App](https://github.com/FinWave-App)
- [telegram-mini-apps-dev/awesome-telegram-mini-apps](https://github.com/telegram-mini-apps-dev/awesome-telegram-mini-apps)
- [mesuutt/ledger-cli-telegram-bot](https://github.com/mesuutt/ledger-cli-telegram-bot)
- [MarcelBeining/EazeBot](https://github.com/MarcelBeining/EazeBot)
- [Endogen/OpenCryptoBot](https://github.com/Endogen/OpenCryptoBot)
- [freqtrade/freqtrade](https://github.com/freqtrade/freqtrade)
- [savandriy/baratto](https://github.com/savandriy/baratto)
- [alberto-rota/CryptoWallet-TelegramBot](https://github.com/alberto-rota/CryptoWallet-TelegramBot)
- [ablanco/cryptorates-telegram-bot](https://github.com/ablanco/cryptorates-telegram-bot)
- [jasursadikov/telegram-currency-converter-bot](https://github.com/jasursadikov/telegram-currency-converter-bot)
- [botcrypto-io/awesome-crypto-trading-bots](https://github.com/botcrypto-io/awesome-crypto-trading-bots)
- [robdevops/finbot](https://github.com/robdevops/finbot)
- [KonstantinS343/Finance-telegram-bot](https://github.com/KonstantinS343/Finance-telegram-bot)
- [samgozman/fin-thread](https://github.com/samgozman/fin-thread)
