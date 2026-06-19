# Liveness + readiness probes for Docker healthcheck and load balancers.
#
# Per plan §1.4 (M1):
#   - GET /healthz → {"status": "ok"} when the process is up. No DB query.
#   - GET /readyz  → 200 when the DB and Redis are reachable; 503 otherwise.
#                    Used by ops/compose.yml's `depends_on: condition: service_healthy`.
#
# Both routes are exempt from JWT and from CORS preflight requirements.
