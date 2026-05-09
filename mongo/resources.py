#!/usr/bin/env python3
import logging
import os
import requests
from datetime import datetime, timedelta
import falcon
from bson.objectid import ObjectId


# Set logger
log = logging.getLogger()
log.setLevel('INFO')
handler = logging.FileHandler('multidrdb_mongo.log')
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
log.addHandler(handler)



class userResource:
    def __init__(self, db):
        self.db = db

    pass

class contentResource:
    pass

class noteResource:
    pass


"""
 =================
 USERS COLLECTION
 =================
 Patterns used:
 - Attribute Pattern      -> preferences
 - Extended Reference     -> embedded recent activity/content references
 - Subset Pattern         -> only recent interactions embedded

 Why?
 Users are read constantly during login/session/profile operations.
 Small frequently-used data is embedded.
 Large/high-growth data stays separated.
"""

users_types = {
    "_id": ObjectId,

    # Core identity
    "username": str,
    "email": str, # UNIQUE INDEX
    "password_hash": str,

    # Profile
    "age": int,
    "location": str,

    # Attribute Pattern
    # Flexible/extensible preferences
    "preferences": [
        {
            "name": str,
            "category": str, # prayer, meditation, bible, etc
            # "added_at": datetime
        }
    ],
    # Authorization
    "role": str, # admin or user
    # Session/Auth metadata
    "last_login": datetime,
    "created_at": datetime,
    "updated_at": datetime,

    # Extended Reference Pattern
    # Only RECENT interactions embedded
    "recent_likes": [
        {
            "content_id": ObjectId,
            "title": str,
            # "liked_at": datetime
        }
    ],
    "recent_comments": [
        {
            "comment_id": ObjectId,
            "content_id": ObjectId,
            "content_title": str,
            "comment_preview": str,
            # "created_at": datetime
        }
    ]
}
"""
 =================
 CONTENT COLLECTION
 =================
 Patterns used:
 - Extended Reference Pattern
 - Subset Pattern

 Why?
 Content is frequently read.
 We embed ONLY recent comments/likes.
 Full comments remain in separate collection.
"""
content_types = {
    "_id": ObjectId,

    # Content info
    "title": str,
    "type": str, # text, image, audio, etc

    # Creator reference
    "created_by": {
        "user_id": ObjectId,
        "username": str
    },

    # Metrics
    "likes_count": int,
    "comments_count": int,
    "shares_count": int,

    # Extended Reference Pattern
    # Only recent likes
    "recent_likes": [
        {
            "user_id": ObjectId,
            "username": str,
            # "liked_at": datetime
        }
    ],

    # Subset Pattern
    # Only recent comments embedded
    "recent_comments": [
        {
            "comment_id": ObjectId,
            "user_id": ObjectId,
            "username": str,
            "text": str,
            # "created_at": datetime
        }
    ],

    "created_at": datetime
}
"""
 =================
 COMMENTS COLLECTION
 =================
 Why?
 Comments grow unbounded.
 Store fully separated.
 Embed lightweight references for fast reads.
"""

comments_types = {
    "_id": ObjectId,

    # Content reference
    "content": {
        "content_id": ObjectId,
        "title": str
    },

    # User reference
    "user": {
        "user_id": ObjectId,
        "username": str
    },

    "text": str,

    "created_at": datetime
}
"""
 =================
 CONTENT LIKES COLLECTION
 =================
 Why separate?
 Prevent duplicate likes cleanly.
 Enables UNIQUE compound indexes.

 UNIQUE INDEX:
 (user_id, content_id)
"""

likes_types = {
    "_id": ObjectId,

    "user": {
        "user_id": ObjectId,
        "username": str
    },

    "content": {
        "content_id": ObjectId,
        "title": str
    },

    "created_at": datetime
}

"""
 =================
 INTERNAL SHARES COLLECTION
 =================
 FR-13
"""

shares_types = {
    "_id": ObjectId,

    "from_user": {
        "user_id": ObjectId,
        "username": str
    },

    "to_user": {
        "user_id": ObjectId,
        "username": str
    },

    "content": {
        "content_id": ObjectId,
        "title": str
    },

    "created_at": datetime
}

"""
 =================
 EXTERNAL SHARES COLLECTION
 =================
 FR-18

 Cassandra handles logging/analytics.
 Mongo stores operational/share metadata.
"""

external_shares_types = {
  "_id": ObjectId,

  "user": {
    "user_id": ObjectId,
    "username": str
  },

  "content": {
    "content_id": ObjectId,
    "title": str
  },

  "platform": str,  # Twitter, Facebook, Insta
  "created_at": datetime
}

"""
 =================
 NOTES COLLECTION
 =================
 Patterns used:
 - Extended Reference Pattern

 Why?
 Notes belong to users.
 Can grow indefinitely.
 Keep separated from users collection.
"""

notes_types = {
    "_id": ObjectId,

    "user": {
        "user_id": ObjectId,
        "username": str
    },

    "title": str,
    "text": str,

    "created_at": datetime,
    "updated_at": datetime
}

""" 
 ==========================================
 INDEXES (MAYBE)
 ==========================================
"""

mongo_indexes = {

    "users": [
        {"email": 1},                 # UNIQUE
        {"username": 1},              # UNIQUE
        {"location": 1},
        {"preferences.name": 1}
    ],

    "content": [
        {"created_by.user_id": 1},
        {"created_at": -1},
        {"type": 1}
    ],

    "comments": [
        {"content.content_id": 1},
        {"user.user_id": 1},
        {"created_at": -1}
    ],

    "likes": [
        {
            "user.user_id": 1,
            "content.content_id": 1
        }  # UNIQUE
    ],

    "shares": [
        {"from_user.user_id": 1},
        {"to_user.user_id": 1},
        {"content.content_id": 1}
    ],

    "external_shares": [
        {"platform": 1},
        {"user.user_id": 1}
    ],

    "notes": [
        {"user.user_id": 1},
        {"created_at": -1}
    ],

    "sessions": [
        {"session_token": 1},         # UNIQUE
        {"user.user_id": 1},
        {"expires_at": 1}
    ]
}