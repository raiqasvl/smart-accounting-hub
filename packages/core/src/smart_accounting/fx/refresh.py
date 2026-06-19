# FX rate refresh task — runs in apps/api process lifespan.
#
# Per plan §3.1 (M3) and "No worker container at MVP" rationale:
#
#   async def refresh_loop(*, sessionmaker, http, interval_seconds: int = 3600) -> None:
#       """
#       Forever loop:
#         1. fetch_latest(base='USD') from FrankfurterClient
#         2. INSERT each (base, quote, rate, source='frankfurter', fetched_at=now()) row
#         3. await asyncio.sleep(interval_seconds)
#       Catches and logs all exceptions — must NOT die.
#       """
#
# Wired into apps/api/main.py lifespan:
#   task = asyncio.create_task(refresh_loop(...))
#   yield
#   task.cancel()
#
# When we hit v1.1 and need recurring transactions / rate alerts, this whole module migrates
# to apps/worker (arq). Until then — single asyncio task is sufficient and observable.
