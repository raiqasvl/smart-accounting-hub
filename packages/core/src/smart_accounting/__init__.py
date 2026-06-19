# smart-accounting domain package.
# Public API: import directly from sub-packages (models, services, repositories, auth, fx, i18n).
# Nothing is re-exported at this top level by design — keeps `from smart_accounting import X`
# always resolvable to a clear submodule.
