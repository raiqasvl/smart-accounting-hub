# categories — hierarchical tagging via PostgreSQL `ltree` (D14, copied from FinWave).
#
# Per plan §1.3 (M1) and §4.1 (M4 service + API):
#   id BIGSERIAL PRIMARY KEY
#   book_id BIGINT NOT NULL FK → books(id)
#   parents_tree LTREE NOT NULL                      # materialized path: 'Food.Lunch.Cafe'
#   kind SMALLINT NOT NULL                           # 0=income, 1=expense, 2=both
#   name TEXT NOT NULL
#   description TEXT NULL
#   archived BOOLEAN NOT NULL DEFAULT FALSE
#   created_at, updated_at
#
# Indexes:
#   GIST(book_id, parents_tree)                      # for `<@` containment + ordering by tree path
#
# D14: when a category's `parents_tree` changes (move under a different parent), the descendants
# get cascade-updated in the same transaction via `UPDATE ... SET parents_tree = ...`.
# Implemented in services/categories.py.
