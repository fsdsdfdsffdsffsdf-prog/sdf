"""
ReportService — domain service for creating and managing graffiti reports.

Responsibilities:
  - Generating unique report numbers (AG-YYYY-NNNNNN)
  - Persisting Report entities with related history entries
  - Enqueueing background tasks (AI analysis, geocoding, notifications)
  - Updating report status with full audit trail
"""

import re
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import logger
from app.database.models.enums import ReportStatus
from app.database.models.history import ReportHistory
from app.database.models.report import Report

settings = get_settings()


class ReportService:
    """Manages graffiti report lifecycle operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_report(
        self,
        user_id: int,
        photo_path: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None,
        description: Optional[str] = None,
        district: Optional[str] = None,
    ) -> Report:
        """
        Creates a new graffiti report and queues background processing tasks.

        Returns the created Report ORM object (with report_number assigned).
        """
        report_number = await self._generate_report_number()

        report = Report(
            report_number=report_number,
            user_id=user_id,
            photo_path=photo_path,
            latitude=latitude,
            longitude=longitude,
            address=address,
            district=district,
            description=description,
            status=ReportStatus.NEW,
        )
        self._session.add(report)
        await self._session.flush()  # Flush to get the auto-generated ID

        # Create initial history entry
        history_entry = ReportHistory(
            report_id=report.id,
            old_status=None,
            new_status=ReportStatus.NEW,
            changed_by="SYSTEM",
            comment="Заявка создана пользователем через Telegram Bot",
        )
        self._session.add(history_entry)
        await self._session.flush()

        # Enqueue background tasks (non-blocking — Webhook returns immediately)
        await self._enqueue_background_tasks(report.id, photo_path, latitude, longitude)

        logger.info(
            "Report %s created: user_id=%d, has_coords=%s",
            report_number,
            user_id,
            bool(latitude and longitude),
        )
        return report

    async def update_status(
        self,
        report_id: int,
        new_status: ReportStatus,
        changed_by: str,
        comment: Optional[str] = None,
        assigned_admin_id: Optional[int] = None,
    ) -> Report:
        """
        Updates report status, records history entry, and enqueues user notification.
        """
        result = await self._session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            raise ValueError(f"Report id={report_id} not found.")

        old_status = report.status
        report.status = new_status
        if assigned_admin_id is not None:
            report.assigned_admin_id = assigned_admin_id

        history_entry = ReportHistory(
            report_id=report.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            comment=comment,
        )
        self._session.add(history_entry)

        logger.info(
            "Report %s status updated: %s → %s by %s",
            report.report_number,
            old_status.value,
            new_status.value,
            changed_by,
        )
        return report

    async def _generate_report_number(self) -> str:
        """
        Generates a unique sequential report number in format AG-YYYY-NNNNNN.
        Uses database count + Redis atomic counter for collision safety.
        """
        year = datetime.now(timezone.utc).year
        redis_key = f"report_counter:{year}"

        try:
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            sequence = await r.incr(redis_key)
            # Set expiry at year end to auto-reset (optional — cosmetic, not safety-critical)
            await r.expire(redis_key, 366 * 24 * 3600)
            await r.aclose()
        except Exception:
            # Fallback: use DB count + 1 if Redis is unavailable
            result = await self._session.execute(func.count(Report.id))
            sequence = (result.scalar_one() or 0) + 1

        return f"AG-{year}-{sequence:06d}"

    @staticmethod
    async def _enqueue_background_tasks(
        report_id: int,
        photo_path: str,
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> None:
        """
        Enqueues ARQ background tasks:
          1. AI graffiti analysis (required, always)
          2. Reverse geocoding (only if GPS coordinates are available)
        """
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
            pool = await create_pool(redis_settings)

            await pool.enqueue_job("analyze_graffiti_photo", report_id, photo_path)
            logger.info("Enqueued AI analysis task for report_id=%d", report_id)

            if latitude is not None and longitude is not None:
                await pool.enqueue_job("reverse_geocode_report", report_id, latitude, longitude)
                logger.info("Enqueued geocoding task for report_id=%d", report_id)

            await pool.aclose()
        except Exception as exc:
            logger.error("Failed to enqueue background tasks for report_id=%d: %s", report_id, exc)
            # Non-fatal: report is saved, tasks can be retried manually
