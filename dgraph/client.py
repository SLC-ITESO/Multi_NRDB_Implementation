import json
import os

import requests

from dgraph import dgraph_model


PROJECT_API_URL = os.getenv("PROJECT_API_URL", "http://localhost:8000")
SESSION_FILE = ".session.json"


def get_authenticated_user():
    if not os.path.exists(SESSION_FILE):
        print("Error: User not logged in. Please login first.")
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)


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

    payload = {
        "user_id": user["user_id"],
        "target_user_id": args.user_id,
    }
    response = requests.post(PROJECT_API_URL + "/graph/follow", json=payload)
    _print_response(response)


def recommend_users(args):
    user = get_authenticated_user()
    if not user:
        return

    response = requests.get(
        PROJECT_API_URL + "/graph/recommend-users",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def recommend_users_by_location(args):
    user = get_authenticated_user()
    if not user:
        return

    response = requests.get(
        PROJECT_API_URL + "/graph/recommend-users-by-location",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def local_events(args):
    user = get_authenticated_user()
    if not user:
        return

    response = requests.get(
        PROJECT_API_URL + "/graph/local-events",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def attend_event(args):
    user = get_authenticated_user()
    if not user:
        return

    payload = {
        "user_id": user["user_id"],
        "event_id": args.event_id,
    }
    response = requests.post(PROJECT_API_URL + "/graph/attend", json=payload)
    _print_response(response)


def recommend_events(args):
    user = get_authenticated_user()
    if not user:
        return

    response = requests.get(
        PROJECT_API_URL + "/graph/recommend-events",
        params={"user_id": user["user_id"]},
    )
    _print_response(response)


def graph_summary(args):
    response = requests.get(PROJECT_API_URL + "/graph/summary")
    _print_response(response)


def _print_response(response):
    if response.ok:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Dgraph request failed: {response.status_code} - {response.text}")
