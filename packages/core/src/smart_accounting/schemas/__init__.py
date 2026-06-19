# Pydantic v2 schemas — the wire-format contracts.
#
# Distinct from `models/` (which holds SQLAlchemy ORM classes). Schemas are what travels
# over HTTP between apps/api and the Mini-App; models are what lives in Postgres.
#
# Per plan §3.4 / §4.1 / §4.5 — schema files added per feature in M2-M4:
#   M2: book.py, invite.py, account.py, currency.py, member.py
#   M3: transaction.py, report.py
#   M4: category.py, transfer.py, export.py
#
# Q5-locked: `Money` is the canonical type for every money-shaped field in every schema.
# See `money.py`.
