#!/usr/bin/env python3
"""
Authors:

Religious App

"""
import falcon.asgi as falcon
from pymongo import MongoClient
import logging
import argparse
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

def mongo_init():
    try:
        mongo_client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        mongo_client.server_info()
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise

    mongo_db = mongo_client.final_proj
    return mongo_db

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
    # FR-02: User Login
    usr_login = subparsers.add_parser('login', help='Login a user')
    usr_login.add_argument('--email', help='', type=str, required=True)
    usr_login.add_argument('--password', help='', required=True)
    # FR-03: Update User Information | MUST BE LOGGED IN
    usr_update = subparsers.add_parser('update', help='Update a user | MUST BE LOGGED IN')
    usr_update.add_argument('--username', help='', type=str, required=True)
    usr_update.add_argument('--email', help='', type=str, required=True)
    usr_update.add_argument('--password', help='', required=True)
    usr_update.add_argument('--age', help='', type=int, required=True)
    usr_update.add_argument('--location', help='', type=str, required=True)
    usr_update.add_argument('--preferences', help='', required=True)
    # FR-04: Manage Preferences | MUST BE LOGGED IN
    # Add preferences
    usr_add_pref = subparsers.add_parser('add_pref', help='Add a preference | MUST BE LOGGED IN')
    usr_rem_pref = subparsers.add_parser('rem_pref', help='Remove a preference | MUST BE LOGGED IN')
    # FR-06: Create Content | MUST BE LOGGED IN
    cnt_create = subparsers.add_parser('create_content', help='Create content | MUST BE ADMIN')
    cnt_create.add_argument('--title', help='', type=str, required=True)
    cnt_create.add_argument('--type', help='', type=str, required=True)
    # FR-07: Like Content | MUST BE LOGGED IN
    usr_like = subparsers.add_parser('like_content', help='Like content | MUST BE LOGGED IN')
    usr_like.add_argument('--content_id', "-cid", help='', type=str, required=True)
    # FR-08: Comment on Content | MUST BE LOGGED IN
    usr_comment = subparsers.add_parser('comment_content', help='Comment on content | MUST BE LOGGED IN')
    usr_comment.add_argument('--content_id', "-cid", help='', type=str, required=True)
    usr_comment.add_argument('--text', '-t', help='', type=str, required=True)
    # FR-09: Get Comments by Content
    cnt_get_comments = subparsers.add_parser('get_comments', help='Get comments by content')
    cnt_get_comments.add_argument('--content_id', "-cid", help='', type=str, required=True)
    # FR-10: Get Comments by User
    usr_get_comments = subparsers.add_parser('get_comments', help='Returns authenticated user comments')

    # FR-13: Share Content (Internal)
    usr_share = subparsers.add_parser('share_content', help='Share content with a user')
    usr_share.add_argument('--content_id', "-cid", help='', type=str, required=True)
    usr_share.add_argument('--user_id', "-uid", help='', type=str, required=True)

    # FR-18: External Sharing Tracking  | MUST BE LOGGED IN | CASSANDRA LOGGING
    usr_share_ext = subparsers.add_parser('share_content_ext', help='Share content with a user')
    usr_share_ext.add_argument('--content_id', "-cid", help='', type=str, required=True)
    usr_share_ext.add_argument('--platform', "-p", help='Twitter | Insta | Facebook | etc', type=str, required=True)

    # FR-21: Create Notes
    usr_create_note = subparsers.add_parser('create_note', help='Create a note | MUST BE LOGGED IN')
    usr_create_note.add_argument('--title', "-t", help='', type=str, required=True)
    usr_create_note.add_argument('--text', "-t", help='', type=str, required=True)
    # FR-22: Retrieve Notes
    usr_get_notes = subparsers.add_parser('get_notes', help='Retrieve notes | MUST BE LOGGED IN')
    # FR-23: Update/Delete Notes
    usr_update_note = subparsers.add_parser('update_note', help='Update/Delete notes | MUST BE LOGGED IN')
    usr_update_note.add_argument('--note_id', "-nid", help='', type=str, required=True)
    usr_update_note.add_argument('--title', "-t", help='', type=str)
    usr_update_note.add_argument('--text', "-t", help='', type=str)

    usr_delete_note = subparsers.add_parser('delete_note', help='Update/Delete notes | MUST BE LOGGED IN')
    usr_delete_note.add_argument('--note_id', "-nid", help='', type=str, required=True)

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
    # FR-16: Retrieve Activity History | MUST BE LOGGED IN
    # FR-17: Filter Activity History
    usr_activity = subparsers.add_parser('get-activity_history', help='Retrieve activity history | MUST BE LOGGED IN')
    usr_activity.add_argument('--like', "-l", help='Gets liked content', type=str)
    usr_activity.add_argument('--date', "-d", help='Gets accesed in a certain date', type=str)

    # FR-19: Activity Logging
    # FR-20: Daily Active Users

    return parser


if __name__ == "__main__":
    mong = mongo_init()