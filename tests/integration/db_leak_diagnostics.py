from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from domain.config import get_settings
from domain.db.session import get_async_session_factory, list_database_session_sources


async def fetch_idle_in_transaction_backends(
    session: AsyncSession,
    *,
    application_name: str | None = None,
) -> list[dict[str, Any]]:
    app_name = application_name or get_settings().database_application_name
    result = await session.execute(
        text(
            """
            SELECT
                pid,
                application_name,
                backend_start,
                xact_start,
                state_change,
                state,
                query
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND application_name = :app_name
              AND state = 'idle in transaction'
              AND pid != pg_backend_pid()
            ORDER BY backend_start
            """
        ),
        {"app_name": app_name},
    )
    rows: list[dict[str, Any]] = []
    for mapping in result.mappings():
        row = dict(mapping)
        for key in ("backend_start", "xact_start", "state_change"):
            value = row.get(key)
            if isinstance(value, datetime):
                row[key] = value.isoformat()
        rows.append(row)
    return rows


def format_idle_backend_report(backends: list[dict[str, Any]]) -> str:
    if not backends:
        return "No idle-in-transaction backends matched the filter."

    lines = [
        f"Found {len(backends)} idle-in-transaction backend(s) "
        f"(application_name={get_settings().database_application_name}):"
    ]
    for backend in backends:
        lines.append(
            "  - pid={pid} application_name={application_name} backend_start={backend_start} "
            "xact_start={xact_start} state_change={state_change} query={query!r}".format(**backend)
        )

    lines.append("")
    lines.append("Registered database session sources:")
    for source in list_database_session_sources():
        lines.append(
            "  - {name} ({kind}): application_name={application_name}; {notes}".format(**source)
        )
    return "\n".join(lines)


async def count_idle_in_transaction_backends() -> int:
    async with get_async_session_factory()() as session:
        backends = await fetch_idle_in_transaction_backends(session)
        return len(backends)


async def idle_in_transaction_failure_message() -> str:
    async with get_async_session_factory()() as session:
        backends = await fetch_idle_in_transaction_backends(session)
    return format_idle_backend_report(backends)
