from __future__ import annotations

from collections import Counter
from datetime import datetime
import logging
import time
import uuid

log = logging.getLogger(__name__)

DEFAULT_KEYSPACE = "hallow_db"

CREATE_KEYSPACE = """
    CREATE KEYSPACE IF NOT EXISTS {keyspace}
    WITH replication = {{ 'class': 'SimpleStrategy', 'replication_factor': {replication_factor} }}
"""

# FR-16, FR-17, FR-19, FR-35
# Query: get all activity of a user ordered by time; filter by activity_type
CREATE_ACTIVITY_BY_USER = """
    CREATE TABLE IF NOT EXISTS activity_by_user (
        user_id       uuid,
        user_ref      text,
        timestamp     timestamp,
        activity_id   uuid,
        activity_type text,
        content_id    uuid,
        content_ref   text,
        metadata      text,
        PRIMARY KEY ((user_id), timestamp, activity_id)
    ) WITH CLUSTERING ORDER BY (timestamp DESC);
"""
# FR-05, FR-20, FR-33, FR-35
# Query: get all activity on a given date; count unique users (DAU)
CREATE_ACTIVITY_BY_DAY = """
    CREATE TABLE IF NOT EXISTS activity_by_day (
        date          date,
        timestamp     timestamp,
        activity_id   uuid,
        user_id       uuid,
        user_ref      text,
        activity_type text,
        content_id    uuid,
        content_ref   text,
        PRIMARY KEY ((date), timestamp, activity_id)
    ) WITH CLUSTERING ORDER BY (timestamp DESC);
"""
# FR-07, FR-08, FR-13, FR-18, FR-32, FR-34
# Query: get all interactions for a piece of content ordered by time; derive metrics
CREATE_ACTIVITY_BY_CONTENT = """
    CREATE TABLE IF NOT EXISTS activity_by_content (
        content_id    uuid,
        content_ref   text,
        timestamp     timestamp,
        activity_id   uuid,
        user_id       uuid,
        user_ref      text,
        activity_type text,
        metadata      text,
        PRIMARY KEY ((content_id), timestamp, activity_id)
    ) WITH CLUSTERING ORDER BY (timestamp DESC);
"""

REFERENCE_COLUMNS = {
    "activity_by_user": {
        "user_ref": "text",
        "content_ref": "text",
    },
    "activity_by_day": {
        "user_ref": "text",
        "content_ref": "text",
    },
    "activity_by_content": {
        "content_ref": "text",
        "user_ref": "text",
    },
}


def _new_batch_statement():
    try:
        from cassandra.query import BatchStatement
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The Cassandra Python driver is not available. Install `cassandra-driver` "
            "before using the Cassandra module."
        ) from exc

    return BatchStatement()


def _normalize_limit(limit, default=20):
    if limit is None:
        return default

    normalized = int(limit)
    if normalized <= 0:
        raise ValueError("limit must be greater than zero")
    return normalized


def _row_to_activity(row):
    return {
        "user_id": getattr(row, "user_ref", None) or row.user_id,
        "user_key": row.user_id,
        "timestamp": row.timestamp,
        "date": row.timestamp.date() if getattr(row, "timestamp", None) else None,
        "activity_id": row.activity_id,
        "activity_type": row.activity_type,
        "content_id": getattr(row, "content_ref", None) or getattr(row, "content_id", None),
        "content_key": getattr(row, "content_id", None),
        "user_ref": getattr(row, "user_ref", None),
        "content_ref": getattr(row, "content_ref", None),
        "metadata": getattr(row, "metadata", None),
    }


def execute_with_retries(session, cql, retries=3, timeout=30, delay=5):
    """Execute schema-related CQL with retries to absorb startup timing issues."""
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            log.info("Executing CQL attempt %s/%s", attempt, retries)
            session.execute(cql, timeout=timeout)
            time.sleep(0.2)
            return
        except Exception as exc:  # pragma: no cover - driver-specific failures
            last_error = exc
            log.warning("CQL execution failed on attempt %s/%s: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(delay * attempt)

    raise last_error


def create_keyspace(session, keyspace=DEFAULT_KEYSPACE, replication_factor=1):
    create_keyspace_cql = CREATE_KEYSPACE.format(
        keyspace=keyspace,
        replication_factor=int(replication_factor),
    )
    execute_with_retries(session, create_keyspace_cql)


def create_schema(session):
    for statement in (
        CREATE_ACTIVITY_BY_USER,
        CREATE_ACTIVITY_BY_DAY,
        CREATE_ACTIVITY_BY_CONTENT,
    ):
        execute_with_retries(session, statement)
    _ensure_reference_columns(session)


def _get_table_columns(session, table_name):
    keyspace = session.keyspace or DEFAULT_KEYSPACE
    rows = session.execute(
        """
        SELECT column_name
        FROM system_schema.columns
        WHERE keyspace_name = %s AND table_name = %s
        """,
        (keyspace, table_name),
    )
    return {row.column_name for row in rows}


def _ensure_reference_columns(session):
    for table_name, columns in REFERENCE_COLUMNS.items():
        existing_columns = _get_table_columns(session, table_name)
        for column_name, column_type in columns.items():
            if column_name not in existing_columns:
                execute_with_retries(
                    session,
                    f"ALTER TABLE {table_name} ADD {column_name} {column_type}",
                )


def log_activity(
    session,
    user_id,
    activity_type,
    content_id=None,
    user_ref=None,
    content_ref=None,
    metadata=None,
    event_time=None,
    activity_id=None,
):
    """
    Store one activity event in the query tables needed for analytics.

    Returns a dictionary with the persisted identifiers and timestamps so the
    caller can reuse the data in CLI or API responses.
    """
    activity_id = activity_id or uuid.uuid4()
    event_time = event_time or datetime.now().astimezone()
    event_date = event_time.date()
    user_ref = user_ref or str(user_id)
    content_ref = content_ref or (str(content_id) if content_id is not None else None)
    if metadata is not None and not isinstance(metadata, str):
        metadata = str(metadata)

    insert_by_user = session.prepare(
        """
        INSERT INTO activity_by_user
            (user_id, user_ref, timestamp, activity_id, activity_type, content_id, content_ref, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )
    insert_by_day = session.prepare(
        """
        INSERT INTO activity_by_day
            (date, timestamp, activity_id, user_id, user_ref, activity_type, content_id, content_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
    )

    batch = _new_batch_statement()
    batch.add(
        insert_by_user,
        (user_id, user_ref, event_time, activity_id, activity_type, content_id, content_ref, metadata),
    )
    batch.add(
        insert_by_day,
        (event_date, event_time, activity_id, user_id, user_ref, activity_type, content_id, content_ref),
    )

    # Only write to activity_by_content when a content_id is provided
    if content_id is not None:
        insert_by_content = session.prepare(
            """
            INSERT INTO activity_by_content
                (content_id, content_ref, timestamp, activity_id, user_id, user_ref, activity_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        batch.add(
            insert_by_content,
            (content_id, content_ref, event_time, activity_id, user_id, user_ref, activity_type, metadata),
        )

    session.execute(batch)
    log.info(
        "Activity logged user=%s activity_type=%s content_id=%s",
        user_id,
        activity_type,
        content_id,
    )

    return {
        "activity_id": activity_id,
        "user_id": user_id,
        "timestamp": event_time,
        "date": event_date,
        "activity_type": activity_type,
        "content_id": content_ref or content_id,
        "user_ref": user_ref,
        "content_ref": content_ref,
        "metadata": metadata,
    }

# selection functions

# FR-16: Retrieve a user's full activity history, ordered by timestamp DESC.
def get_activity_history(
    session,
    user_id,
    limit=20,
    activity_type=None,
    activity_date=None,
    fetch_limit=1000,
):
    normalized_limit = _normalize_limit(limit)
    normalized_fetch_limit = max(_normalize_limit(fetch_limit, default=1000), normalized_limit)
    statement = session.prepare(
        f"""
        SELECT user_id, user_ref, timestamp, activity_id, activity_type, content_id, content_ref, metadata
        FROM activity_by_user
        WHERE user_id = ?
        LIMIT {normalized_fetch_limit}
        """
    )
    rows = session.execute(statement, (user_id,))
    activities = [_row_to_activity(row) for row in rows]

    if activity_type:
        activities = [row for row in activities if row["activity_type"] == activity_type]

    if activity_date:
        activities = [row for row in activities if row["date"] == activity_date]

    return activities[:normalized_limit]

# FR-17: Filter a user's activity history by activity_type.
def filter_activity_history(session, user_id, activity_type=None, activity_date=None, limit=20):
    return get_activity_history(
        session,
        user_id,
        limit=limit,
        activity_type=activity_type,
        activity_date=activity_date,
    )

# FR-20: Count unique users who were active on a given date.
def get_daily_active_users(session, query_date):
    statement = session.prepare(
        """
        SELECT user_id FROM activity_by_day
        WHERE date = ?
        """
    )
    rows = session.execute(statement, (query_date,))
    return len({row.user_id for row in rows})

# FR-32: Engagement metrics for a specific content item.
def get_content_metrics(session, content_id):
    statement = session.prepare(
        """
        SELECT activity_type, content_ref FROM activity_by_content
        WHERE content_id = ?
        """
    )
    rows = session.execute(statement, (content_id,))
    content_ref = None
    metrics = Counter(row.activity_type for row in rows)
    rows = session.execute(statement, (content_id,))
    for row in rows:
        if getattr(row, "content_ref", None):
            content_ref = row.content_ref
            break
    return {
        "content_id": content_id,
        "content_ref": content_ref,
        "total_interactions": sum(metrics.values()),
        "by_type": dict(sorted(metrics.items())),
    }

# FR-33: System-wide metrics for a given date.
def get_system_stats(session, query_date):
    statement = session.prepare(
        """
        SELECT user_id, activity_type FROM activity_by_day
        WHERE date = ?
        """
    )
    rows = session.execute(statement, (query_date,))

    total_events = 0
    unique_users = set()
    activity_breakdown = Counter()

    for row in rows:
        total_events += 1
        unique_users.add(row.user_id)
        activity_breakdown[row.activity_type] += 1

    return {
        "date": query_date,
        "total_events": total_events,
        "unique_active_users": len(unique_users),
        "activity_breakdown": dict(sorted(activity_breakdown.items())),
    }

# FR-34: Identify trending content on a given date based on total interactions.
def get_trending_content(session, query_date, limit=10):
    normalized_limit = _normalize_limit(limit, default=10)
    statement = session.prepare(
        """
        SELECT content_id, content_ref FROM activity_by_day
        WHERE date = ?
        """
    )
    rows = session.execute(statement, (query_date,))

    content_counts = Counter(
        (row.content_id, getattr(row, "content_ref", None))
        for row in rows
        if row.content_id is not None
    )
    ranked = sorted(
        content_counts.items(),
        key=lambda item: (-item[1], item[0][1] or str(item[0][0])),
    )[:normalized_limit]

    return [
        {
            "content_id": content_id,
            "content_ref": content_ref,
            "interaction_count": interaction_count,
            "engagement_score": interaction_count,
        }
        for (content_id, content_ref), interaction_count in ranked
    ]
