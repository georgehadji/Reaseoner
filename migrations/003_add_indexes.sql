-- Migration 003: Add composite indexes for query performance (Critical Enhancement 9.4)
-- Run: psql $DATABASE_URL -f migrations/003_add_indexes.sql

-- Speed up user data export and dashboard history queries
CREATE INDEX IF NOT EXISTS idx_query_log_user_created
    ON query_log (user_id, created_at DESC);

-- Speed up subscription lookups by user + status
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status
    ON subscriptions (user_id, status);

-- Speed up quota period-based queries
CREATE INDEX IF NOT EXISTS idx_usage_quotas_period
    ON usage_quotas (period_start);

-- Optional: index for feedback stats
CREATE INDEX IF NOT EXISTS idx_feedback_timestamp
    ON feedback (timestamp DESC);
