# books — top-level multi-tenancy boundary (D2).
# Every domain row in the system is scoped by book_id from line 1 of v1.0.
#
# Per plan §1.3 (M1):
#   id BIGSERIAL PRIMARY KEY
#   owner_id BIGINT NOT NULL FK → users(id)          # creator; immutable; their role is OWNER
#   name TEXT NOT NULL
#   kind SMALLINT NOT NULL                           # 0=personal, 1=family, 2=business
#   base_currency_code TEXT NOT NULL                 # display currency for aggregate reports
#   default_language TEXT NOT NULL DEFAULT 'en'      # used when book is shared across users with different prefs
#   archived BOOLEAN NOT NULL DEFAULT FALSE
#   created_at, updated_at
#
# Relationships:
#   members      1-many → BookMember        # incl. the owner
#   accounts     1-many → Account
#   categories   1-many → Category
#   transactions 1-many → FxTransaction
#   currencies   1-many → Currency           # per-book overrides; system catalogue uses book_id NULL
#   invites      1-many → BookInvite
