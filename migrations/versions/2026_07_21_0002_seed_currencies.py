"""seed_currencies

Revision ID: 0002_seed_currencies
Revises: 0001_initial
Create Date: 2026-07-21 00:00:00.000000

Seeds the system currency catalogue (book_id IS NULL). Idempotent: only inserts codes not
already present as system rows, so re-running never duplicates. (The 0001 UNIQUE(book_id, code)
constraint can't enforce this for NULL book_ids, since Postgres treats NULLs as distinct.)
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from smart_accounting.data.currencies_seed import SEED_CURRENCIES

revision: str = "0002_seed_currencies"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = {
        row[0] for row in conn.execute(sa.text("SELECT code FROM currencies WHERE book_id IS NULL"))
    }
    rows = [
        {"code": c.code, "symbol": c.symbol, "decimals": c.decimals, "kind": c.kind}
        for c in SEED_CURRENCIES
        if c.code not in existing
    ]
    if rows:
        conn.execute(
            sa.text(
                "INSERT INTO currencies (book_id, code, symbol, decimals, kind) "
                "VALUES (NULL, :code, :symbol, :decimals, :kind)"
            ),
            rows,
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM currencies WHERE book_id IS NULL AND code = ANY(:codes)"),
        {"codes": [c.code for c in SEED_CURRENCIES]},
    )
