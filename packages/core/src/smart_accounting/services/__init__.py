# Service layer — business logic. Both apps/api and apps/bot import from here.
#
# Per plan §0 "Two surfaces, one service layer": API routers and bot handlers MUST be
# presentation-only. They translate transport-shaped inputs (HTTP body / Telegram update)
# into service calls. They DO NOT contain business rules, validation beyond schema, or
# multi-step orchestration.
#
# Files added across milestones:
#   M1: auth_service.py        (orchestrates verify_init_data → upsert user → auto-create default book → issue JWT)
#   M2: book_service.py, invite_service.py, account_service.py, currency_service.py
#   M3: transaction_service.py, fx_refresh_service.py
#   M4: category_service.py, transfer_service.py, export_service.py
#
# Each service holds its repositories via constructor injection (Dishka builds them).
# Each service method is one logical operation; transactions begin/end inside the method.
