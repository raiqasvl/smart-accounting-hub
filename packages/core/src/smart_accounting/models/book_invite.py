# book_invites — single-use magic-link invitations.
#
# Per plan §1.3 (M1) and §2.3 (M2):
#   id BIGSERIAL PRIMARY KEY
#   book_id BIGINT FK → books(id) NOT NULL
#   invited_by BIGINT FK → users(id) NOT NULL        # who minted the invite
#   token TEXT UNIQUE NOT NULL                       # secrets.token_urlsafe(24); URL-safe, opaque
#   role SMALLINT NOT NULL                           # role assigned on acceptance (cannot be 0=OWNER)
#   expires_at TIMESTAMPTZ NOT NULL                  # default ttl 24h; max 30d
#   used_at TIMESTAMPTZ NULL                         # set on first successful accept; idempotent thereafter
#   created_at TIMESTAMPTZ NOT NULL DEFAULT now()
#
# The deep-link is constructed as `https://t.me/${BOT_USERNAME}?start=invite_${token}`.
# The bot's /start handler in apps/bot/handlers/commands.py routes `invite_<token>` payloads.
