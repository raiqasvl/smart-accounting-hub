# Observability bootstrap — M1 uses stdlib logging only (supersedes milestone plan §1.9).
#
# structlog + a full log pipeline are deferred; Sentry initializes only when SENTRY_DSN is set
# (a no-op locally). Called once at process boot in apps/api/main.py and apps/bot/__main__.py.
from __future__ import annotations

import logging
import sys


def configure_observability(*, sentry_dsn: str | None, environment: str, log_level: str) -> None:
    logging.basicConfig(
        level=log_level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(dsn=sentry_dsn, environment=environment, traces_sample_rate=0.1)
