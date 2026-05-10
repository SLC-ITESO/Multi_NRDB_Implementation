#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
import logging
import os
import time
import uuid

import cassandra_model as model


log = logging.getLogger(__name__)

DEFAULT_CONTACT_POINTS = "localhost"
CLUSTER_IPS = [
    host.strip()
    for host in os.getenv("CASSANDRA_CLUSTER_IPS", DEFAULT_CONTACT_POINTS).split(",")
    if host.strip()
]
KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", model.DEFAULT_KEYSPACE).strip().lower()
REPLICATION_FACTOR = os.getenv("CASSANDRA_REPLICATION_FACTOR", "1")
CONNECT_RETRIES = int(os.getenv("CASSANDRA_CONNECT_RETRIES", "12"))
CONNECT_DELAY_SECONDS = int(os.getenv("CASSANDRA_CONNECT_DELAY_SECONDS", "10"))

_cluster = None
_session = None


def _get_session():
    global _cluster, _session

    if _session is not None:
        return _session

    try:
        from cassandra.cluster import Cluster, NoHostAvailable
    except Exception as exc:
        raise RuntimeError(
            "The Cassandra driver could not be initialized in this Python environment. "
            "If you are using Python 3.12+, install a compatible event loop dependency "
            "or run the project with a Python version supported by your driver build."
        ) from exc

    _cluster = Cluster(CLUSTER_IPS)
    session = _connect_with_retries(_cluster, NoHostAvailable)
    model.create_keyspace(session, keyspace=KEYSPACE, replication_factor=REPLICATION_FACTOR)
    session.set_keyspace(KEYSPACE)
    model.create_schema(session)
    _session = session
    return _session


def _connect_with_retries(cluster, no_host_available_error):
    # Cassandra can be "running" in Docker before it is ready to accept CQL connections.
    # This waits a bit so demo commands do not fail just because Cassandra is still starting.
    last_error = None
    for attempt in range(1, CONNECT_RETRIES + 1):
        try:
            return cluster.connect()
        except no_host_available_error as exc:
            last_error = exc
            print(
                f"Cassandra is not ready yet "
                f"({attempt}/{CONNECT_RETRIES}). Waiting {CONNECT_DELAY_SECONDS}s..."
            )
            if attempt < CONNECT_RETRIES:
                time.sleep(CONNECT_DELAY_SECONDS)

    raise RuntimeError(
        "Could not connect to Cassandra. Make sure the cassandra container is running "
        "and healthy on localhost:9042. Try: docker compose ps cassandra"
    ) from last_error


def _print_activity_list(activities):
    if not activities:
        print("No activities found.")
        return

    separator = "-" * 64
    print(separator)
    for activity in activities:
        print(f"  {'Timestamp':20}{activity['timestamp']}")
        print(f"  {'Type':20}{activity['activity_type']}")
        print(f"  {'Content ID':20}{activity['content_id'] or '-'}")
        print(f"  {'Metadata':20}{activity['metadata'] or '-'}")
        print(separator)


def _print_content_metrics(metrics):
    print(f"\nEngagement metrics for content: {metrics['content_id']}")
    print(f"  {'Total interactions':30}{metrics['total_interactions']}")
    print("  Breakdown by type:")
    for activity_type, count in metrics["by_type"].items():
        print(f"    {activity_type:<28}{count}")


def _print_system_stats(stats):
    separator = "-" * 48
    print(f"\nSystem stats for {stats['date']}")
    print(separator)
    print(f"  {'Total events':<28}{stats['total_events']}")
    print(f"  {'Unique active users':<28}{stats['unique_active_users']}")
    print("\n  Breakdown by type:")
    for activity_type, count in stats["activity_breakdown"].items():
        print(f"    {activity_type:<26}{count}")
    print(separator)


def _print_trending(results, query_date):
    separator = "-" * 64
    print(f"\nTrending content on {query_date}")
    print(separator)
    if not results:
        print("  No content activity found for this date.")
        print(separator)
        return

    for rank, item in enumerate(results, start=1):
        print(
            f"  #{rank:<4}{str(item['content_id']):<40}"
            f"interactions: {item['interaction_count']}"
        )
    print(separator)


def log_session(args):
    session = _get_session()
    user_id = uuid.UUID(args.user_id)
    result = model.log_activity(session, user_id, activity_type=args.event_type)
    print(
        f"Session event '{result['activity_type']}' logged "
        f"[activity_id={result['activity_id']}]."
    )


def log_activity(args):
    session = _get_session()
    user_id = uuid.UUID(args.user_id)
    content_id = uuid.UUID(args.content_id) if args.content_id else None
    result = model.log_activity(
        session,
        user_id,
        activity_type=args.activity_type,
        content_id=content_id,
        metadata=args.metadata,
    )
    print(
        f"Activity '{result['activity_type']}' logged "
        f"[activity_id={result['activity_id']}]."
    )


def get_activity_history(args):
    session = _get_session()
    user_id = uuid.UUID(args.user_id)
    activities = model.get_activity_history(session, user_id, limit=args.limit)
    print(f"\nActivity history for user: {args.user_id} ({len(activities)} events)")
    _print_activity_list(activities)


def filter_activity(args):
    session = _get_session()
    user_id = uuid.UUID(args.user_id)
    activity_date = datetime.fromisoformat(args.date).date() if args.date else None
    activities = model.filter_activity_history(
        session,
        user_id,
        activity_type=args.activity_type,
        activity_date=activity_date,
        limit=args.limit,
    )
    label = args.activity_type or "all types"
    print(
        f"\nFiltered history for user {args.user_id} "
        f"[{label}] ({len(activities)} events)"
    )
    _print_activity_list(activities)


def get_daily_active_users(args):
    session = _get_session()
    query_date = datetime.fromisoformat(args.date).date()
    count = model.get_daily_active_users(session, query_date)
    print(f"\nDaily Active Users on {args.date}: {count}")


def get_content_metrics(args):
    session = _get_session()
    content_id = uuid.UUID(args.content_id)
    metrics = model.get_content_metrics(session, content_id)
    _print_content_metrics(metrics)


def get_system_stats(args):
    session = _get_session()
    query_date = datetime.fromisoformat(args.date).date()
    stats = model.get_system_stats(session, query_date)
    _print_system_stats(stats)


def trending_content(args):
    session = _get_session()
    query_date = datetime.fromisoformat(args.date).date()
    results = model.get_trending_content(session, query_date, limit=args.limit)
    _print_trending(results, args.date)
