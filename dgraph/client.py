import json
import os

import requests

from dgraph import dgraph_model
from event_log import log_event


PROJECT_API_URL = os.getenv("PROJECT_API_URL", "http://localhost:8000")
SESSION_FILE = ".session.json"


def get_authenticated_user():
    if not os.path.exists(SESSION_FILE):
        print("Error: User not logged in. Please login first.")
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)


def get_session_user_if_present():
    if not os.path.exists(SESSION_FILE):
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)


def ensure_session_user_in_dgraph(user):
    # The logged-in user comes from MongoDB, but Dgraph has its own graph nodes.
    # Before graph queries, we copy the session user into Dgraph using the same user_id.
    full_user = get_full_mongo_user(user)
    dgraph_model.ensure_user_from_session(full_user)
    return full_user


def get_full_mongo_user(user):
    # Login currently stores only a small session. This fetch gets location/preferences from Mongo.
    if user.get("email"):
        try:
            response = requests.get(PROJECT_API_URL + "/user", params={"email": user["email"]})
            if response.ok and response.json():
                mongo_user = response.json()[0]
                return {
                    "user_id": user["user_id"],
                    "username": mongo_user.get("username", user.get("username")),
                    "email": user.get("email"),
                    "location": mongo_user.get("location", "Guadalajara"),
                    "preferences": mongo_user.get("preferences", "prayer"),
                }
        except requests.RequestException:
            pass
    return user


def dgraph_setup(args):
    # Setup talks directly to Dgraph because it is an admin command, not a normal user action.
    result = dgraph_model.setup_schema()
    print(result["message"])


def dgraph_seed(args):
    # This loads a small demo graph for testing the project requirements.
    result = dgraph_model.seed_graph()
    print(result["message"])


def follow_user(args):
    user = get_authenticated_user()
    if not user:
        return
    ensure_session_user_in_dgraph(user)

    payload = {
        "user_id": user["user_id"],
        "target_user_id": args.user_id,
    }
    response = requests.post(PROJECT_API_URL + "/graph/follow", json=payload)
    if response.ok:
        log_event(
            "follow",
            user_id=user["user_id"],
            username=user.get("username"),
            metadata={"target_user_id": args.user_id},
        )
    _print_response(response)


def recommend_users(args):
    user = get_authenticated_user()
    if not user:
        return
    ensure_session_user_in_dgraph(user)

    response = requests.get(
        PROJECT_API_URL + "/graph/recommend-users",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def recommend_users_by_location(args):
    user = get_authenticated_user()
    if not user:
        return
    ensure_session_user_in_dgraph(user)

    response = requests.get(
        PROJECT_API_URL + "/graph/recommend-users-by-location",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def local_events(args):
    user = get_authenticated_user()
    if not user:
        return
    ensure_session_user_in_dgraph(user)

    response = requests.get(
        PROJECT_API_URL + "/graph/local-events",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def attend_event(args):
    user = get_authenticated_user()
    if not user:
        return
    ensure_session_user_in_dgraph(user)

    payload = {
        "user_id": user["user_id"],
        "event_id": args.event_id,
    }
    response = requests.post(PROJECT_API_URL + "/graph/attend", json=payload)
    if response.ok:
        log_event(
            "attend_event",
            user_id=user["user_id"],
            username=user.get("username"),
            metadata={"event_id": args.event_id},
        )
    _print_response(response)


def recommend_events(args):
    user = get_authenticated_user()
    if not user:
        return
    ensure_session_user_in_dgraph(user)

    response = requests.get(
        PROJECT_API_URL + "/graph/recommend-events",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def graph_summary(args):
    user = get_session_user_if_present()
    if user:
        ensure_session_user_in_dgraph(user)
    response = requests.get(PROJECT_API_URL + "/graph/summary")
    _print_response(response)


def _print_response(response):
    if response.ok:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Dgraph request failed: {response.status_code} - {response.text}")
