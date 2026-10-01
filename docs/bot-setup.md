# Bot setup — registering with @BotFather and wiring credentials

Step-by-step guide to creating the Telegram bot, getting all the credentials, configuring it for our project, and filling in `.env`. Covers both local development (with a public tunnel for the Mini-App) and production deployment.

> **Time required:** ~15 minutes for the bot itself; +10 minutes if you've never set up a public tunnel before.

## Prerequisites

- A regular Telegram account (any country, any phone number).
- The `Telegram` app (mobile or desktop) — both work; desktop is faster for paste-heavy steps like avatars.
- For the Mini-App: a public HTTPS URL.
  - **Dev:** `cloudflared` or `ngrok` to expose `http://localhost:3000`.
  - **Prod:** a domain you control + a server with ports 80/443 open.

You will end up with these credentials filled into `.env`:

| Variable | Source |
|---|---|
| `BOT_TOKEN` | @BotFather (Step 2) |
| `BOT_USERNAME` | @BotFather (Step 1) |
| `JWT_SECRET` | Generated locally (Step 6) |
| `DOMAIN` | Your tunnel/prod URL (Step 5 / Step 9) |

---

## Step 1 — Create the bot

1. Open Telegram. Search for **`@BotFather`** (the one with the blue verified checkmark — there are impostors).
2. Send `/start`. BotFather replies with a menu of commands.
3. Send `/newbot`.
4. BotFather asks for a **display name**. This is what users see at the top of a chat. For dev, use something like `Smart Accounting Hub (dev)`. For prod, the production name, e.g. `Smart Accounting Hub`.
5. BotFather asks for a **username**. Must:
   - End with `bot` (case-insensitive).
   - Be 5–32 characters.
   - Be globally unique on Telegram.
   - Suggest: `smart_accounting_dev_bot` for dev, `smart_accounting_hub_bot` (or whatever's free) for prod.
6. BotFather replies with a confirmation that includes your **bot token**. It looks like:

   ```text
   123456789:AAEhZGoMo2hQQCcqYmQ2N9Wxqz1234567ABC
   ```

   **This is `BOT_TOKEN`.** Copy it now and save it somewhere safe (a password manager).
   - Treat it like a database password. Anyone with the token can impersonate the bot.
   - If it leaks, send `/revoke` to BotFather → it issues a new one (the old one stops working immediately).

Also note your **bot username** without the `@` — e.g. `smart_accounting_hub_bot` — this is `BOT_USERNAME`.

## Step 2 — Save credentials

Open `.env` (create it from `.env.example` if you haven't):

```bash
cp .env.example .env
chmod 600 .env
```

Fill in:

```dotenv
BOT_TOKEN=123456789:AAEhZGoMo2hQQCcqYmQ2N9Wxqz1234567ABC
BOT_USERNAME=smart_accounting_hub_bot
```

Verify the token works (one-shot check, doesn't write anything):

```bash
curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe" | python -m json.tool
```

You should see a JSON response with `"ok": true` and your bot's identity. If you get `"ok": false` and `"description": "Unauthorized"` — the token is wrong or revoked.

## Step 3 — Configure the bot in @BotFather

Send each command separately to @BotFather. They're chat-driven menus.

### 3.1 Set the description (long, shown in profile)

```text
/setdescription
```

Choose your bot, then send the description text. Suggested:

> Telegram-Mini-App-driven personal/family/business FX accounting tool.
> Headline feature: weighted-average exchange-rate queries across stored FX transactions.
> Supports EN + RU.

### 3.2 Set the about text (short, shown above the description)

```text
/setabouttext
```

Suggested:

> FX accounting with weighted-average rates. Personal, family, business books.

### 3.3 Set the avatar

```text
/setuserpic
```

Send a 640×640 PNG (file or photo). Telegram accepts any square image but prefers ≥512px. Use the project logo or a placeholder.

### 3.4 Set the slash-command menu

```text
/setcommands
```

Choose your bot, then **paste the full block below** (one command per line, format `command - description`):

```text
start - Open the main dashboard
books - Switch active book
trade - Record an FX trade
avg - Show weighted-average rate
lang - Change language (EN/RU)
help - Get help
```

**Note:** these commands light up across milestones — `/start` in M1, `/books` and `/lang` in M2, `/avg` and `/trade` in M3, `/help` in M4. You can register them all now; the bot will gracefully reply "this command is not yet implemented" for unregistered handlers (we'll wire that fallback in M1).

### 3.5 Set group permissions

```text
/setjoingroups
```

Choose **Enable** — we want users to be able to add the bot to family/business group chats.

```text
/setprivacy
```

Choose **Disable** (privacy mode OFF). This lets the bot **read every message** in groups it's added to, not just messages that mention it or replies to it. Required for our group-chat free-text recording flows in v1.1+. (At v1.0 the bot mostly responds to commands, but flipping this later requires re-adding the bot to every group, so set it now.)

### 3.6 Disable inline mode

```text
/setinline
```

Choose **Disable** — we don't use inline queries.

### 3.7 (Optional) Set the menu button

The persistent button at the bottom-left of every chat. Useful for one-tap Mini-App access.

```text
/setmenubutton
```

Choose your bot. Send the button text (e.g. `Open app`) and the Mini-App URL. **Skip this until Step 5** when you have a URL.

---

## Step 4 — Create the Mini-App

The Mini-App is a web app that opens inside Telegram's WebView. It needs a public HTTPS URL.

### 4.1 Tell @BotFather about the Mini-App

```text
/newapp
```

@BotFather will ask:

1. Which bot — pick yours.
2. **Title** — `Smart Accounting Hub` (or `Smart Accounting Hub (dev)` for dev).
3. **Short description** (≤512 chars).
4. **Photo** — 640×360 PNG (the preview image when sharing the app).
5. **Demo GIF** — optional; skip with `/empty`.
6. **Web App URL** — see Step 5.
7. **Short name** — URL-safe slug, used in `https://t.me/<bot_username>/<short_name>`. Use `app` or `accounting`.

Save the resulting Mini-App URL — it looks like:

```text
https://t.me/smart_accounting_hub_bot/app
```

This is what you share when you want users to launch the Mini-App.

### 4.2 Web App URL — what to put

The URL must be HTTPS and serve our Next.js frontend. Three options:

| Where | URL shape | When |
|---|---|---|
| **Dev with cloudflared** | `https://<random>.trycloudflare.com` | Local development |
| **Dev with ngrok** | `https://<random>.ngrok.app` | Local development (ngrok account required) |
| **Production** | `https://${DOMAIN}` (your real domain) | Production deploy |

Detailed setup for each in Step 5.

---

## Step 5 — Public URL for the Mini-App

### Option A: cloudflared (recommended for dev — no signup, free, fast)

```bash
brew install cloudflared            # macOS
# or: https://github.com/cloudflare/cloudflared/releases
```

After `make up` (the compose stack is running, miniapp is on :3000):

```bash
cloudflared tunnel --url http://localhost:3000
```

The output prints a `https://<random>.trycloudflare.com` URL. **This URL changes every time you restart cloudflared.** Each restart you need to update the Mini-App URL in @BotFather (`/myapps` → choose app → Edit Web App URL).

### Option B: ngrok

```bash
brew install ngrok
ngrok config add-authtoken <YOUR_TOKEN>     # one-time, after signing up at ngrok.com
ngrok http 3000
```

The URL also changes on restart unless you have a paid plan with a reserved subdomain.

### Option C: production domain

You own `accounting.example.com`. DNS A record points to your server's IP. The shared Caddy on the droplet handles auto-TLS (see [deploy.md](deploy.md)). The URL is permanent.

After picking one, **update `.env`**:

```dotenv
DOMAIN=<your-tunnel-or-prod-domain-without-https>
```

The Mini-App needs no URL of its own: it calls the API by relative `/api/v1/*` paths on its own origin.

And **update the Mini-App URL in @BotFather**:

```text
/myapps
```

Choose your bot → choose the Mini-App → **Edit Web App URL** → paste `https://<your-domain>/`.

---

## Step 6 — Generate the JWT secret

The Mini-App auth path issues a JWT signed with `JWT_SECRET` (decision D12). Generate a 32-byte URL-safe secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Paste it into `.env`:

```dotenv
JWT_SECRET=ZkH7w9...              # output of the command above
JWT_LIFETIME_SECONDS=1800          # 30 minutes (D12)
```

**Never commit `.env`.** It's in `.gitignore` already.

## Step 7 — Set the database password

Postgres password is mounted as a Docker secret (decision D20):

```bash
mkdir -p db
python -c "import secrets; print(secrets.token_urlsafe(24))" > db/password.txt
chmod 600 db/password.txt
```

Update the inline password in `POSTGRES_DSN` to match what's in `db/password.txt`:

```dotenv
POSTGRES_DSN=postgresql+asyncpg://smart_accounting:<paste-from-password.txt>@db:5432/smart_accounting
```

> The duplication is annoying but unavoidable: `db/password.txt` is consumed by Postgres's container at boot via `POSTGRES_PASSWORD_FILE`, while the Python app reads the full DSN. Keep them in sync.

## Step 8 — Test the bot locally (M1 onward)

Once code lands in M1:

```bash
make up           # postgres + redis + api + bot + caddy
make migrate      # alembic upgrade head
docker compose logs -f bot
```

In Telegram, find your bot by `@username` and send `/start`. You should see the welcome message we coded in `apps/bot/src/smart_accounting_bot/handlers/commands.py`.

If `/start` does nothing:

- Check `docker compose logs bot` for errors.
- Verify `BOT_TOKEN` is correct: `curl https://api.telegram.org/bot${BOT_TOKEN}/getMe`.
- Confirm polling is connecting: bot logs should show `INFO aiogram.dispatcher Run polling for bot @<username>`.

If the Mini-App button does nothing in Telegram:

- Confirm the Web App URL in @BotFather (`/myapps` → Edit) is your current cloudflared/ngrok URL.
- Confirm `make dev-miniapp` is running and the URL serves: open it in a regular browser; you should see the M1 hello card.

---

## Step 9 — Production

Production reuses the **same bot** as local development (decision 2026-10-01 — one bot is enough
at this stage). That has two consequences:

- **Never poll from two places at once.** Telegram gives each token's updates to one poller; a
  local `make dev-bot` while the server's bot runs makes both race for updates and log
  `TelegramConflictError`. Before working on the bot locally, stop production's, and start it
  again afterwards:

  ```bash
  ssh deploy@167.172.137.214 'cd /srv/smart-accounting && docker compose stop bot'
  ssh deploy@167.172.137.214 'cd /srv/smart-accounting && docker compose start bot'
  ```

- **The `/start` button follows whichever process answered.** It is built from that process's
  `DOMAIN`, so a local bot with `DOMAIN=<tunnel>` sends users to your laptop. The menu button set
  in @BotFather is one per bot and stays on production.

Steps:

1. Copy the existing bot's token into `/srv/smart-accounting/.env` on the droplet
   ([deploy.md §4](deploy.md#4-secrets-on-the-droplet)) — never into chat, the repo or GitHub.
2. After the first deploy answers on `https://<domain>/`:
   - `/newapp` (or `/myapps` → Edit Web App URL) → `https://<domain>/`
   - `/setmenubutton` → `Open app` → `https://<domain>/`
3. `/start` the bot from your phone and open the Mini-App.

If one bot becomes limiting (real users while you develop), create a separate dev bot with
`/newbot` and give it its own token in your local `.env`; production keeps the current one.

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `Unauthorized` from `/getMe` | Wrong or revoked `BOT_TOKEN` | Re-copy from BotFather; or `/revoke` to mint a new one |
| Mini-App button does nothing | Web App URL not set, or HTTP (must be HTTPS) | `/myapps` in BotFather; verify URL is `https://...` |
| Mini-App opens but shows blank | Next.js dev server not running, or 404 | `make dev-miniapp` and check the terminal output |
| `403` from `POST /auth/telegram` | initData HMAC mismatch — your `BOT_TOKEN` differs between BotFather and `.env` | Re-copy token; restart `dev-api` and `dev-bot` |
| Bot doesn't respond in groups | Privacy mode is ON | `/setprivacy` → Disable; remove + re-add bot to the group |
| `make migrate` fails: "extension ltree does not exist" | Postgres image too old | Confirm `image: postgres:16` in `ops/compose.yml`; `docker compose pull` |
| `connection refused` on `localhost:5432` from `make dev-api` | `make up` not run, or container unhealthy | `make logs` to see if Postgres started; `docker compose -f ops/compose.yml ps` |

## Useful @BotFather commands reference

| Command | Purpose |
|---|---|
| `/newbot` | Create a new bot |
| `/mybots` | List your bots, edit settings |
| `/myapps` | List Mini-Apps, edit URLs |
| `/token` | Re-fetch the bot token |
| `/revoke` | Invalidate the current token, get a new one |
| `/setname` | Change display name |
| `/setdescription` | Change long description |
| `/setabouttext` | Change short about text |
| `/setuserpic` | Change avatar |
| `/setcommands` | Update slash-command menu |
| `/setjoingroups` | Allow/disallow adding to groups |
| `/setprivacy` | Privacy mode in groups |
| `/setinline` | Inline-query mode (we don't use) |
| `/setmenubutton` | Persistent menu button |
| `/deletebot` | Permanently delete the bot |

## One bot or two

Currently **one bot** serves both local development and production (see Step 9 for the rule that
comes with it: stop production's poller before running `make dev-bot`).

Splitting later is cheap: create a second bot with `/newbot`, put its token in your local `.env`,
and leave production's token where it is. Each bot then has its own Mini-App URL and nothing needs
stopping.

## What's next

Once `/start` works in Telegram and `/healthz` returns 200 over HTTPS, you're ready to start filling in M1. The implementation order is laid out in `thoughts/shared/plans/2026-05-01-mvp-scope-and-milestones.md` §1.

## References

- [Telegram Bot API docs](https://core.telegram.org/bots/api)
- [Telegram Mini Apps overview](https://core.telegram.org/bots/webapps)
- [Validating initData on the server](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app) — the spec our `auth/initdata.py` follows
- [aiogram 3 docs](https://docs.aiogram.dev/en/v3.13.1/)
- [@BotFather official](https://t.me/BotFather)
