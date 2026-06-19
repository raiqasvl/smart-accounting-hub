# Role-Based Access Control matrix.
#
# Per plan §2.1 (M2):
#
#   class Role(IntEnum):
#       OWNER = 0; ADMIN = 1; EDITOR = 2; VIEWER = 3
#
#   PERMISSIONS = {
#       Role.OWNER:  {'book.delete', 'book.invite', 'book.role.change', 'book.read',
#                     'tx.write', 'tx.read', 'category.write', 'account.write'},
#       Role.ADMIN:  {'book.invite', 'book.role.change', 'book.read',
#                     'tx.write', 'tx.read', 'category.write', 'account.write'},
#       Role.EDITOR: {'book.read', 'tx.write', 'tx.read', 'category.write', 'account.write'},
#       Role.VIEWER: {'book.read', 'tx.read'},
#   }
#
# Public helpers:
#   has_permission(role: Role, permission: str) -> bool
#   require_or_raise(role: Role, permission: str) -> None     # raises Forbidden
#
# Used by both apps/api FastAPI deps and apps/bot middlewares — single source of truth.
# Test coverage: parametrised matrix test in M2 covers all 16 (role, permission-class) pairs.
