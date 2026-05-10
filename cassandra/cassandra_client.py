#!/usr/bin/env python3
import cassandra_model as model
import logging
import os
from datetime import datetime
import uuid

from cassandra.cluster import Cluster


# Set logger
log = logging.getLogger(__name__)


# Read env vars related to Cassandra App
CLUSTER_IPS = os.getenv('CASSANDRA_CLUSTER_IPS', 'localhost').split(',')
KEYSPACE = os.getenv('CASSANDRA_KEYSPACE', model.DEFAULT_KEYSPACE)
REPLICATION_FACTOR = os.getenv('CASSANDRA_REPLICATION_FACTOR', '1')

_cluster = Cluster(CLUSTER_IPS)
session  = _cluster.connect()

model.create_keyspace(session, keyspace=KEYSPACE, replication_factor=REPLICATION_FACTOR)
session.set_keyspace(KEYSPACE)
model.create_schema(session)

# Print helpers
def _print_activity_list(activities):
    if not activities:
        print("No activities found.")
        return
    sep = "-" * 64
    print(sep)
    for act in activities:
        print(f"  {'Timestamp':20}{act['timestamp']}")
        print(f"  {'Type':20}{act['activity_type']}")
        print(f"  {'Content ID':20}{act['content_id'] or '—'}")
        print(f"  {'Metadata':20}{act['metadata'] or '—'}")
        print(sep)


def _print_content_metrics(metrics):
    print(f"\nEngagement metrics for content: {metrics['content_id']}")
    print(f"  {'Total interactions':30}{metrics['total_interactions']}")
    print("  Breakdown by type:")
    for activity_type, count in metrics['by_type'].items():
        print(f"    {activity_type:<28}{count}")


def _print_system_stats(stats):
    sep = "-" * 48
    print(f"\nSystem stats for {stats['date']}")
    print(sep)
    print(f"  {'Total events':<28}{stats['total_events']}")
    print(f"  {'Unique active users':<28}{stats['unique_active_users']}")
    print("\n  Breakdown by type:")
    for activity_type, count in stats['activity_breakdown'].items():
        print(f"    {activity_type:<26}{count}")
    print(sep)


def _print_trending(results, query_date):
    sep = "-" * 64
    print(f"\nTrending content on {query_date}")
    print(sep)
    if not results:
        print("  No content activity found for this date.")
        print(sep)
        return
    for rank, item in enumerate(results, start=1):
        print(f"  #{rank:<4}{str(item['content_id']):<40}"
              f"interactions: {item['interaction_count']}")
    print(sep)

# Handlers 

# FR-05: Log a login or logout session event.
def log_session(args):
    user_id = uuid.UUID(args.user_id)
    result  = model.log_activity(session, user_id, activity_type=args.event_type)
    print(f"Session event '{result['activity_type']}' logged "
          f"[activity_id={result['activity_id']}].")

# FR-07 / FR-08 / FR-13 / FR-18 / FR-19: Log a generic user activity event.
def log_activity(args):
    user_id    = uuid.UUID(args.user_id)
    content_id = uuid.UUID(args.content_id) if args.content_id else None
    result = model.log_activity(session, user_id,
                                activity_type=args.activity_type,
                                content_id=content_id,
                                metadata=args.metadata)
    print(f"Activity '{result['activity_type']}' logged "
          f"[activity_id={result['activity_id']}].")

# FR-16: Retrieve full activity history for a user.
def get_activity_history(args):
    user_id    = uuid.UUID(args.user_id)
    activities = model.get_activity_history(session, user_id, limit=args.limit)
    print(f"\nActivity history for user: {args.user_id} ({len(activities)} events)")
    _print_activity_list(activities)

# FR-17: Filter activity history by type and/or date.
def filter_activity(args):
    user_id       = uuid.UUID(args.user_id)
    activity_date = datetime.fromisoformat(args.date).date() if args.date else None
    activities    = model.filter_activity_history(
        session, user_id,
        activity_type=args.activity_type,
        activity_date=activity_date,
        limit=args.limit,
    )
    label = args.activity_type or "all types"
    print(f"\nFiltered history for user {args.user_id} "
          f"[{label}] ({len(activities)} events)")
    _print_activity_list(activities)

# FR-20: Count unique active users on a given date.
def get_daily_active_users(args):
    query_date = datetime.fromisoformat(args.date).date()
    count      = model.get_daily_active_users(session, query_date)
    print(f"\nDaily Active Users on {args.date}: {count}")

# FR-32: Engagement metrics for a specific content item.
def get_content_metrics(args):
    content_id = uuid.UUID(args.content_id)
    metrics    = model.get_content_metrics(session, content_id)
    _print_content_metrics(metrics)

# FR-33: System-wide activity statistics for a given date.
def get_system_stats(args):
    query_date = datetime.fromisoformat(args.date).date()
    stats      = model.get_system_stats(session, query_date)
    _print_system_stats(stats)

# FR-34: Identify trending content by interaction volume.
def trending_content(args):
    query_date = datetime.fromisoformat(args.date).date()
    results    = model.get_trending_content(session, query_date, limit=args.limit)
    _print_trending(results, args.date)
