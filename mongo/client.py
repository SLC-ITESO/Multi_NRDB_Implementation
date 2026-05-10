import os
from traceback import print_tb

import requests
import hashlib
import json

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
        print(f"Content '{content['title']}' liked successfully!")
    else:
        print(f"Failed to like content: {x.status_code} - {x.text}")

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