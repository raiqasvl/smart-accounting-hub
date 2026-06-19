# Structlog + Sentry initialization (D17).
#
# Per plan §1.9 (M1):
#   - configure_observability(sentry_dsn, environment) sets up:
#       * structlog with merge_contextvars, add_log_level, ISO timestamp, JSONRenderer.
#       * stdlib logging at INFO writing to stdout (json-format).
#       * sentry_sdk.init() with FastApiIntegration + AsyncioIntegration; traces_sample_rate 0.1.
#   - Called once at process boot in apps/api/main.py and apps/bot/__main__.py before anything else.
#
# Logs to stdout, picked up by Docker's json-file driver and (later) shipped to Loki.
# No Prometheus, no OpenTelemetry — explicitly deferred to v1.1+ per D17.
