# Custom aiogram middlewares. Order of registration in main.py matters.
#
# Per plan §1.5 / §2.1 / §4.4 (M1-M4):
#   - structlog_middleware     (M1) Bind chat_id, user_id, update_id to structlog contextvars.
#   - user_loader_middleware   (M1) Resolve telegram_user_id → users row, attach to handler kwargs.
#   - active_book_middleware   (M2) Resolve tg_chats.active_book_id → book + role, attach.
#   - rbac_middleware          (M2) Reject updates that don't carry the required permission for the dialog.
#   - fluent_middleware        (M4) Inject FluentLocalization for users.language into handler kwargs.
#
# Dishka's middleware is added by setup_dishka() in main.py; it slots in BEFORE these.
