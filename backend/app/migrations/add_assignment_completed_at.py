"""Explicit, idempotent schema and backfill migration for Assignment history."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import os

from sqlalchemy import Engine, inspect, text, update

from ..database import (
    DEFAULT_DATABASE_URL,
    create_database_engine,
    create_database_tables,
    normalize_database_url,
)
from ..models import Assignment
from ..services.assignment_history import current_utc_datetime


class CompletionTimestampMigrationError(ValueError):
    """Raised when an explicit completion-timestamp migration is unsafe."""


@dataclass(frozen=True)
class CompletionTimestampMigrationResult:
    """The schema and legacy-data work completed by one migration run."""

    column_added: bool
    assignments_backfilled: int


def get_migration_database_url(
    environ: Mapping[str, str] | None = None,
    *,
    use_local_sqlite: bool = False,
) -> str:
    """Return an explicitly selected migration target without exposing secrets."""
    environment = os.environ if environ is None else environ
    configured_url = environment.get("DATABASE_URL", "").strip()
    if configured_url:
        return normalize_database_url(configured_url)
    if use_local_sqlite:
        return DEFAULT_DATABASE_URL
    raise CompletionTimestampMigrationError(
        "Set DATABASE_URL for the target database or use --local-sqlite explicitly."
    )


def completed_at_column_type(dialect_name: str) -> str:
    """Return the portable timestamp DDL for the supported database backends."""
    return "TIMESTAMP WITH TIME ZONE" if dialect_name == "postgresql" else "DATETIME"


def normalize_utc_timestamp(timestamp: datetime) -> datetime:
    """Ensure a backfill timestamp is timezone-aware UTC."""
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def migrate_assignment_completed_at(
    database_engine: Engine,
    now: datetime | None = None,
) -> CompletionTimestampMigrationResult:
    """Add ``completed_at`` when needed and backfill legacy completed rows.

    This is intentionally separate from normal API startup because ``create_all``
    does not alter tables that already exist. The column addition and legacy
    backfill occur in one transaction for databases that support transactional
    DDL; the data update is always transactional.
    """
    if "assignments" not in inspect(database_engine).get_table_names():
        create_database_tables(database_engine)
        return CompletionTimestampMigrationResult(
            column_added=False,
            assignments_backfilled=0,
        )

    backfill_timestamp = normalize_utc_timestamp(now or current_utc_datetime())
    column_added = False

    with database_engine.begin() as connection:
        column_names = {
            column["name"] for column in inspect(connection).get_columns("assignments")
        }
        if "completed_at" not in column_names:
            timestamp_type = completed_at_column_type(connection.dialect.name)
            connection.execute(
                text(
                    "ALTER TABLE assignments "
                    f"ADD COLUMN completed_at {timestamp_type}"
                )
            )
            column_added = True

        result = connection.execute(
            update(Assignment)
            .where(
                Assignment.completed.is_(True),
                Assignment.completed_at.is_(None),
            )
            .values(completed_at=backfill_timestamp)
        )

    return CompletionTimestampMigrationResult(
        column_added=column_added,
        assignments_backfilled=int(result.rowcount or 0),
    )


def main() -> None:
    """Run the explicitly requested completion timestamp migration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--local-sqlite",
        action="store_true",
        help="Target the local SQLite database only when DATABASE_URL is not set.",
    )
    arguments = parser.parse_args()

    try:
        target_url = get_migration_database_url(
            use_local_sqlite=arguments.local_sqlite,
        )
    except CompletionTimestampMigrationError as error:
        parser.exit(status=1, message=f"Migration failed: {error}\n")

    target_engine = create_database_engine(target_url)
    try:
        result = migrate_assignment_completed_at(target_engine)
    finally:
        target_engine.dispose()

    print("Assignment completion timestamp migration completed safely.")
    print(f"Column added: {result.column_added}")
    print(f"Legacy completed Assignments backfilled: {result.assignments_backfilled}")


if __name__ == "__main__":
    main()
