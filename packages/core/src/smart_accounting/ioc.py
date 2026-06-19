# Dishka providers — DI graph shared by api and bot processes.
#
# Per plan §1.2 (M1, cherry-picked from research/AiogramBotTemplate/bot/ioc.py:8-12):
#
#   class DepsProvider(Provider):
#       @provide(scope=Scope.REQUEST)
#       async def get_uow(self) -> AsyncGenerator[UoW, None]:
#           async with SessionFactory() as session:
#               yield UoW(session)
#
# M2-M5 expansion adds providers for:
#   - Settings (Scope.APP, singleton via @lru_cache get_config())
#   - AsyncEngine + sessionmaker (Scope.APP)
#   - httpx.AsyncClient (Scope.APP, single shared client with connection pool)
#   - FrankfurterClient (Scope.APP, depends on httpx)
#   - Repository instances (Scope.REQUEST, depend on UoW)
#   - Service instances (Scope.REQUEST, depend on Repositories)
#   - JWT codec (Scope.APP, depends on Settings.JWT_SECRET)
#
# The same DepsProvider shape is used by both api (via dishka.integrations.fastapi.setup_dishka)
# and bot (via dishka.integrations.aiogram.setup_dishka) — see apps/*/main.py.
