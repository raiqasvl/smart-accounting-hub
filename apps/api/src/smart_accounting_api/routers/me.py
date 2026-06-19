# Current-user / current-book convenience endpoints.
#
# Per plan §1.4 (M1):
#   - GET /me
#       Depends on current_user() + current_book_member() from deps.py.
#       Returns {user, active_book, role, books: [{id, name, kind, role}, ...]}
#       The full books list lets the Mini-App render the book switcher without a second round-trip.
#
# Lands first in M1 as the "auth path works end-to-end" demo target.
