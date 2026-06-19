# users — Telegram-identified humans.
#
# Per plan §1.3 (M1) initial migration:
#   id BIGSERIAL PRIMARY KEY
#   telegram_user_id BIGINT UNIQUE NOT NULL          # the canonical identity (we don't auth any other way)
#   telegram_username TEXT NULL                      # @handle, mutable; logged but not authoritative
#   first_name TEXT NULL
#   last_name TEXT NULL
#   language TEXT NOT NULL DEFAULT 'en'              # 'en' | 'ru' (D13: i18n on bot/Mini-App side)
#   timezone TEXT NOT NULL DEFAULT 'UTC'             # IANA TZ name
#   is_blocked BOOLEAN NOT NULL DEFAULT FALSE        # admin kill-switch
#   created_at, updated_at                           # from Base mixin
#
# Relationships:
#   tg_chats     1-many → TgChat
#   memberships  1-many → BookMember
#   owned_books  1-many → Book (via owner_id)
#   transactions 1-many → FxTransaction (via created_by_user_id)
