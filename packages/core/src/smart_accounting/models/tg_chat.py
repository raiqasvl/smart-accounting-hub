# tg_chats — one row per Telegram chat (private OR group) that has interacted with the bot.
#
# Per plan §1.3 (M1) and D15:
#   chat_id BIGINT PRIMARY KEY                       # Telegram chat id (negative for groups)
#   user_id BIGINT NOT NULL FK → users(id)           # the User this chat is bound to
#   active_book_id BIGINT NULL FK → books(id)        # NULL ⇒ user is in onboarding
#   last_message_id BIGINT NULL                      # for FinWave's single-rolling-message UX
#   ui_mode SMALLINT NOT NULL DEFAULT 0              # placeholder for future per-chat preferences
#   gpt_mode SMALLINT NOT NULL DEFAULT 0             # placeholder; AI features are out of scope at v1.0
#   hide_amounts BOOLEAN NOT NULL DEFAULT FALSE      # privacy mode for group chats
#   created_at, updated_at
#
# One user can have many chats, each with its own active_book_id. The bot's rolling-message
# UX (FinWave-style) keys off `last_message_id` — every state change calls
# bot.edit_message_text(chat_id=..., message_id=last_message_id, ...).
