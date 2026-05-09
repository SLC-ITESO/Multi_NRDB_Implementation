import os
import requests
import hashlib
import json

from dns.dnssec import PRIVATEDNS

PROJECT_API_URL = os.getenv("PROJECT_API_URL", "http://localhost:8000")
SESSION_FILE = ".session.json"

def get_authenticated_user():
    if not os.path.exists(SESSION_FILE):
        print("Error: User not logged in. Please login first.")
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)

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
        print(f"User {user_info['username']} logged in successfully")
    else:
        print(f"Login failed {x.status_code} - {x.text}")

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
    print(f"Adding pref for user {user['user_id']}: {args}")

def mongo_rem_pref(args):
    user = get_authenticated_user()
    if not user:
        return
    print(f"Removing pref for user {user['user_id']}: {args}")

def mongo_create_content(args):
    user = get_authenticated_user()
    if not user:
        return
    # This might require admin check too? Users should be able to create content
    print(f"Creating content by {user['user_id']}: {args}")

def mongo_like_content(args):
    user = get_authenticated_user()
    if not user:
        return
    print(f"Like content by {user['user_id']}: {args}")

def mongo_comment_content(args):
    user = get_authenticated_user()
    if not user:
        return
    print(f"Commenting content by {user['user_id']}: {args}")

def mongo_get_comments(args):
    print(args)
    return None

def mongo_get_own_comments(args):
    print(args)
    return None

def mongo_share_content(args):
    print(args)
    return None

def mongo_share_content_ext(args):
    print(args)
    return None

def mongo_create_note(args):
    print(args)
    return None

def mongo_get_notes(args):
    print(args)
    return None

def mongo_update_note(args):
    print(args)
    return None

def mongo_delete_note(args):
    print(args)
    return None