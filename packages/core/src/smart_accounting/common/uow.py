# Unit-of-Work wrapper around AsyncSession.
#
# Per plan §1.2 (M1, cherry-picked from research/AiogramBotTemplate/bot/common/uow.py:1-27):
#   - UoW(session) exposes:
#       commit() / rollback() / close()
#       async __aenter__ / __aexit__ that auto-commit on success, rollback on exception.
#   - The Dishka provider in ioc.py owns session lifecycle (open + close), so UoW.__aexit__
#     is mostly a convenience for explicit `async with uow:` blocks inside services.
#
# Repositories accept a UoW (or AsyncSession) and don't manage transactions themselves.
# Services compose multiple repository calls inside a single UoW boundary.
