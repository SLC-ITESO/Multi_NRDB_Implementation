import os
from traceback import print_tb
import sys
import logging

import requests
import hashlib
import json

PROJECT_API_URL = os.getenv("PROJECT_API_URL", "http://localhost:8000")
SESSION_FILE = ".session.json"
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
CASSANDRA_DIR = os.path.join(PROJECT_ROOT, "cassandra")

if CASSANDRA_DIR not in sys.path:
    sys.path.insert(0, CASSANDRA_DIR)

try:
    import fixtures as cassandra_fixtures
except Exception as exc:
    cassandra_fixtures = None
    CASSANDRA_IMPORT_ERROR = exc
else:
    CASSANDRA_IMPORT_ERROR = None

log = logging.getLogger(__name__)

def get_authenticated_user():
    if not os.path.exists(SESSION_FILE):
        print("Error: User not logged in. Please login first.")
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)


def _log_cassandra_session(user_id, event_type, metadata=None):
    if cassandra_fixtures is None:
        if CASSANDRA_IMPORT_ERROR is not None:
            log.warning("Cassandra fixtures import failed: %s", CASSANDRA_IMPORT_ERROR)
        return

    try:
        cassandra_fixtures.log_session_event(user_id, event_type, metadata=metadata)
    except Exception as exc:
        log.warning("Cassandra session logging failed: %s", exc)
        print(f"Warning: Mongo action succeeded, but Cassandra session logging failed: {exc}")


def _log_cassandra_activity(user_id, activity_type, content_id=None, metadata=None):
    if cassandra_fixtures is None:
        if CASSANDRA_IMPORT_ERROR is not None:
            log.warning("Cassandra fixtures import failed: %s", CASSANDRA_IMPORT_ERROR)
        return

    try:
        cassandra_fixtures.log_activity_event(
            user_id,
            activity_type,
            content_id=content_id,
            metadata=metadata,
        )
    except Exception as exc:
        log.warning("Cassandra activity logging failed: %s", exc)
        print(f"Warning: Mongo action succeeded, but Cassandra activity logging failed: {exc}")

def mongo_register(args):

    endpoint = PROJECT_API_URL + "/user"
    # Hash password using SHA-256
    password_hash = hashlib.sha256(
        args.password.encode("utf-8")
    ).hexdigest()

    user = {
        "username": args.username,
        "email": args.email,
        "password_hash": password_hash,
        "age": args.age,
        "location": args.location,
        "preferences": args.preferences
    }
    print("USER CLIENT.PY")
    print(user)
    x = requests.post(endpoint, json=user)

    if x.ok:
        print(f"User {user['username']} created with id {x.json()['_id']}")
    else:
        print(f"Failed to create user {x.status_code} - {x.text}")

def mongo_login(args):
    endpoint = PROJECT_API_URL + "/login"
    password_hash = hashlib.sha256(
        args.password.encode("utf-8")
    ).hexdigest()

    payload = {
        "email": args.email,
        "password_hash": password_hash
    }
    
    x = requests.post(endpoint, json=payload)
    if x.ok:
        user_info = x.json()
        with open(SESSION_FILE, "w") as f:
            json.dump(user_info, f)
        _log_cassandra_session(
            user_info["user_id"],
            "login",
            metadata={
                "source": "mongo_login",
                "username": user_info["username"],
                "email": user_info["email"],
            },
        )
        print(f"User {user_info['username']} logged in successfully")
    else:
        print(f"Login failed {x.status_code} - {x.text}")


def mongo_logout():
    user = get_authenticated_user()
    if not user:
        return

    _log_cassandra_session(
        user["user_id"],
        "logout",
        metadata={
            "source": "mongo_logout",
            "username": user.get("username"),
            "email": user.get("email"),
        },
    )
    os.remove(SESSION_FILE)
    print("User logged off")

def mongo_update(args):
    user = get_authenticated_user()
    if not user:
        return
    
    update_data = {}
    print("--- Update User Profile ---")
    
    # Password
    if input("Update password? (y/n): ").lower() == 'y':
        password = input("Enter new password: ")
        update_data['password_hash'] = hashlib.sha256(password.encode("utf-8")).hexdigest()
        
    # Age
    if input("Update age? (y/n): ").lower() == 'y':
        try:
            update_data['age'] = int(input("Enter new age: "))
        except ValueError:
            print("Invalid age. Age must be an integer.")
            return
        
    # Location
    if input("Update location? (y/n): ").lower() == 'y':
        update_data['location'] = input("Enter new location: ")
        
    # Preferences
    if input("Update preferences? (y/n): ").lower() == 'y':
        prefs = input("Enter new preferences (comma-separated): ")
        update_data['preferences'] = [p.strip() for p in prefs.split(',')]
        
    if not update_data:
        print("No fields to update.")
        return

    # Call PUT
    endpoint = PROJECT_API_URL + f"/user/{user['user_id']}"
    x = requests.put(endpoint, json=update_data)
    
    if x.ok:
        print("User updated successfully!")
    else:
        print(f"Update failed: {x.status_code} - {x.text}")

def mongo_add_pref(args):
    user = get_authenticated_user()
    if not user:
        return

    update_data = {}

    prefs = input("Enter new preferences (comma-separated): ")
    update_data['preferences'] = [p.strip() for p in prefs.split(',')]

    endpoint = PROJECT_API_URL + f"/user/{user['user_id']}"
    x = requests.put(endpoint, json=update_data)

    if x.ok:
        print("User updated successfully!")
    else:
        print(f"Update failed: {x.status_code} - {x.text}")
    print(f"Adding pref for user {user['user_id']}: {args}")

def mongo_rem_pref(args):
    user = get_authenticated_user()
    if not user:
        return

    # 1. Fetch current preferences
    endpoint = PROJECT_API_URL + "/user"
    response = requests.get(endpoint, params={"email": user['email']})
    if not response.ok:
        print(f"Failed to fetch user profile: {response.status_code}")
        return
    
    users = response.json()
    if not users:
        print("User not found.")
        return
    
    current_user = users[0]
    preferences = current_user.get("preferences", [])
    
    if not preferences:
        print("No preferences to remove.")
        return
    
    # 2. List preferences
    print("--- Current Preferences ---")
    for i, pref in enumerate(preferences):
        print(f"{i + 1}. {pref}")
    
    # 3. Prompt for removal
    try:
        choice = int(input("Enter the number of the preference to remove: "))
        if choice < 1 or choice > len(preferences):
            print("Invalid choice.")
            return
        
        # 4. Remove and update
        removed_pref = preferences.pop(choice - 1)
        
        endpoint = PROJECT_API_URL + f"/user/{user['user_id']}"
        update_data = {"preferences": preferences}
        x = requests.put(endpoint, json=update_data)
        
        if x.ok:
            print(f"Preference '{removed_pref}' removed successfully!")
        else:
            print(f"Update failed: {x.status_code} - {x.text}")
            
    except ValueError:
        print("Invalid input. Please enter a number.")

def mongo_create_content(args):
    user = get_authenticated_user()
    if not user:
        return
    
    endpoint = PROJECT_API_URL + "/content"
    
    content = {
        "title": args.title,
        "type": args.type,
        "created_by": {
            "user_id": user["user_id"],
            "username": user["username"]
        },
        "likes_count": 0,
        "comments_count": 0,
        "shares_count": 0,
        "recent_likes": [],
        "recent_comments": []
    }
    
    x = requests.post(endpoint, json=content)
    
    if x.ok:
        print(f"Content '{args.title}' created successfully!")
    else:
        print(f"Failed to create content: {x.status_code} - {x.text}")

def mongo_like_content(args):
    user = get_authenticated_user()
    if not user:
        return

    # 1. Fetch content to get title
    endpoint_content = PROJECT_API_URL + "/content"
    response = requests.get(endpoint_content, params={"content_id": args.content_id})
    if not response.ok:
        print(f"Failed to fetch content: {response.status_code}")
        return

    contents = response.json()
    if not contents:
        print("Content not found.")
        return

    content = contents[0]

    # 2. Like content
    endpoint_like = PROJECT_API_URL + "/likes"
    like_data = {
        "content": {
            "content_id": args.content_id,
            "title": content["title"]
        },
        "user": {
            "user_id": user["user_id"],
            "username": user["username"]
        }
    }

    x = requests.post(endpoint_like, json=like_data)

    if x.ok:
        _log_cassandra_activity(
            user["user_id"],
            "like",
            content_id=args.content_id,
            metadata={
                "source": "mongo_like_content",
                "content_title": content["title"],
                "username": user["username"],
            },
        )
        print(f"Content '{content['title']}' liked successfully!")
    else:
        print(f"Failed to like content: {x.status_code} - {x.text}")

def mongo_comment_content(args):
    user = get_authenticated_user()
    if not user:
        return

    # 1. Fetch content
    endpoint_content = PROJECT_API_URL + "/content"
    response = requests.get(endpoint_content, params={"content_id": args.content_id})
    if not response.ok:
        print(f"Failed to fetch content: {response.status_code}")
        return

    contents = response.json()
    if not contents:
        print("Content not found.")
        return

    content = contents[0]

    # 2. Post comment
    endpoint_comment = PROJECT_API_URL + "/comment"
    comment_data = {
        "content": {
            "content_id": args.content_id,
            "title": content["title"]
        },
        "user": {
            "user_id": user["user_id"],
            "username": user["username"]
        },
        "text": args.text
    }

    x = requests.post(endpoint_comment, json=comment_data)

    if x.ok:
        _log_cassandra_activity(
            user["user_id"],
            "comment",
            content_id=args.content_id,
            metadata={
                "source": "mongo_comment_content",
                "content_title": content["title"],
                "username": user["username"],
                "text": args.text,
            },
        )
        print(f"Commented on content '{content['title']}' successfully!")
    else:
        print(f"Failed to comment: {x.status_code} - {x.text}")

def mongo_get_comments(args):
    endpoint = PROJECT_API_URL + "/comment"
    response = requests.get(endpoint, params={"content_id": args.content_id})
    if response.ok:
        comments = response.json()
        if not comments:
            print("No comments found.")
            return
        for c in comments:
            print(f"Comment ID: {c['_id']}, User: {c['user']['username']}, comm: {c['text']}")
    else:
        print(f"Failed to fetch comments: {response.status_code} - {response.text}")

def mongo_get_own_comments(args):
    user = get_authenticated_user()
    if not user:
        return

    endpoint = PROJECT_API_URL + "/comment"
    response = requests.get(endpoint, params={"user_id": user['user_id']})
    if response.ok:
        comments = response.json()
        if not comments:
            print("No comments found.")
            return
        for c in comments:
            print(f"Content: {c['content']['title']}, Text: {c['text']}")
    else:
        print(f"Failed to fetch own comments: {response.status_code} - {response.text}")

def mongo_share_content(args):
    user = get_authenticated_user()
    if not user:
        return

    # 1. Fetch content
    endpoint_content = PROJECT_API_URL + "/content"
    response = requests.get(endpoint_content, params={"content_id": args.content_id})
    if not response.ok:
        print(f"Failed to fetch content: {response.status_code}")
        return

    contents = response.json()
    if not contents:
        print("Content not found.")
        return
    content = contents[0]

    # 2. Fetch target user
    endpoint_user = PROJECT_API_URL + "/user"
    response = requests.get(endpoint_user, params={"user_id": args.user_id})
    if not response.ok:
        print(f"Failed to fetch target user: {response.status_code}")
        return

    users = response.json()
    if not users:
        print("Target user not found.")
        return
    target_user = users[0]

    # 3. Post share
    endpoint_share = PROJECT_API_URL + "/share"
    share_data = {
        "from_user": {
            "user_id": user["user_id"],
            "username": user["username"]
        },
        "to_user": {
            "user_id": target_user["_id"],
            "username": target_user["username"]
        },
        "content": {
            "content_id": args.content_id,
            "title": content["title"]
        }
    }

    x = requests.post(endpoint_share, json=share_data)
    if x.ok:
        _log_cassandra_activity(
            user["user_id"],
            "share_internal",
            content_id=args.content_id,
            metadata={
                "source": "mongo_share_content",
                "content_title": content["title"],
                "from_username": user["username"],
                "to_user_id": target_user["_id"],
                "to_username": target_user["username"],
            },
        )
        print(f"Content '{content['title']}' shared successfully with {target_user['username']}!")
    else:
        print(f"Failed to share: {x.status_code} - {x.text}")

def mongo_share_content_ext(args):
    user = get_authenticated_user()
    if not user:
        return

    # 1. Fetch content
    endpoint_content = PROJECT_API_URL + "/content"
    response = requests.get(endpoint_content, params={"content_id": args.content_id})
    if not response.ok:
        print(f"Failed to fetch content: {response.status_code}")
        return

    contents = response.json()
    if not contents:
        print("Content not found.")
        return
    content = contents[0]

    # 2. Post external share
    endpoint_share = PROJECT_API_URL + "/external_share"
    share_data = {
        "user": {
            "user_id": user["user_id"],
            "username": user["username"]
        },
        "content": {
            "content_id": args.content_id,
            "title": content["title"]
        },
        "platform": args.platform
    }

    x = requests.post(endpoint_share, json=share_data)
    if x.ok:
        _log_cassandra_activity(
            user["user_id"],
            "share_external",
            content_id=args.content_id,
            metadata={
                "source": "mongo_share_content_ext",
                "content_title": content["title"],
                "username": user["username"],
                "platform": args.platform,
            },
        )
        print(f"Content '{content['title']}' shared on {args.platform} successfully!")
    else:
        print(f"Failed to share externally: {x.status_code} - {x.text}")

def mongo_create_note(args):
    user = get_authenticated_user()
    if not user:
        return
        
    endpoint = PROJECT_API_URL + "/notes"
    data = {
        "user": {
            "user_id": user['user_id'],
            "username": user['username']
        },
        "title": args.title,
        "text": args.text
    }
    
    response = requests.post(endpoint, json=data)
    if response.ok:
        note = response.json()
        _log_cassandra_activity(
            user["user_id"],
            "note",
            metadata={
                "source": "mongo_create_note",
                "note_id": note["_id"],
                "title": args.title,
                "username": user["username"],
            },
        )
        print(f"Note created with id {response.json()['_id']}")
    else:
        print(f"Failed to create note: {response.status_code} - {response.text}")

def mongo_get_notes(args):
    user = get_authenticated_user()
    if not user:
        return
    
    endpoint = PROJECT_API_URL + "/notes"
    response = requests.get(endpoint, params={"user_id": user['user_id']})
    
    if response.ok:
        notes = response.json()
        if not notes:
            print("No notes found.")
            return
        for n in notes:
            print(f"ID: {n['_id']}, Title: {n['title']}, Text: {n['text']}, Created: {n['created_at']}")
    else:
        print(f"Failed to get notes: {response.status_code} - {response.text}")

def mongo_update_note(args):
    user = get_authenticated_user()
    if not user:
        return
        
    endpoint = PROJECT_API_URL + f"/notes/{args.note_id}"
    data = {}
    if args.title:
        data['title'] = args.title
    if args.text:
        data['text'] = args.text
        
    if not data:
        print("No fields to update.")
        return
        
    response = requests.put(endpoint, json=data)
    if response.ok:
        print("Note updated successfully!")
    else:
        print(f"Failed to update note: {response.status_code} - {response.text}")

def mongo_delete_note(args):
    user = get_authenticated_user()
    if not user:
        return
        
    endpoint = PROJECT_API_URL + f"/notes/{args.note_id}"
    
    response = requests.delete(endpoint)
    if response.ok:
        print("Note deleted successfully!")
    else:
        print(f"Failed to delete note: {response.status_code} - {response.text}")

def mongo_get_prof(args):
    user = get_authenticated_user()
    if not user:
        return

    endpoint = PROJECT_API_URL + "/user"
    response = requests.get(endpoint, params={"email": user['email']})
    if not response.ok:
        print(f"Failed to fetch user profile: {response.status_code}")
        return

    users = response.json()
    if not users:
        print("User not found.")
        return

    current_user = users[0]
    for key, value in current_user.items():
        if key == "password_hash":
            continue

        pretty_key = key.replace("_", " ").title()
        # Handle Lists
        if isinstance(value, list):
            if not value:
                value = "None"
            # Check if the first item is a dictionary (like preferences or likes)
            elif isinstance(value[0], dict):
                # Extract the 'name' or 'title' to make it readable
                items = []
                for item in value:
                    # Use .get() to avoid KeyErrors; fallback to string representation
                    label = item.get("name") or item.get("title") or str(item)
                    items.append(label)
                value = ", ".join(items)
            else:
                # It's a normal list of strings/numbers
                value = ", ".join(map(str, value))

        print(f"{pretty_key}: {value}")
