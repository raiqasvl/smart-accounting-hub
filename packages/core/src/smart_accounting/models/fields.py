# Originally derived from AiogramBotTemplate (https://github.com/arturboyun/AiogramBotTemplate)
# Copyright (c) 2024 Artur Boyun. MIT License. See THIRD_PARTY_NOTICES.md.
#
# Reusable Annotated SQLAlchemy column types shared across the domain models.
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import BigInteger, DateTime, Numeric, String, func
from sqlalchemy.orm import mapped_column
from sqlalchemy_utils import Ltree, LtreeType

# BIGSERIAL primary key — sequential, dense; used by most domain tables.
bigserial_pk = Annotated[int, mapped_column(BigInteger, primary_key=True, autoincrement=True)]

# Telegram user id — BigInteger, UNIQUE, NOT NULL (users.telegram_user_id).
tg_user_id = Annotated[int, mapped_column(BigInteger, unique=True)]

# ISO 4217 + crypto currency codes.
currency_code = Annotated[str, mapped_column(String(8))]

# D5 money precision contract — NUMERIC(20, 8).
money_amount = Annotated[Decimal, mapped_column(Numeric(20, 8))]

# Hierarchical category path (categories.parents_tree, D14).
ltree_path = Annotated[Ltree, mapped_column(LtreeType)]

# Timezone-aware timestamp with server-side default.
timestamptz = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]
