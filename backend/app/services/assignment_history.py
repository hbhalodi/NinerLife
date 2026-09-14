"""Completion timestamps and seven-day retention for Assignment history."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..models import Assignment

ASSIGNMENT_HISTORY_RETENTION_DAYS = 7


def current_utc_datetime() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


def apply_assignment_completion_state(
    assignment: Assignment,
    completed: bool,
    now: datetime | None = None,
) -> None:
    """Apply a completion transition while preserving its original timestamp.

    A newly completed Assignment receives the current UTC timestamp. Reopening
    always clears it. Existing legacy completed rows without a timestamp also
    receive a fresh retention window the next time they are updated as complete.
    """
    was_completed = assignment.completed
    assignment.completed = completed

    if not completed:
        assignment.completed_at = None
    elif not was_completed or assignment.completed_at is None:
        assignment.completed_at = now or current_utc_datetime()


def purge_expired_assignment_history(
    database_session: Session,
    now: datetime | None = None,
) -> int:
    """Permanently remove completed Assignments whose seven-day history expired.

    The one-statement delete runs in its own database transaction. Its predicate
    can never match incomplete Assignments or legacy completed rows that still
    need the explicit timestamp backfill migration.
    """
    cutoff = (now or current_utc_datetime()) - timedelta(
        days=ASSIGNMENT_HISTORY_RETENTION_DAYS
    )

    try:
        result = database_session.execute(
            delete(Assignment).where(
                Assignment.completed.is_(True),
                Assignment.completed_at.is_not(None),
                Assignment.completed_at <= cutoff,
            )
        )
        database_session.commit()
    except Exception:
        database_session.rollback()
        raise

    return int(result.rowcount or 0)
