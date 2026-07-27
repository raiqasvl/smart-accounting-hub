"""add fx_transactions.idempotency_key

Revision ID: 0003_tx_idempotency
Revises: 0002_seed_currencies
Create Date: 2026-07-21 00:00:00.000000

D28: idempotent trade recording. Adds a nullable idempotency_key plus a partial UNIQUE
(book_id, idempotency_key) WHERE idempotency_key IS NOT NULL, so a replayed Confirm returns the
existing row instead of inserting a duplicate. NULL keys stay unconstrained (Postgres treats NULLs
as distinct, and the partial predicate excludes them anyway).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_tx_idempotency"
down_revision: str | None = "0002_seed_currencies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("fx_transactions", sa.Column("idempotency_key", sa.Text(), nullable=True))
    op.create_index(
        "uq_fx_transactions_book_idempotency",
        "fx_transactions",
        ["book_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_fx_transactions_book_idempotency", table_name="fx_transactions")
    op.drop_column("fx_transactions", "idempotency_key")
