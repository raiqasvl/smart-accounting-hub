# Shared pytest fixtures for the bot test suite.
#
# Per plan Testing Strategy:
#   - `mocked_bot` fixture returns a Bot instance with aiogram's MockedBot session.
#   - `dp` fixture returns a Dispatcher with handlers + dialogs registered, FSM storage = MemoryStorage.
#   - `make_chat_update` factory builds Update payloads for /start, callback_query, dialog inputs.
#   - DB fixtures shared with apps/api/tests via a conftest in packages/core/tests/.
