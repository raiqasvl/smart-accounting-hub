# Deploying to production

The stack runs on one DigitalOcean droplet it shares with bvlk. GitHub Actions builds the images;
the droplet only pulls them. Design and reasoning:
[thoughts/shared/plans/2026-09-26-m5-phase3-4-droplet-deploy.md](../thoughts/shared/plans/2026-09-26-m5-phase3-4-droplet-deploy.md).

| What | Where |
|---|---|
| Droplet | `ubuntu-omnionelocal-droplet`, `167.172.137.214`, NYC1, Ubuntu 24.04, 4 GB / 2 vCPU |
| Our stack | `/srv/smart-accounting/` — `compose.yml`, `.env`, `db/password.txt` |
| Shared proxy | `/srv/edge/` — `compose.yml`, `Caddyfile`, `sites/*.caddy` |
| Images | `ghcr.io/raiqasvl/smart-accounting-app`, `ghcr.io/raiqasvl/smart-accounting-miniapp` |

Sections 1–5 are one-time. Section 6 is what every push to `main` does on its own.

## 1. Server preparation

**Swap.** The droplet has none; under memory pressure the OOM killer picks Postgres first.

```bash
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

**Cloud Firewall.** In the DigitalOcean panel, attach a firewall allowing inbound 22, 80, 443
only. It sits outside the droplet, so Docker's iptables rules cannot bypass it the way they
bypass UFW. Nothing in our compose publishes a port, but this is the guard against someone
adding one.

**Deploy user.** GitHub Actions must not log in as root. If bvlk's `DEPLOY_USER` is already a
non-root user in the `docker` group, reuse it; otherwise:

```bash
adduser --disabled-password --gecos '' deploy
usermod -aG docker deploy
install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
# paste the public half of a key pair made for this repository, then Ctrl-D:
install -m 600 -o deploy -g deploy /dev/stdin /home/deploy/.ssh/authorized_keys
```

Use a separate key pair per repository so either can be revoked alone.

## 2. Moving bvlk onto the edge proxy

> **Done 2026-10-01** (raiqasvl/bvlk.exe#11, #12, #13): about 4 s of bvlk downtime, the same
> certificate kept. The edge stack now runs from `/srv/edge`; keep this section as the record of
> how, and as the recipe for the next project that joins the droplet.

bvlk's Caddy owned 80/443 until then. It moves into `/srv/edge` so both projects can be served. Do the
repository change first — if bvlk's old `deploy.yml` runs after the switch, it starts its own
Caddy again, which then fails on the taken ports.

**In the bvlk repository:**

1. `deploy/compose.yml`: delete the `caddy` service and its volumes; attach `web` to the external
   network with a prefixed alias:

   ```yaml
   services:
     web:
       networks:
         edge:
           aliases: [bvlk-web]

   networks:
     edge:
       external: true
   ```

2. Create `deploy/bvlk.caddy` from the current `deploy/Caddyfile`, with the **literal** site
   address (the value of `SITE_ADDRESS` in `/srv/bvlk/.env` — the edge container has no such
   variable) and `reverse_proxy bvlk-web:3000`.
3. `deploy.yml`: scp `deploy/bvlk.caddy` to `/srv/edge/sites/bvlk.caddy` instead of the
   Caddyfile; run `up -d --remove-orphans` once to drop the old Caddy container; after `up -d`, add
   `docker compose -f /srv/edge/compose.yml exec -T caddy caddy reload --config /etc/caddy/Caddyfile </dev/null`.

**On the droplet (a few seconds of bvlk downtime at step 5):**

```bash
# 1. network and edge files (deploy/edge/compose.yml and deploy/edge/Caddyfile from this repo)
docker network create edge
mkdir -p /srv/edge/sites
# 2. bvlk's site file, as prepared above
cp bvlk.caddy /srv/edge/sites/
# 3. carry the certificates over so nothing is re-issued (Let's Encrypt rate-limits repeats)
docker volume create edge_caddy-data
docker run --rm -v bvlk_caddy_data:/from:ro -v edge_caddy-data:/to alpine cp -a /from/. /to/
# 4. attach the running bvlk web to edge under its alias
docker network connect --alias bvlk-web edge bvlk-web-1
# 5. switch
docker stop bvlk-caddy-1 && docker compose -f /srv/edge/compose.yml up -d
# 6. check
curl -sI https://<bvlk domain>/ | head -1
```

Then merge the bvlk change; its next deploy recreates `web` with the network from compose and
removes the stopped Caddy. To roll back before merging:
`docker compose -f /srv/edge/compose.yml down && docker start bvlk-caddy-1`.

## 3. Domain

Buy the domain and add an **A record** pointing to `167.172.137.214`. If DNS is on Cloudflare, keep the record
**DNS only (grey cloud)**: Caddy must complete the ACME challenge itself. Wait until
`dig +short <domain>` returns the droplet's address before the first deploy — a failed challenge
is rate-limited for an hour.

## 4. Secrets on the droplet

```bash
install -d -m 750 -o deploy -g deploy /srv/smart-accounting /srv/smart-accounting/db
chown deploy:deploy /srv/edge/sites
```

On your machine, fill in a copy of [`deploy/.env.example`](../deploy/.env.example) with the bot
token (the same bot as local dev — see [bot-setup.md Step 9](bot-setup.md#step-9--production)) and a
freshly generated `JWT_SECRET` and DB password, then copy both files over:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(24))" > password.txt
scp .env deploy@167.172.137.214:/srv/smart-accounting/.env
scp password.txt deploy@167.172.137.214:/srv/smart-accounting/db/password.txt
ssh deploy@167.172.137.214 'chmod 600 /srv/smart-accounting/.env /srv/smart-accounting/db/password.txt'
```

The password inside `POSTGRES_DSN` must equal `db/password.txt`. The production config refuses to
boot without `BOT_TOKEN`, `JWT_SECRET` (≥ 32 chars) and `DOMAIN`. A missing value therefore shows up
as a restarting container whose log names what is missing, not as a silently insecure API.

## 5. GitHub configuration

Repository → Settings → Secrets and variables → Actions.

| Kind | Name | Value |
|---|---|---|
| Secret | `DEPLOY_SSH_KEY` | private half of the deploy key pair |
| Secret | `DEPLOY_HOST` | `167.172.137.214` |
| Secret | `DEPLOY_USER` | `deploy` |
| Secret | `DEPLOY_HOST_KEY` | output of `ssh-keyscan -t ed25519 167.172.137.214`, taken once and checked against the droplet console |
| Variable | `SITE_ADDRESS` | the bare domain, e.g. `accounting.example.com` |
| Variable | `DEPLOY_ENABLED` | `true` — last, once sections 1–4 are done |

The bot token, JWT secret and DB password never go into GitHub: the repository is public and so
are its Actions logs.

## 6. Deploying

Every push to `main` runs CI. With `DEPLOY_ENABLED=true` it then builds both images and pushes
them to GHCR as `latest` and `<sha>`. On the droplet it pulls the images, runs `migrate`, runs
`up -d`, installs the site file and reloads Caddy, then polls `https://<domain>/readyz` and `/`.
To re-run a deploy by hand, use the Actions tab (`workflow_dispatch`).

After the first successful deploy, point the bot's Mini-App at the site in @BotFather — see
[bot-setup.md Step 9](bot-setup.md#step-9--production). The same bot serves local development, so
stop production's bot before running `make dev-bot` (Step 9 has the commands).

## 7. Operating

```bash
cd /srv/smart-accounting
docker compose ps
docker compose logs -f api bot
docker compose restart bot
docker compose run --rm migrate      # migrate sits in the `tools` profile; `up` never runs it
```

**Roll back:** set `APP_TAG=<earlier commit sha>` in `.env`, then run `docker compose up -d`.
Remove the line to return to `latest`. This does not roll back migrations, so check the target
commit's head revision first.
