# Dgraph Part of the Project


## 1. What Dgraph Is Used For

Dgraph handles the relationship-based features of the app:

| Requirement | Feature |
|---|---|
| FR-11 | Follow users |
| FR-14 | Recommend users |
| FR-15 | Recommend users by location |
| FR-25 | Local events |
| FR-26 | Attend event |
| FR-27 | Recommend events |

The graph stores these relationships:

```text
(User)-[follows]->(User)
(User)-[attends]->(Event)
(User)-[interested_in]->(Interest)
(Event)-[event_topic]->(Interest)
```

MongoDB is better for normal documents, but Dgraph is better for questions like:

- Which users share interests with me?
- Which events match my interests?
- How many users follow this person?
- How many users attend this event?

## 2. Graph Model

The graph uses three node types:

```text
User
Event
Interest
```

The relationships are:

- `follows`: one user follows another user
- `attends`: one user attends an event
- `interested_in`: one user is interested in a topic
- `event_topic`: one event is about a topic

## 3. Dgraph Schema

The schema lives in `dgraph/dgraph_model.py`:

```graphql
user_id: string @index(exact) @upsert .
username: string @index(term) .
location: string @index(exact) .

event_id: string @index(exact) @upsert .
title: string @index(term) .
start_date: datetime @index(day) .

interest_name: string @index(exact) @upsert .

follows: [uid] @reverse .
attends: [uid] @reverse .
interested_in: [uid] @reverse .
event_topic: [uid] @reverse .
```

### Indexes

- `user_id`, `event_id`, `interest_name`: fast lookup by ID
- `location`: filters users and events by city
- `start_date`: filters future events

### Reverse edges

- `~follows`: who follows this user?
- `~attends`: who attends this event?
- `~interested_in`: who else shares this interest?
- `~event_topic`: which events match this interest?

## 4. Key Files

| File | Purpose |
|---|---|
| `dgraph/dgraph_model.py` | Pure Dgraph logic: schema, queries, mutations |
| `dgraph/resources.py` | Falcon HTTP resource for `/graph/{action}` |
| `dgraph/client.py` | CLI helper that sends HTTP requests to the API |
| `main.py` | CLI parser and command registration |

## 5. The Two Flows

### Flow 1: Admin Commands

Admin commands prepare the database. They run directly from the CLI and do not use Falcon.

Example:

```bash
python3 main.py dgraph_setup
```

Flow:

```text
Terminal
  -> main.py parser
  -> main.py:dgraph_setup_schema(args)
  -> dgraph/client.py:dgraph_setup(args)
  -> dgraph/dgraph_model.py:setup_schema()
  -> Dgraph POST /alter
```

Key points:

- no HTTP server is needed for this flow
- no Falcon Resource is used
- there is no `/graph/{action}` route involved
- it is a direct Python-to-Dgraph setup path

Admin commands:

```bash
python3 main.py dgraph_setup
python3 main.py dgraph_seed
```

### Flow 2: User Commands

User commands use the session file, call the API, and then Falcon routes the request.

One important integration detail: login happens in MongoDB, so the session user has a Mongo ObjectId. Before Dgraph user commands run, `dgraph/client.py` makes sure that same session user also exists as a Dgraph `User` node. This avoids the old problem where the session user was something like `6a00ba6fe204703196b479ec`, but the Dgraph seed only had users like `u1`, `u2`, `u3`, and `u4`.

Example:

```bash
python3 main.py follow_user --user_id u4
```

Flow:

```text
Terminal
  -> main.py parser
  -> main.py:dgraph_follow_user(args)
  -> dgraph/client.py:follow_user(args)
  -> dgraph/client.py:ensure_session_user_in_dgraph()
  -> HTTP POST http://localhost:8000/graph/follow
  -> Falcon receives /graph/{action}
  -> dgraph/resources.py:DgraphResource.on_post(action="follow")
  -> dgraph/dgraph_model.py:follow_user(session user id, u4)
  -> Dgraph POST /mutate
```

Key points:

- an HTTP server must be running with `uvicorn main:app`
- Falcon Resource is part of the flow
- `/graph/{action}` is where the action name is extracted
- Falcon validates and routes the request
- the CLI first syncs the logged-in Mongo user into Dgraph using the same `user_id`

User commands:

```bash
python3 main.py follow_user --user_id u4
python3 main.py recommend_user
python3 main.py attend_event --event_id e2
```

## 6. Flow Comparison

| Aspect | Admin (`dgraph_setup`) | User (`follow_user`) |
|---|---|---|
| Command | `python3 main.py dgraph_setup` | `python3 main.py follow_user --user_id u4` |
| HTTP server | No | Yes (`uvicorn`) |
| Falcon Resource | No | Yes (`DgraphResource`) |
| `/graph/{action}` route | No | Yes |
| Handler | Function in `main.py` | `DgraphResource.on_get()` or `on_post()` |
| Purpose | One-time setup | User action |

## 7. How Routing Works in the Resource

When Falcon receives a request to `/graph/{action}`:

1. The `{action}` part is extracted from the URL path.
2. Falcon decides whether to call `on_get()` or `on_post()` based on the HTTP method.
3. Query parameters or JSON body data are read from the request.
4. Inside the resource, `if` and `elif` statements decide which Dgraph function to call.

Example from `dgraph/resources.py`:

```python
async def on_post(self, req, resp, action):
    data = await req.media

    if action == "follow":
        dgraph_model.follow_user(data["user_id"], data["target_user_id"])
    elif action == "attend":
        dgraph_model.attend_event(data["user_id"], data["event_id"])
    else:
        raise falcon.HTTPNotFound()
```

Example from the CLI client:

```python
response = requests.post(
    PROJECT_API_URL + "/graph/follow",
    json={"user_id": user["user_id"], "target_user_id": args.user_id}
)
```

## 8. Full CLI Setup

### Setup flow

```bash
# Start Dgraph in Docker
docker compose up -d dgraph

# Install the schema in Dgraph
python3 main.py dgraph_setup

# Load seed data
python3 main.py dgraph_seed
```

### API flow

In another terminal:

```bash
# Start the Falcon API
uvicorn main:app --host 0.0.0.0 --port 8000
```

### User testing flow

```bash
# Register and login through MongoDB
python3 main.py register --username demo --email demo@mail.com --password 1234 --age 21 --location Guadalajara --preferences prayer
python3 main.py login --email demo@mail.com --password 1234
python3 main.py get_profile

# Follow a user
python3 main.py follow_user --user_id u4

# Recommend users by shared interests
python3 main.py recommend_user

# Recommend users by location
python3 main.py recommend_user_loc

# Get local events
python3 main.py local_events

# Attend an event
python3 main.py attend_event --event_id e2

# Recommend events
python3 main.py recommend_events

# Show graph summary
python3 main.py graph_summary
```

When these commands run, the CLI reads `.session.json`, fetches the user's full Mongo profile when possible, and calls `ensure_user_from_session()` in `dgraph/dgraph_model.py`. That creates or updates a Dgraph user with the same id, location, and preferences.

## 9. Main Queries

### `recommend_users`

This query recommends users who share an interest with the current user.

Simple idea:

```text
User -> interested_in -> Interest -> ~interested_in -> other Users
```

It excludes:

- the current user
- users already followed

It also returns a follower count:

```graphql
follower_count: count(~follows)
```

### `recommend_events`

This query recommends events that match the current user's interests.

Simple idea:

```text
User -> interested_in -> Interest -> ~event_topic -> Event
```

It excludes:

- events the user already attends
- events in the past

### `graph_summary`

This query shows users and events with aggregate counts.

It uses reverse edges:

```graphql
count(~follows)
count(~attends)
```

## 10. Follow User Walkthrough

Command:

```bash
python3 main.py follow_user --user_id u4
```

Step 1: CLI parser in `main.py`

```python
usr_follow = subparsers.add_parser('follow_user', ...)
usr_follow.set_defaults(func=dgraph_follow_user)
args.func(args)
```

Step 2: handler in `main.py`

```python
def dgraph_follow_user(args):
    dgraph_client_py.follow_user(args)
```

Step 3: CLI client prepares the HTTP request

```python
def follow_user(args):
    user = get_authenticated_user()
    payload = {
        "user_id": user["user_id"],
        "target_user_id": args.user_id,
    }
    response = requests.post(
        PROJECT_API_URL + "/graph/follow",
        json=payload,
    )
    _print_response(response)
```

Step 4: Falcon Resource receives the request

```python
async def on_post(self, req, resp, action):
    data = await req.media

    if action == "follow":
        dgraph_model.follow_user(data["user_id"], data["target_user_id"])
        resp.media = {"message": "Follow relationship created"}
```

Step 5: Dgraph model performs the mutation

```python
def follow_user(user_id, target_user_id):
    if user_id == target_user_id:
        raise ValueError("Users cannot follow themselves")

    if edge_exists("user_id", user_id, "follows", "user_id", target_user_id):
        raise ValueError("Follow relationship already exists")

    return add_edge("user_id", user_id, "follows", "user_id", target_user_id)
```

Step 6: the HTTP response goes back to the CLI

```text
201 Created
{ "message": "Follow relationship created" }
```

## 11. Where to Read First

1. `dgraph/dgraph_model.py` - the actual Dgraph logic
2. `dgraph/resources.py` - the Falcon HTTP routing layer
3. `dgraph/client.py` - the CLI client that calls the API
4. `main.py` - the CLI parser and command registration

## 12. Rubric Coverage

This implementation covers the main Dgraph rubric points:

- clear relationships between nodes: `follows`, `attends`, `interested_in`, `event_topic`
- indexes: `user_id`, `event_id`, `interest_name`, `location`, `start_date`
- reverse traversal: `~follows`, `~attends`, `~interested_in`, `~event_topic`
- aggregation: `count(~follows)` and `count(~attends)`
- query-driven modeling: the schema is based on the recommendation and event queries
- working code: CLI commands and API endpoints both call Dgraph correctly
- setup and seed: `dgraph_setup` and `dgraph_seed`
