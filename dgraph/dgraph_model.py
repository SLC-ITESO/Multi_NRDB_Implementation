#!/usr/bin/env python3
import os
from datetime import datetime, timezone

import requests


DGRAPH_ALPHA_URL = os.getenv("DGRAPH_ALPHA_URL", "http://localhost:8080")


# This is the Dgraph schema for the small graph part of the project.
# We use indexes on ids and locations because our queries search by those values.
# We use @reverse on edges because we want counts like "who follows this user?"
SCHEMA = """
user_id: string @index(exact) @upsert .
username: string @index(term) .
location: string @index(exact) .

event_id: string @index(exact) @upsert .
title: string @index(term) .
start_date: datetime @index(day) .

interest_name: string @index(exact) @upsert .

follows: [uid] @reverse .
attends: [uid] @reverse .
interested_in: [uid] @reverse .
event_topic: [uid] @reverse .

type User {
    user_id
    username
    location
    follows
    attends
    interested_in
}

type Event {
    event_id
    title
    location
    start_date
    event_topic
}

type Interest {
    interest_name
}
"""


SEED_USERS = [
    ("u1", "mariano", "Guadalajara", ["prayer", "meditation"]),
    ("u2", "german", "Guadalajara", ["prayer", "community"]),
    ("u3", "santiago", "Zapopan", ["meditation"]),
    ("u4", "ana", "Guadalajara", ["community"]),
]

SEED_EVENTS = [
    ("e1", "Prayer Circle", "Guadalajara", "2026-06-03T18:00:00Z", ["prayer"]),
    ("e2", "Community Service", "Guadalajara", "2026-06-12T09:00:00Z", ["community"]),
    ("e3", "Meditation Meetup", "Zapopan", "2026-06-07T17:00:00Z", ["meditation"]),
]


def setup_schema():
    # This installs the predicates, indexes, node types, and reverse edges in Dgraph.
    response = requests.post(
        f"{DGRAPH_ALPHA_URL}/alter",
        data=SCHEMA,
        headers={"Content-Type": "application/rdf"},
    )
    _check_response(response)
    return {"message": "Dgraph schema installed"}


def seed_graph():
    # This function creates the basic graph data so we can test the Dgraph queries.
    setup_schema()

    for user_id, username, location, interests in SEED_USERS:
        save_user(user_id, username, location)
        for interest in interests:
            save_interest(interest)
            add_edge("user_id", user_id, "interested_in", "interest_name", interest)

    for event_id, title, location, start_date, topics in SEED_EVENTS:
        save_event(event_id, title, location, start_date)
        for topic in topics:
            save_interest(topic)
            add_edge("event_id", event_id, "event_topic", "interest_name", topic)

    add_edge("user_id", "u1", "follows", "user_id", "u2")
    add_edge("user_id", "u1", "follows", "user_id", "u3")
    add_edge("user_id", "u2", "follows", "user_id", "u4")
    add_edge("user_id", "u2", "attends", "event_id", "e1")
    add_edge("user_id", "u4", "attends", "event_id", "e2")
    add_edge("user_id", "u3", "attends", "event_id", "e3")

    return {"message": "Dgraph seed data loaded"}


def save_user(user_id, username, location):
    # A User is a node because other nodes connect to it with follows and attends edges.
    uid = _uid_for("user_id", user_id) or f"_:{_blank_name(user_id)}"
    node = _node(uid)
    rdf = f"""
    {node} <dgraph.type> "User" .
    {node} <user_id> "{_escape(user_id)}" .
    {node} <username> "{_escape(username)}" .
    {node} <location> "{_escape(location)}" .
    """
    return _mutate(rdf)


def save_event(event_id, title, location, start_date):
    # An Event is a node because users can attend it and it can be recommended.
    uid = _uid_for("event_id", event_id) or f"_:{_blank_name(event_id)}"
    node = _node(uid)
    rdf = f"""
    {node} <dgraph.type> "Event" .
    {node} <event_id> "{_escape(event_id)}" .
    {node} <title> "{_escape(title)}" .
    {node} <location> "{_escape(location)}" .
    {node} <start_date> "{_escape(start_date)}" .
    """
    return _mutate(rdf)


def save_interest(interest_name):
    # Interest is a node because both users and events can point to the same interest.
    uid = _uid_for("interest_name", interest_name) or f"_:{_blank_name(interest_name)}"
    node = _node(uid)
    rdf = f"""
    {node} <dgraph.type> "Interest" .
    {node} <interest_name> "{_escape(interest_name)}" .
    """
    return _mutate(rdf)


def follow_user(user_id, target_user_id):
    # This creates User -> follows -> User.
    # Dgraph does not store duplicate edges, but we check first so the CLI can explain it.
    if user_id == target_user_id:
        raise ValueError("Users cannot follow themselves")
    if edge_exists("user_id", user_id, "follows", "user_id", target_user_id):
        raise ValueError("Follow relationship already exists")
    return add_edge("user_id", user_id, "follows", "user_id", target_user_id)


def attend_event(user_id, event_id):
    # This creates User -> attends -> Event.
    # We model attendance as an edge because event recommendations traverse through it.
    if edge_exists("user_id", user_id, "attends", "event_id", event_id):
        raise ValueError("Attendance relationship already exists")
    return add_edge("user_id", user_id, "attends", "event_id", event_id)


def add_edge(source_predicate, source_id, edge_name, target_predicate, target_id):
    source_uid = _uid_for(source_predicate, source_id)
    target_uid = _uid_for(target_predicate, target_id)
    if not source_uid or not target_uid:
        raise ValueError("Source or target node does not exist")

    rdf = f"<{source_uid}> <{edge_name}> <{target_uid}> ."
    return _mutate(rdf)


def recommend_users(user_id):
    # This query recommends users who share an interest with the current user.
    # It also removes users already followed by the current user.
    query_text = f"""
    {{
      var(func: eq(user_id, "{_escape(user_id)}")) {{
        direct as follows
        interested_in {{
          candidate as ~interested_in
        }}
      }}
    
      users(func: uid(candidate), first: 10) @filter(NOT uid(direct) AND NOT eq(user_id, "{_escape(user_id)}")) {{
        user_id
        username
        location
        follower_count: count(~follows)
      }}
    }}
    """
    return _query(query_text).get("users", [])


def recommend_users_by_location(user_id):
    # This is a simpler recommendation: users in the same city, excluding self and direct follows.
    user = get_user(user_id)
    if not user:
        return []

    query_text = f"""
    {{
      var(func: eq(user_id, "{_escape(user_id)}")) {{
        direct as follows
      }}
    
      users(func: type(User), first: 10) @filter(eq(location, "{_escape(user['location'])}") AND NOT uid(direct) AND NOT eq(user_id, "{_escape(user_id)}")) {{
        user_id
        username
        location
        follower_count: count(~follows)
      }}
    }}
    """
    return _query(query_text).get("users", [])


def local_events(user_id):
    # This query returns future events in the same city as the user.
    user = get_user(user_id)
    if not user:
        return []

    now = datetime.now(timezone.utc).isoformat()
    query_text = f"""
{{
  events(func: type(Event), first: 10) @filter(eq(location, "{_escape(user['location'])}") AND ge(start_date, "{now}")) {{
    event_id
    title
    location
    start_date
    attendee_count: count(~attends)
  }}
}}
"""
    return _query(query_text).get("events", [])


def recommend_events(user_id):
    # This query recommends events that share interests with the current user.
    # We also exclude events the user already attends.
    now = datetime.now(timezone.utc).isoformat()
    query_text = f"""
{{
  var(func: eq(user_id, "{_escape(user_id)}")) {{
    my_events as attends
    interested_in {{
      event_candidate as ~event_topic
    }}
  }}

  events(func: uid(event_candidate), first: 10) @filter(NOT uid(my_events) AND ge(start_date, "{now}")) {{
    event_id
    title
    location
    start_date
    attendee_count: count(~attends)
  }}
}}
"""
    return _query(query_text).get("events", [])


def graph_summary():
    # This is the aggregation query for the rubric.
    # count(~follows) uses the reverse follows edge to count followers.
    # count(~attends) uses the reverse attends edge to count event attendees.
    query_text = """
{
  users(func: type(User), first: 20) {
    user_id
    username
    follower_count: count(~follows)
  }

  events(func: type(Event), first: 20) {
    event_id
    title
    attendee_count: count(~attends)
  }
}
"""
    return _query(query_text)


def get_user(user_id):
    query_text = f"""
{{
  users(func: eq(user_id, "{_escape(user_id)}"), first: 1) {{
    uid
    user_id
    username
    location
  }}
}}
"""
    users = _query(query_text).get("users", [])
    return users[0] if users else None


def edge_exists(source_predicate, source_id, edge_name, target_predicate, target_id):
    query_text = f"""
{{
  nodes(func: eq({source_predicate}, "{_escape(source_id)}"), first: 1) {{
    {edge_name} @filter(eq({target_predicate}, "{_escape(target_id)}")) {{
      uid
    }}
  }}
}}
"""
    nodes = _query(query_text).get("nodes", [])
    return bool(nodes and nodes[0].get(edge_name))


def _uid_for(predicate, value):
    query_text = f"""
    {{
      nodes(func: eq({predicate}, "{_escape(value)}"), first: 1) {{
        uid
      }}
    }}
    """
    nodes = _query(query_text).get("nodes", [])
    return nodes[0]["uid"] if nodes else None


def _query(query_text):
    response = requests.post(
        f"{DGRAPH_ALPHA_URL}/query",
        data=query_text,
        headers={"Content-Type": "application/dql"},
    )
    payload = _check_response(response)
    return payload.get("data", {})


def _mutate(rdf):
    mutation_text = "{\nset {\n" + rdf.strip() + "\n}\n}"
    response = requests.post(
        f"{DGRAPH_ALPHA_URL}/mutate?commitNow=true",
        data=mutation_text,
        headers={"Content-Type": "application/rdf"},
    )
    return _check_response(response)


def _check_response(response):
    try:
        payload = response.json()
    except ValueError:
        payload = {"text": response.text}

    if not response.ok:
        raise RuntimeError(f"Dgraph error {response.status_code}: {payload}")
    if isinstance(payload, dict) and payload.get("errors"):
        raise RuntimeError(f"Dgraph error: {payload['errors']}")
    return payload


def _escape(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def _blank_name(value):
    return "".join(char if char.isalnum() else "_" for char in str(value))


def _node(uid):
    if uid.startswith("_:"):
        return uid
    return f"<{uid}>"
