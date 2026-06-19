# Reusable Annotated SQLAlchemy column types.
#
# Per plan §1.2 (M1, cherry-picked from research/AiogramBotTemplate/bot/models/fields.py:1-19),
# extended for our domain:
#
#   uuid_pk         UUID primary key with gen_random_uuid() server default        (cherry-picked)
#   chat_id_bigint  BigInteger UNIQUE                                             (cherry-picked)
#
# Domain-specific additions:
#   bigserial_pk    BIGSERIAL primary key (most domain tables use this — sequential, dense)
#   currency_code   String(8) NOT NULL — ISO 4217 + crypto codes
#   money_amount    NUMERIC(20, 8) NOT NULL — D5 precision contract
#   ltree_path      LtreeType NOT NULL (categories.parents_tree, D14)
#   tg_user_id      BigInteger UNIQUE NOT NULL (telegram_user_id on users)
#   timestamptz     DateTime(timezone=True) NOT NULL DEFAULT now()
