# notifications_outbox — table-backed outbox for in-app notifications (FinWave pattern).
#
# Per plan §1.3 (M1) — schema lands now; drainer is a stretch goal for M4 (in-app delivery only).
# v1.1 will add WebSocket push from this table; v1.0 just persists for audit.
#
#   id BIGSERIAL PRIMARY KEY
#   user_id BIGINT NOT NULL FK → users(id)
#   book_id BIGINT NULL FK → books(id)               # NULL ⇒ user-level notification
#   kind TEXT NOT NULL                               # 'invite_accepted', 'rate_alert' (v1.1), 'low_balance' (v1.1)
#   payload JSONB NOT NULL                           # type-specific body
#   delivered_at TIMESTAMPTZ NULL                    # set when in-app inbox marks as read
#   created_at TIMESTAMPTZ NOT NULL DEFAULT now()
#   attempts SMALLINT NOT NULL DEFAULT 0
#
# Index:
#   (created_at) WHERE delivered_at IS NULL          # partial index for the drain query
#
# The 1-second drainer (FinWave's NotificationsService) is NOT implemented at v1.0; the table
# just stays as an audit log. The drainer lands in v1.1 alongside WebSocket push to the Mini-App.
