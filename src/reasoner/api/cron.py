"""Background task handlers for periodic maintenance."""

from __future__ import annotations

import logging

from reasoner.infrastructure.persistence.quota_repo_postgres import PostgresQuotaRepository
from reasoner.core.settings import settings

logger = logging.getLogger(__name__)


async def reset_all_quotas_monthly() -> None:
    """Reset all usage_quotas at month start. Called by external scheduler."""
    repo = PostgresQuotaRepository(settings.DATABASE_URL)
    pool = await repo._get_pool()
    result = await pool.execute(
        "UPDATE usage_quotas SET used_queries = 0, period_start = date_trunc('month', NOW()), "
        "updated_at = NOW() WHERE period_start < date_trunc('month', NOW())"
    )
    logger.info("Monthly quota reset complete: %s", result)
