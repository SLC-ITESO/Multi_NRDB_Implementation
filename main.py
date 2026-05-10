#!/usr/bin/env python3
"""
Authors:

Religious App

"""
import falcon.asgi as falcon
from pymongo import MongoClient
import logging
import argparse

from mongo import client as mongo_client_py
from mongo import resources

import app as cassandra_client

import sys
import csv
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggingMiddleware:
    async def process_request(self, req, resp):
        logger.info(f"Request: {req.method} {req.uri}")

    async def process_response(self, req, resp, resource, req_succeeded):
        logger.info(f"Response debug: {resp.status} for {req.method} {req.uri}")


# Initialize MongoDB client and database
mongo_client = MongoClient('mongodb://localhost:27017/')
mongo_db = mongo_client.final_project

# Create the Falcon application
app = falcon.App(middleware=[LoggingMiddleware()])

    # Instantiate the resources
user_resource = resources.UserResource(mongo_db)
auth_resource = resources.AuthResource(mongo_db)
notes_resource = resources.NotesResource(mongo_db)
content_resource = resources.ContentResource(mongo_db)
comment_resource = resources.CommentResource(mongo_db)
likes_resource = resources.ContentLikesResource(mongo_db)
share_resource = resources.InternalShareResource(mongo_db)
external_share_resource = resources.ExternalShareResource(mongo_db)

    # Add routes to serve the resources
app.add_route('/user', user_resource)
app.add_route('/user/{user_id}', user_resource)
app.add_route('/login', auth_resource)
app.add_route('/notes', notes_resource)
app.add_route('/content', content_resource)
app.add_route('/comment', comment_resource)
app.add_route('/likes', likes_resource)
app.add_route('/share', share_resource)
app.add_route('/external_share', external_share_resource)


def build_parser():
    # Initialize argument parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    # USERS (MONGODB)

    # FR-01: User Registration
    usr_register = subparsers.add_parser('register', help='Register a new user')
    usr_register.add_argument('--username', help='', type=str, required=True)
    usr_register.add_argument('--email', help='', type=str, required=True)
    usr_register.add_argument('--password', help='', required=True)
    usr_register.add_argument('--age', help='', type=int, required=True)
    usr_register.add_argument('--location', help='', type=str, required=True)
    usr_register.add_argument('--preferences', help='', required=True)
    usr_register.set_defaults(func=mongo_register)

    # FR-02: User Login
    usr_login = subparsers.add_parser('login', help='Login a user')
    usr_login.add_argument('--email', help='', type=str, required=True)
    usr_login.add_argument('--password', help='', required=True)
    usr_login.set_defaults(func=mongo_login)

    usr_logout = subparsers.add_parser('logout', help='Logout a user')
    usr_logout.set_defaults(func=mongo_logoff)

    # FR-03: Update User Information | MUST BE LOGGED IN
    usr_update = subparsers.add_parser('update', help='Update a user | MUST BE LOGGED IN')
    usr_update.set_defaults(func=mongo_update)

    # FR-04: Manage Preferences | MUST BE LOGGED IN
    # Add preferences
    usr_add_pref = subparsers.add_parser('add_pref', help='Add a preference | MUST BE LOGGED IN')
    usr_add_pref.set_defaults(func=mongo_add_pref)
    usr_rem_pref = subparsers.add_parser('rem_pref', help='Remove a preference | MUST BE LOGGED IN')
    usr_rem_pref.set_defaults(func=mongo_rem_pref)

    # FR-06: Create Content | MUST BE LOGGED IN
    cnt_create = subparsers.add_parser('create_content', help='Create content | MUST BE ADMIN')
    cnt_create.add_argument('--title', help='', type=str, required=True)
    cnt_create.add_argument('--type', help='', type=str, required=True)
    cnt_create.set_defaults(func=mongo_create_content)

    # FR-07: Like Content | MUST BE LOGGED IN
    usr_like = subparsers.add_parser('like_content', help='Like content | MUST BE LOGGED IN')
    usr_like.add_argument('--content_id', "-cid", help='', type=str, required=True)
    usr_like.set_defaults(func=mongo_like_content)

    # FR-08: Comment on Content | MUST BE LOGGED IN
    usr_comment = subparsers.add_parser('comment_content', help='Comment on content | MUST BE LOGGED IN')
    usr_comment.add_argument('--content_id', "-cid", help='', type=str, required=True)
    usr_comment.add_argument('--text', '-t', help='', type=str, required=True)
    usr_comment.set_defaults(func=mongo_comment_content)

    # FR-09: Get Comments by Content
    cnt_get_comments = subparsers.add_parser('get_comments', help='Get comments by content')
    cnt_get_comments.add_argument('--content_id', "-cid", help='', type=str, required=True)
    cnt_get_comments.set_defaults(func=mongo_get_comments)

    # FR-10: Get Comments by User
    usr_get_comments = subparsers.add_parser('get_own_comments', help='Returns authenticated user comments')
    usr_get_comments.set_defaults(func=mongo_get_own_comments)

    # FR-13: Share Content (Internal)
    usr_share = subparsers.add_parser('share_content', help='Share content with a user')
    usr_share.add_argument('--content_id', "-cid", help='', type=str, required=True)
    usr_share.add_argument('--user_id', "-uid", help='', type=str, required=True)
    usr_share.set_defaults(func=mongo_share_content)

    # FR-18: External Sharing Tracking  | MUST BE LOGGED IN | CASSANDRA LOGGING
    usr_share_ext = subparsers.add_parser('share_content_ext', help='Share content with a user')
    usr_share_ext.add_argument('--content_id', "-cid", help='', type=str, required=True)
    usr_share_ext.add_argument('--platform', "-p", help='Twitter | Insta | Facebook | etc', type=str, required=True)
    usr_share_ext.set_defaults(func=mongo_share_content_ext)

    # FR-21: Create Notes
    usr_create_note = subparsers.add_parser('create_note', help='Create a note | MUST BE LOGGED IN')
    usr_create_note.add_argument('--title', "-ttl", help='', type=str, required=True)
    usr_create_note.add_argument('--text', "-txt", help='', type=str, required=True)
    usr_create_note.set_defaults(func=mongo_create_note)
    # FR-22: Retrieve Notes
    usr_get_notes = subparsers.add_parser('get_notes', help='Retrieve notes | MUST BE LOGGED IN')
    usr_get_notes.set_defaults(func=mongo_get_notes)
    # FR-23: Update/Delete Notes
    usr_update_note = subparsers.add_parser('update_note', help='Update/Delete notes | MUST BE LOGGED IN')
    usr_update_note.add_argument('--note_id', "-nid", help='', type=str, required=True)
    usr_update_note.add_argument('--title', "-ttl", help='', type=str)
    usr_update_note.add_argument('--text', "-txt", help='', type=str)
    usr_update_note.set_defaults(func=mongo_update_note)

    usr_delete_note = subparsers.add_parser('delete_note', help='Update/Delete notes | MUST BE LOGGED IN')
    usr_delete_note.add_argument('--note_id', "-nid", help='', type=str, required=True)
    usr_delete_note.set_defaults(func=mongo_delete_note)

    # DGRAPH
    # FR-11: Follow Users
    usr_follow = subparsers.add_parser('follow_user', help='Follow a user')
    usr_follow.add_argument('--user_id', "-uid", help='', type=str, required=True)
    # FR-14: Recommend Users | MUST BE LOGGED IN
    usr_recommend = subparsers.add_parser('recommend_user', help='Recommend users to follow | MUST BE LOGGED IN')
    # FR-15: Recommend Users by Location
    usr_recommend_loc = subparsers.add_parser('recommend_user_loc', help='Recommend users to follow by location | MUST BE LOGGED IN')
    # FR-24: Recommend Content
    usr_recommend_content = subparsers.add_parser('recommend_content', help='Recommend content | MUST BE LOGGED IN')
    # FR-25: Local Events
    usr_local_events = subparsers.add_parser('local_events', help='Get local events | MUST BE LOGGED IN')
    # FR-26: Attend Event
    usr_attend_event = subparsers.add_parser('attend_event', help='Attend an event | MUST BE LOGGED IN')
    usr_attend_event.add_argument('--event_id', "-eid", help='', type=str, required=True)
    # FR-27: Recommend Events via connections (Following people?)
    usr_recommend_events = subparsers.add_parser('recommend_events', help='Recommend events | MUST BE LOGGED IN')

    # CHROMADB

    # CASSANDRA
    # FR-05: Session Tracking
    p = subparsers.add_parser('log_session',
                              help='Log a login or logout event (FR-05)')
    p.add_argument('--user_id',    required=True)
    p.add_argument('--event_type', required=True, choices=['login', 'logout'])
    p.set_defaults(func=cassandra_client.log_session)

    # FR-07 / FR-08 / FR-13 / FR-18 / FR-19: Generic activity log
    p = subparsers.add_parser('log_activity',
                              help='Log a user activity event (FR-07, FR-08, FR-13, FR-18, FR-19)')
    p.add_argument('--user_id',       required=True)
    p.add_argument('--activity_type', required=True,
                   choices=['like', 'comment', 'share_internal',
                            'share_external', 'view', 'note'])
    p.add_argument('--content_id', '-cid', required=False, default=None)
    p.add_argument('--metadata',           required=False, default=None)
    p.set_defaults(func=cassandra_client.log_activity)

    # FR-16: Retrieve Activity History
    p = subparsers.add_parser('get_activity_history',
                              help='Retrieve activity history for a user (FR-16)')
    p.add_argument('--user_id', required=True)
    p.add_argument('--limit',   type=int, default=20)
    p.set_defaults(func=cassandra_client.get_activity_history)
 
    # FR-17: Filter Activity History
    p = subparsers.add_parser('filter_activity',
                              help='Filter activity history by type and/or date (FR-17)')
    p.add_argument('--user_id',       required=True)
    p.add_argument('--activity_type', required=False, default=None,
                   choices=['login', 'logout', 'like', 'comment',
                            'share_internal', 'share_external', 'view', 'note'])
    p.add_argument('--date',  required=False, default=None, help='YYYY-MM-DD')
    p.add_argument('--limit', type=int, default=20)
    p.set_defaults(func=cassandra_client.filter_activity)
 
    # FR-20: Daily Active Users
    p = subparsers.add_parser('get_daily_active_users',
                              help='Count unique active users on a given date (FR-20)')
    p.add_argument('--date', required=True, help='YYYY-MM-DD')
    p.set_defaults(func=cassandra_client.get_daily_active_users)
 
    # FR-32: Content Engagement Metrics
    p = subparsers.add_parser('get_content_metrics',
                              help='Get engagement metrics for a content item (FR-32)')
    p.add_argument('--content_id', '-cid', required=True)
    p.set_defaults(func=cassandra_client.get_content_metrics)
 
    # FR-33: System-wide Stats
    p = subparsers.add_parser('get_system_stats',
                              help='Get system-wide statistics for a given date (FR-33)')
    p.add_argument('--date', required=True, help='YYYY-MM-DD')
    p.set_defaults(func=cassandra_client.get_system_stats)
 
    # FR-34: Trending Content
    p = subparsers.add_parser('trending_content',
                              help='Identify trending content by interaction volume (FR-34)')
    p.add_argument('--date',  required=True, help='YYYY-MM-DD')
    p.add_argument('--limit', type=int, default=10)
    p.set_defaults(func=cassandra_client.trending_content)

    return parser

def mongo_register(args):
    print("ENTRO A MONGO_REGISTER")
    mongo_client_py.mongo_register(args)

def mongo_login(args):
    print("ENTRO A MONGO_LOGIN")
    mongo_client_py.mongo_login(args)

def mongo_logoff(args):
    os.remove(mongo_client_py.SESSION_FILE)
    print("User logged off")

def mongo_update(args):
    print("ENTRO A MONGO_UPDATE")
    mongo_client_py.mongo_update(args)

def mongo_add_pref(args):
    print("ENTRO A MONGO_ADD_PREF")
    mongo_client_py.mongo_add_pref(args)

def mongo_rem_pref(args):
    print("ENTRO A MONGO_REM_PREF")
    mongo_client_py.mongo_rem_pref(args)

def mongo_create_content(args):
    print("ENTRO A MONGO_CREATE_CONTENT")
    mongo_client_py.mongo_create_content(args)

def mongo_like_content(args):
    print("ENTRO A MONGO_LIKE_CONTENT")
    mongo_client_py.mongo_like_content(args)

def mongo_comment_content(args):
    print("ENTRO A MONGO_COMMENT_CONTENT")
    mongo_client_py.mongo_comment_content(args)

def mongo_get_comments(args):
    print("ENTRO A MONGO_GET_COMMENTS")
    mongo_client_py.mongo_get_comments(args)

def mongo_get_own_comments(args):
    print("ENTRO A MONGO_GET_OWN_COMMENTS")
    mongo_client_py.mongo_get_own_comments(args)

def mongo_share_content(args):
    print("ENTRO A MONGO_SHARE_CONTENT")
    mongo_client_py.mongo_share_content(args)

def mongo_share_content_ext(args):
    print("ENTRO A MONGO_SHARE_CONTENT_EXT")
    mongo_client_py.mongo_share_content_ext(args)

def mongo_create_note(args):
    print("ENTRO A MONGO_CREATE_NOTE")
    mongo_client_py.mongo_create_note(args)

def mongo_get_notes(args):
    print("ENTRO A MONGO_GET_NOTES")
    mongo_client_py.mongo_get_notes(args)

def mongo_update_note(args):
    print("ENTRO A MONGO_UPDATE_NOTE")
    mongo_client_py.mongo_update_note(args)

def mongo_delete_note(args):
    print("ENTRO A MONGO_DELETE_NOTE")
    mongo_client_py.mongo_delete_note(args)

if __name__ == "__main__":

    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.error(f"Command '{args.command}' is not implemented yet.")
    args.func(args)