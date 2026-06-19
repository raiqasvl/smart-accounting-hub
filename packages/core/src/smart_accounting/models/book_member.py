# book_members — junction table user × book × role.
#
# Per plan §1.3 (M1) and §2.1 (M2 RBAC):
#   book_id BIGINT FK → books(id) NOT NULL
#   user_id BIGINT FK → users(id) NOT NULL
#   role SMALLINT NOT NULL                           # 0=owner, 1=admin, 2=editor, 3=viewer
#   invited_at TIMESTAMPTZ NOT NULL DEFAULT now()
#   accepted_at TIMESTAMPTZ NULL                     # NULL ⇒ pending invite (not used at MVP — invites are
#                                                    # in book_invites; this is for direct-add flows v1.1+)
#   PRIMARY KEY (book_id, user_id)
#
# The role enum maps to the permission matrix in auth/rbac.py.
# Owner role is granted exactly once per book (= books.owner_id row); demoted/promoted via
# `BookMemberService.change_role()` which refuses to demote the last owner.
