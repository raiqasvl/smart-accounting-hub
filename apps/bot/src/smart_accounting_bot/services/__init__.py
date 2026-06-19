# Bot-only services — thin wrappers around smart_accounting.services that handle Telegram-specific
# concerns: rolling-message edit (find tg_chats.last_message_id and bot.edit_message_text),
# WebAppInfo button URL construction with short-lived tokens, deep-link generation.
#
# Pure domain logic NEVER lives here — that goes in packages/core/services/.
