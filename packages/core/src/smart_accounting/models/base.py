# Declarative Base + timestamp mixin + Postgres index naming convention.
#
# Per plan §1.2 (M1, cherry-picked verbatim from research/AiogramBotTemplate/bot/models/base.py:1-33):
#
#   POSTGRES_INDEXES_NAMING_CONVENTION = {
#       "ix": "ix_%(column_0_label)s",
#       "uq": "uq_%(table_name)s_%(column_0_name)s",
#       "ck": "ck_%(table_name)s_%(constraint_name)s",
#       "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#       "pk": "pk_%(table_name)s",
#   }
#   metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)
#
#   class Base(AsyncAttrs, DeclarativeBase):
#       __abstract__ = True
#       metadata = metadata
#       created_at: Mapped[datetime] = mapped_column(server_default=func.current_timestamp())
#       updated_at: Mapped[datetime] = mapped_column(default=datetime.now, onupdate=datetime.now)
#
# The naming convention matters for clean Alembic autogenerate diffs — without it,
# autogen produces unstable index names that change between runs.
