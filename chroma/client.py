import json
import os

import requests

from chroma import chroma_model


PROJECT_API_URL = os.getenv("PROJECT_API_URL", "http://localhost:8000")
SESSION_FILE = ".session.json"


def get_authenticated_user():
    if not os.path.exists(SESSION_FILE):
        print("Error: User not logged in. Please login first.")
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)


def chroma_setup(args):
    # Setup creates the local Chroma collection.
    result = chroma_model.setup_collection()
    print(result["message"])


def chroma_seed(args):
    # Seed loads sample content documents with embeddings.
    result = chroma_model.seed_collection()
    print(f"{result['message']} ({result['count']} documents)")


def semantic_search(args):
    response = requests.get(
        PROJECT_API_URL + "/chroma/search",
        params={"query": args.query, "limit": args.limit},
    )
    _print_response(response)


def rag_context(args):
    response = requests.get(
        PROJECT_API_URL + "/chroma/rag-context",
        params={"query": args.query, "limit": args.limit},
    )
    _print_response(response)


def recommend_content(args):
    # This command uses the logged-in user's preferences when available.
    user = get_authenticated_user()
    if user and user.get("preferences"):
        preferences = user["preferences"]
    else:
        preferences = args.preferences

    if not preferences:
        print("Error: add --preferences or login with preferences in .session.json")
        return

    if isinstance(preferences, list):
        preferences = " ".join(preferences)

    response = requests.get(
        PROJECT_API_URL + "/chroma/recommend-content",
        params={"preferences": preferences, "limit": args.limit},
    )
    _print_response(response)


def _print_response(response):
    if response.ok:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Chroma request failed: {response.status_code} - {response.text}")
