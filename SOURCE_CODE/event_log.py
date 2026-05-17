#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone


APP_EVENT_LOG = os.getenv("APP_EVENT_LOG", "app_events.log")


def log_event(event_type, user_id=None, username=None, content_id=None, metadata=None):
    # Normal app actions go to a small JSON-lines log file.
    # Cassandra is kept for analytics commands, so login/like/comment/share do not depend on it.
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "username": username,
        "content_id": content_id,
        "metadata": metadata or {},
    }

    with open(APP_EVENT_LOG, "a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(event, sort_keys=True) + "\n")

    return event
