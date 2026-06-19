# Third-Party Notices

This product incorporates code and patterns from the following open-source projects.

## AiogramBotTemplate (MIT)

Source: <https://github.com/arturboyun/AiogramBotTemplate>
Copyright (c) 2024 Artur Boyun.

The following files are derived directly from AiogramBotTemplate and retain their MIT licence:

- `packages/core/src/smart_accounting/models/base.py` (was `bot/models/base.py`)
- `packages/core/src/smart_accounting/models/fields.py` (was `bot/models/fields.py`)
- `packages/core/src/smart_accounting/common/uow.py` (was `bot/common/uow.py`)
- `packages/core/src/smart_accounting/database/engine.py` (was `bot/database/db.py`)
- `packages/core/src/smart_accounting/ioc.py` (was `bot/ioc.py`)
- `migrations/env.py` (was `migrations/env.py`)
- `migrations/script.py.mako` (was `migrations/script.py.mako`)
- `alembic.ini` (was `alembic.ini`)
- `apps/bot/src/smart_accounting_bot/storage.py` (was `bot/misc.py`)
- `apps/bot/src/smart_accounting_bot/main.py` (boot-order pattern from `bot/main.py`)
- `apps/bot/src/smart_accounting_bot/__main__.py` (entry shape from `bot/__main__.py`)
- `packages/core/src/smart_accounting/config.py` (shape from `bot/config.py`)

The full text of the MIT licence is below.

```
MIT License

Copyright (c) 2024 Artur Boyun

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## FinWave (Apache 2.0) — architectural inspiration only

Source: <https://github.com/FinWave-App/FinWave-Backend>, <https://github.com/FinWave-App/FinWave-Telegram-Bot>
Copyright (c) FinWave team.

No FinWave code is incorporated into this product. The following architectural patterns are
adopted independently in our Python rewrite (full analysis in `thoughts/shared/research/2026-05-01-deep-dive-finwave-and-aiogram-template-references.md`):

- Hierarchical categories via PostgreSQL `ltree` (mirrored from FinWave's `parents_tree` column)
- Polymorphic transactions via `kind` enum + `linked_transaction_id`
- Two-table notification outbox pattern (`notifications_outbox` here)
- Per-book overrides on a system catalogue (currencies)
- DB-stored bearer tokens with `limited` flag (adapted to JWT in our system)

Apache 2.0 licence permits derivative works without code copying; this NOTICES file is informational.
