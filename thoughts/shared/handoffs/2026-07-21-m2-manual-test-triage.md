---
date: 2026-07-21
author: i.gorvier (GitHub raiqasvl)
repository: smart-accounting-hub
branch: main
topic: "M2 manual-test triage — bot + Mini-App are 'raw / not fully functional'; next-session start here"
status: open
---

# M2 manual-test triage

M2 is code-complete, committed, and pushed (see `2026-07-21-m2-in-progress.md` for the ledger). But
the user's **real-phone manual test found the bot and Mini-App "still raw, not fully functional."**
The automated gates are green (102 py tests, mypy, lint, `next build`), so the gaps are in the
**runtime UX / integration**, not the type-level contract. **Start the next session here.**

## FIRST: get the specifics
No concrete repro was captured before wrap-up. Ask the user (or reproduce on device) exactly what
broke, per surface — which command/screen, what was expected, what happened, any error toast.
Capture it at the top of this doc before fixing.

## Candidate issues to verify (honest list of known simplifications / untested paths)

### Bot (`apps/bot`)
- **No command menu registered** — `/newbook`, `/newaccount`, `/books` are handlers but never sent to
  BotFather via `set_my_commands`, so they're undiscoverable (user must type them). Likely the biggest
  "feels broken" factor. → add `bot.set_my_commands([...])` on startup (en+ru).
- **Rolling single-message UX not built** — the plan's `MainMenuService` (edit one
  `tg_chats.last_message_id` message) was deferred; we rely on aiogram-dialog's default message reuse.
  Dialogs + `/start` may leave multiple stacked messages. Verify the flow feels like one live card.
- **Currency entry is free text** (book base currency, account currency) — no picker; a typo yields a
  server error toast. Consider a picker or client-side validation.
- **No `/invite` in the bot** — invites are minted only in the Mini-App. Joining via deep link works;
  creating one from chat does not. Decide if that's acceptable for MVP.
- **`/start` "Open App" button** depends on a live tunnel + correct `.env` DOMAIN; ephemeral.

### Mini-App (`apps/miniapp`)
- **Never verified on a real device by the agent** — only `next build` + a desktop curl. Check inside
  Telegram: theme vars (`--tg-theme-*`) actually applied, initData auth succeeds, the layout fits.
- **Native `<select>` book picker** — may render awkwardly in the Telegram in-app browser; confirm it
  opens and switching actually re-mints the JWT + reloads data.
- **Drawer / bottom-sheet** — check it opens, scrolls, and closes on the overlay tap on device.
- **Money display** — `opening_balance` shows raw (e.g. `500.00000000`); no `big.js` formatting yet
  (deferred to M3). May look unpolished.
- **Error surfacing** — API errors show `error ({code})` with the raw D24 code, not friendly copy.
- **Auth edge**: if initData is missing/expired the client throws; verify the re-auth retry path.

### Cross-cutting
- The three surfaces were proven in isolation (unit/dispatch/build) but the **full round-trip
  (phone → tunnel → Next → API → PG)** is exactly what the user exercised and found rough.

## How to resume the stack
`make up` (DB :5433 / Redis :6380 — may already be running) · `make dev-api` · `make dev-bot` ·
`make dev-miniapp` · `make tunnel` → set `.env` DOMAIN to the printed `*.trycloudflare.com` host and
**restart the bot**. Then `/start` in @smart_accounting_hub_bot → Open App.

## Suggested next-session order
1. Collect the user's concrete findings → pin them above.
2. Bot quick wins: `set_my_commands`, verify each dialog end-to-end on device, tidy message UX.
3. Mini-App on-device pass: theme, auth, picker, drawer, error copy.
4. Only once M2 is genuinely usable end-to-end → write the **M3** plan (weighted-average FX).
