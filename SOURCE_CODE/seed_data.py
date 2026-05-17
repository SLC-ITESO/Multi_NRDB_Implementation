#!/usr/bin/env python3

# These records are the shared demo data for MongoDB and Dgraph.
# The important part is that the MongoDB _id and the Dgraph user_id are the same.

DEMO_PASSWORD = "1234"

DEMO_USERS = [
    {
        "id": "6a00ba6fe204703196b479ec",
        "username": "demo",
        "email": "demo@mail.com",
        "age": 21,
        "location": "Guadalajara",
        "preferences": ["prayer"],
    },
    {
        "id": "6a00ba6fe204703196b479ed",
        "username": "mariano",
        "email": "mariano@mail.com",
        "age": 22,
        "location": "Guadalajara",
        "preferences": ["prayer", "meditation"],
    },
    {
        "id": "6a00ba6fe204703196b479ee",
        "username": "german",
        "email": "german@mail.com",
        "age": 22,
        "location": "Guadalajara",
        "preferences": ["prayer", "community"],
    },
    {
        "id": "6a00ba6fe204703196b479ef",
        "username": "ana",
        "email": "ana@mail.com",
        "age": 23,
        "location": "Guadalajara",
        "preferences": ["community"],
    },
    {
        "id": "6a00ba6fe204703196b479f0",
        "username": "santiago",
        "email": "santiago@mail.com",
        "age": 22,
        "location": "Zapopan",
        "preferences": ["meditation"],
    },
]

DEMO_CONTENT = [
    {
        "id": "7000ba6fe204703196b479e1",
        "title": "Peaceful Evening Prayer",
        "type": "prayer",
        "created_by": "6a00ba6fe204703196b479ec",
    },
    {
        "id": "7000ba6fe204703196b479e2",
        "title": "Meditation for Anxiety",
        "type": "meditation",
        "created_by": "6a00ba6fe204703196b479ed",
    },
]

DEMO_EVENTS = [
    {
        "id": "e1",
        "title": "Prayer Circle",
        "location": "Guadalajara",
        "start_date": "2026-06-03T18:00:00Z",
        "topics": ["prayer"],
    },
    {
        "id": "e2",
        "title": "Community Service",
        "location": "Guadalajara",
        "start_date": "2026-06-12T09:00:00Z",
        "topics": ["community"],
    },
    {
        "id": "e3",
        "title": "Meditation Meetup",
        "location": "Zapopan",
        "start_date": "2026-06-07T17:00:00Z",
        "topics": ["meditation"],
    },
]

DEMO_FOLLOWS = [
    ("6a00ba6fe204703196b479ed", "6a00ba6fe204703196b479ee"),
    ("6a00ba6fe204703196b479ed", "6a00ba6fe204703196b479f0"),
    ("6a00ba6fe204703196b479ee", "6a00ba6fe204703196b479ef"),
]

DEMO_ATTENDANCE = [
    ("6a00ba6fe204703196b479ed", "e1"),
    ("6a00ba6fe204703196b479ef", "e2"),
    ("6a00ba6fe204703196b479f0", "e3"),
]
