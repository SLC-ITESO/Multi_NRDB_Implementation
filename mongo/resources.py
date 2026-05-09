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


class UserResource:
    def __init__(self, db):
        self.db = db

    async def on_get(self, req, resp):
        filters = {}
        if 'email' in req.params:
            filters['email'] = req.params['email']
        if 'username' in req.params:
            filters['username'] = req.params['username']
        if 'location' in req.params:
            filters['location'] = req.params['location']
        
        users_cursor = self.db.users.find(filters)
        users = []
        for user in users_cursor:
            user["_id"] = str(user["_id"])
            users.append(user)
        
        resp.media = users
        resp.status = falcon.HTTP_200
        log.info("Users retrieved")

    async def on_post(self, req, resp):
        data = await req.media

        print("DATA:")
        print(data)

        required_fields = [
            'username',
            'email',
            'password_hash',
            'age',
            'location',
            'preferences'
        ]

        for field in required_fields:
            if field not in data:
                raise falcon.HTTPBadRequest(
                    title='Missing field',
                    description=f'{field} is required'
                )

        if self.db.users.find_one({"email": data["email"]}):
            raise falcon.HTTPConflict(
                title='Email already registered',
                description='The provided email is already in use.'
            )

        now = datetime.now()

        user = {
            "username": data["username"],
            "email": data["email"],
            "password_hash": data["password_hash"],
            "age": data["age"],
            "location": data["location"],
            "preferences": data["preferences"],
            "created_at": now,
            "updated_at": now
        }

        print("USER:")
        print(user)

        result = self.db.users.insert_one(user)

        # Conversion of ObjectId to string
        user["_id"] = str(result.inserted_id)

        # Conversion of datetime objects to JSON-safe strings
        user["created_at"] = user["created_at"].isoformat()
        user["updated_at"] = user["updated_at"].isoformat()

        resp.media = user
        resp.status = falcon.HTTP_201

        log.info(f"User registered: {user['username']}")

    async def on_put(self, req, resp, user_id):
        data = await req.media
        update_doc = {}
        if 'password_hash' in data:
            update_doc['password_hash'] = data['password_hash']
        if 'age' in data:
            update_doc['age'] = data['age']
        if 'location' in data:
            update_doc['location'] = data['location']
        if 'preferences' in data:
            update_doc['preferences'] = data['preferences']
        
        update_doc['updated_at'] = datetime.now()
            
        if len(update_doc) == 1:
            raise falcon.HTTPBadRequest(title='No fields to update')
            
        result = self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )
        if result.matched_count == 0:
            raise falcon.HTTPNotFound()
        
        resp.status = falcon.HTTP_200
        log.info(f"User updated: {user_id}")

class AuthResource:
    def __init__(self, db):
        self.db = db

    async def on_post(self, req, resp):
        data = await req.media
        if 'email' not in data or 'password_hash' not in data:
            raise falcon.HTTPBadRequest(title='Missing fields', description='email and password_hash are required')

        user = self.db.users.find_one({"email": data['email']})
        if not user or user['password_hash'] != data['password_hash']:
            raise falcon.HTTPUnauthorized(description='Invalid email or password')

        resp.media = {
            "user_id": str(user["_id"]),
            "username": user["username"],
            "email": user["email"]
        }
        resp.status = falcon.HTTP_200
        log.info(f"User logged in: {user['username']}")

class NotesResource:
    def __init__(self, db):
        self.db = db

    async def on_get(self, req, resp):
        filters = {}
        if 'user_id' in req.params:
            filters['user.user_id'] = ObjectId(req.params['user_id'])
            
        notes_cursor = self.db.notesResource.find(filters)
        notes = []
        for note in notes_cursor:
            note["_id"] = str(note["_id"])
            if "user" in note and "user_id" in note["user"]:
                note["user"]["user_id"] = str(note["user"]["user_id"])
            notes.append(note)
            
        resp.media = notes
        resp.status = falcon.HTTP_200
        log.info("Notes retrieved")

    async def on_post(self, req, resp):
        data = await req.media
        required_fields = ['user', 'title', 'text']
        for field in required_fields:
            if field not in data:
                raise falcon.HTTPBadRequest(title='Missing field', description=f'{field} is required')

        if 'user_id' not in data['user'] or 'username' not in data['user']:
             raise falcon.HTTPBadRequest(title='Missing user_id/username in user')

        now = datetime.now()
        note = {
            "user": {
                "user_id": ObjectId(data["user"]["user_id"]),
                "username": data["user"]["username"]
            },
            "title": data["title"],
            "text": data["text"],
            "created_at": now,
            "updated_at": now
        }
        result = self.db.notesResource.insert_one(note)
        note["_id"] = str(result.inserted_id)
        note["user"]["user_id"] = str(note["user"]["user_id"])
        
        resp.media = note
        resp.status = falcon.HTTP_201
        log.info(f"Note created: {note['_id']}")

    async def on_put(self, req, resp, note_id):
        data = await req.media
        update_doc = {}
        if 'title' in data:
            update_doc['title'] = data['title']
        if 'text' in data:
            update_doc['text'] = data['text']
        update_doc['updated_at'] = datetime.now()
            
        if not update_doc:
            raise falcon.HTTPBadRequest(title='No fields to update')
            
        result = self.db.notesResource.update_one(
            {"_id": ObjectId(note_id)},
            {"$set": update_doc}
        )
        if result.matched_count == 0:
            raise falcon.HTTPNotFound()
        
        resp.status = falcon.HTTP_200
        log.info(f"Note updated: {note_id}")

    async def on_delete(self, req, resp, note_id):
        result = self.db.notesResource.delete_one({"_id": ObjectId(note_id)})
        if result.deleted_count == 0:
            raise falcon.HTTPNotFound()
            
        resp.status = falcon.HTTP_204
        log.info(f"Note deleted: {note_id}")

class ContentResource:
    def __init__(self, db):
        self.db = db

    async def on_get(self, req, resp):
        filters = {}
        if 'type' in req.params:
            filters['type'] = req.params['type']
        if 'user_id' in req.params:
            filters['created_by.user_id'] = ObjectId(req.params['user_id'])
        
        contents_cursor = self.db.content.find(filters)
        contents = []
        for content in contents_cursor:
            content["_id"] = str(content["_id"])
            if "created_by" in content and "user_id" in content["created_by"]:
                content["created_by"]["user_id"] = str(content["created_by"]["user_id"])
            contents.append(content)
            
        resp.media = contents
        resp.status = falcon.HTTP_200
        log.info("Contents retrieved")

    async def on_post(self, req, resp):
        data = await req.media
        required_fields = ['title', 'type', 'created_by']
        for field in required_fields:
            if field not in data:
                raise falcon.HTTPBadRequest(title='Missing field', description=f'{field} is required')

        if 'user_id' not in data['created_by'] or 'username' not in data['created_by']:
             raise falcon.HTTPBadRequest(title='Missing user_id/username in created_by')

        content = {
            "title": data["title"],
            "type": data["type"],
            "created_by": {
                "user_id": ObjectId(data["created_by"]["user_id"]),
                "username": data["created_by"]["username"]
            },
            "created_at": datetime.now()
        }
        result = self.db.content.insert_one(content)
        content["_id"] = str(result.inserted_id)
        content["created_by"]["user_id"] = str(content["created_by"]["user_id"])
        
        resp.media = content
        resp.status = falcon.HTTP_201
        log.info(f"Content created: {content['_id']}")

    async def on_put(self, req, resp, content_id):
        data = await req.media
        update_doc = {}
        if 'title' in data:
            update_doc['title'] = data['title']
        if 'type' in data:
            update_doc['type'] = data['type']
            
        if not update_doc:
            raise falcon.HTTPBadRequest(title='No fields to update')
            
        result = self.db.content.update_one(
            {"_id": ObjectId(content_id)},
            {"$set": update_doc}
        )
        if result.matched_count == 0:
            raise falcon.HTTPNotFound()
        
        resp.status = falcon.HTTP_200
        log.info(f"Content updated: {content_id}")

    async def on_delete(self, req, resp, content_id):
        result = self.db.content.delete_one({"_id": ObjectId(content_id)})
        if result.deleted_count == 0:
            raise falcon.HTTPNotFound()
            
        resp.status = falcon.HTTP_204
        log.info(f"Content deleted: {content_id}")

class CommentResource:
    def __init__(self, db):
        self.db = db

    async def on_get(self, req, resp):
        filters = {}
        if 'content_id' in req.params:
            filters['content.content_id'] = ObjectId(req.params['content_id'])
        if 'user_id' in req.params:
            filters['user.user_id'] = ObjectId(req.params['user_id'])
            
        comments_cursor = self.db.commentResource.find(filters)
        comments = []
        for comment in comments_cursor:
            comment["_id"] = str(comment["_id"])
            if "content" in comment and "content_id" in comment["content"]:
                comment["content"]["content_id"] = str(comment["content"]["content_id"])
            if "user" in comment and "user_id" in comment["user"]:
                comment["user"]["user_id"] = str(comment["user"]["user_id"])
            comments.append(comment)
            
        resp.media = comments
        resp.status = falcon.HTTP_200
        log.info("Comments retrieved")

    async def on_post(self, req, resp):
        data = await req.media
        required_fields = ['content', 'user', 'text']
        for field in required_fields:
            if field not in data:
                raise falcon.HTTPBadRequest(title='Missing field', description=f'{field} is required')

        if 'content_id' not in data['content'] or 'title' not in data['content']:
             raise falcon.HTTPBadRequest(title='Missing content_id/title in content')
        if 'user_id' not in data['user'] or 'username' not in data['user']:
             raise falcon.HTTPBadRequest(title='Missing user_id/username in user')

        comment = {
            "content": {
                "content_id": ObjectId(data["content"]["content_id"]),
                "title": data["content"]["title"]
            },
            "user": {
                "user_id": ObjectId(data["user"]["user_id"]),
                "username": data["user"]["username"]
            },
            "text": data["text"],
            "created_at": datetime.now()
        }
        result = self.db.commentResource.insert_one(comment)
        comment["_id"] = str(result.inserted_id)
        comment["content"]["content_id"] = str(comment["content"]["content_id"])
        comment["user"]["user_id"] = str(comment["user"]["user_id"])
        
        resp.media = comment
        resp.status = falcon.HTTP_201
        log.info(f"Comment created: {comment['_id']}")

    async def on_delete(self, req, resp, comment_id):
        result = self.db.commentResource.delete_one({"_id": ObjectId(comment_id)})
        if result.deleted_count == 0:
            raise falcon.HTTPNotFound()
            
        resp.status = falcon.HTTP_204
        log.info(f"Comment deleted: {comment_id}")

class ContentLikesResource:
    def __init__(self, db):
        self.db = db

    async def on_get(self, req, resp):
        filters = {}
        if 'content_id' in req.params:
            filters['content.content_id'] = ObjectId(req.params['content_id'])
        if 'user_id' in req.params:
            filters['user.user_id'] = ObjectId(req.params['user_id'])
            
        likes_cursor = self.db.contentLikes.find(filters)
        likes = []
        for like in likes_cursor:
            like["_id"] = str(like["_id"])
            if "content" in like and "content_id" in like["content"]:
                like["content"]["content_id"] = str(like["content"]["content_id"])
            if "user" in like and "user_id" in like["user"]:
                like["user"]["user_id"] = str(like["user"]["user_id"])
            likes.append(like)
            
        resp.media = likes
        resp.status = falcon.HTTP_200
        log.info("Content likes retrieved")

    async def on_post(self, req, resp):
        data = await req.media
        required_fields = ['content', 'user']
        for field in required_fields:
            if field not in data:
                raise falcon.HTTPBadRequest(title='Missing field', description=f'{field} is required')

        if 'content_id' not in data['content'] or 'title' not in data['content']:
             raise falcon.HTTPBadRequest(title='Missing content_id/title in content')
        if 'user_id' not in data['user'] or 'username' not in data['user']:
             raise falcon.HTTPBadRequest(title='Missing user_id/username in user')

        like = {
            "content": {
                "content_id": ObjectId(data["content"]["content_id"]),
                "title": data["content"]["title"]
            },
            "user": {
                "user_id": ObjectId(data["user"]["user_id"]),
                "username": data["user"]["username"]
            },
            "created_at": datetime.now()
        }
        result = self.db.contentLikes.insert_one(like)
        like["_id"] = str(result.inserted_id)
        like["content"]["content_id"] = str(like["content"]["content_id"])
        like["user"]["user_id"] = str(like["user"]["user_id"])
        
        resp.media = like
        resp.status = falcon.HTTP_201
        log.info(f"Like created: {like['_id']}")

    async def on_delete(self, req, resp, like_id):
        result = self.db.contentLikes.delete_one({"_id": ObjectId(like_id)})
        if result.deleted_count == 0:
            raise falcon.HTTPNotFound()
            
        resp.status = falcon.HTTP_204
        log.info(f"Like deleted: {like_id}")

class InternalShareResource:
    def __init__(self, db):
        self.db = db

    async def on_get(self, req, resp):
        filters = {}
        if 'from_user_id' in req.params:
            filters['from_user.user_id'] = ObjectId(req.params['from_user_id'])
        if 'to_user_id' in req.params:
            filters['to_user.user_id'] = ObjectId(req.params['to_user_id'])
        if 'content_id' in req.params:
            filters['content.content_id'] = ObjectId(req.params['content_id'])

        shares_cursor = self.db.internalShareResource.find(filters)
        shares = []
        for share in shares_cursor:
            share["_id"] = str(share["_id"])
            share["from_user"]["user_id"] = str(share["from_user"]["user_id"])
            share["to_user"]["user_id"] = str(share["to_user"]["user_id"])
            share["content"]["content_id"] = str(share["content"]["content_id"])
            shares.append(share)

        resp.media = shares
        resp.status = falcon.HTTP_200
        log.info("Internal shares retrieved")

    async def on_post(self, req, resp):
        data = await req.media
        required_fields = ['from_user', 'to_user', 'content']
        for field in required_fields:
            if field not in data:
                raise falcon.HTTPBadRequest(title='Missing field', description=f'{field} is required')

        if 'user_id' not in data['from_user'] or 'username' not in data['from_user']:
            raise falcon.HTTPBadRequest(title='Missing user_id/username in from_user')
        if 'user_id' not in data['to_user'] or 'username' not in data['to_user']:
            raise falcon.HTTPBadRequest(title='Missing user_id/username in to_user')
        if 'content_id' not in data['content'] or 'title' not in data['content']:
            raise falcon.HTTPBadRequest(title='Missing content_id/title in content')

        share = {
            "from_user": {
                "user_id": ObjectId(data['from_user']['user_id']),
                "username": data['from_user']['username']
            },
            "to_user": {
                "user_id": ObjectId(data['to_user']['user_id']),
                "username": data['to_user']['username']
            },
            "content": {
                "content_id": ObjectId(data['content']['content_id']),
                "title": data['content']['title']
            },
            "created_at": datetime.now()
        }
        result = self.db.internalShareResource.insert_one(share)
        share["_id"] = str(result.inserted_id)
        share["from_user"]["user_id"] = str(share["from_user"]["user_id"])
        share["to_user"]["user_id"] = str(share["to_user"]["user_id"])
        share["content"]["content_id"] = str(share["content"]["content_id"])

        resp.media = share
        resp.status = falcon.HTTP_201
        log.info(f"Internal share created: {share['_id']}")

class ExternalShareResource:
    def __init__(self, db):
        self.db = db

    async def on_get(self, req, resp):
        filters = {}
        if 'platform' in req.params:
            filters['platform'] = req.params['platform']
        if 'user_id' in req.params:
            filters['user.user_id'] = ObjectId(req.params['user_id'])
        
        shares_cursor = self.db.externalShareResource.find(filters)
        shares = []
        for share in shares_cursor:
            share["_id"] = str(share["_id"])
            if "user" in share and "user_id" in share["user"]:
                share["user"]["user_id"] = str(share["user"]["user_id"])
            if "content" in share and "content_id" in share["content"]:
                share["content"]["content_id"] = str(share["content"]["content_id"])
            shares.append(share)
            
        resp.media = shares
        resp.status = falcon.HTTP_200
        log.info("External shares retrieved")

    async def on_post(self, req, resp):
        data = await req.media
        required_fields = ['user', 'content', 'platform']
        for field in required_fields:
            if field not in data:
                raise falcon.HTTPBadRequest(title='Missing field', description=f'{field} is required')

        if 'user_id' not in data['user'] or 'username' not in data['user']:
             raise falcon.HTTPBadRequest(title='Missing user_id/username in user')
        if 'content_id' not in data['content'] or 'title' not in data['content']:
             raise falcon.HTTPBadRequest(title='Missing content_id/title in content')

        share = {
            "user": {
                "user_id": ObjectId(data["user"]["user_id"]),
                "username": data["user"]["username"]
            },
            "content": {
                "content_id": ObjectId(data["content"]["content_id"]),
                "title": data["content"]["title"]
            },
            "platform": data["platform"],
            "created_at": datetime.now()
        }
        result = self.db.externalShareResource.insert_one(share)
        share["_id"] = str(result.inserted_id)
        share["user"]["user_id"] = str(share["user"]["user_id"])
        share["content"]["content_id"] = str(share["content"]["content_id"])
        
        resp.media = share
        resp.status = falcon.HTTP_201
        log.info(f"External share created: {share['_id']}")


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