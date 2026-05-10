# Multi_NRDB_Implementation

## 1. Project Overview

This repository contains the backend for a religious/wellness application. The app supports user accounts, personal notes, content, comments, shares, user relationships, event recommendations, activity history, and semantic content search.

We use more than one NoSQL database because the data is queried in different ways:

- User profiles, notes, content, comments, and shares fit naturally as documents.
- Activity history is time-based and query-driven.
- Follows, interests, events, and attendance are connected data.
- Semantic search needs embeddings instead of exact text matching.

The project is run mainly from `main.py`. That file builds the Falcon API and also registers the CLI commands used during testing and demo runs.

## 2. Architecture Overview

The backend has two entry points:

- CLI commands, created with `argparse` in `main.py`
- API routes, created with Falcon resources in `main.py`

Most user-facing commands follow this path:

```text
CLI command
   ↓
main.py parser
   ↓
database client file
   ↓
Falcon resource
   ↓
database model/query
   ↓
database response
   ↓
formatted CLI output
```

Examples:

```text
register
   ↓
mongo/client.py
   ↓
POST /user
   ↓
mongo/resources.py:UserResource
   ↓
MongoDB users collection
```

```text
recommend_events
   ↓
dgraph/client.py
   ↓
GET /graph/recommend-events
   ↓
dgraph/resources.py:DgraphResource
   ↓
dgraph/dgraph_model.py
   ↓
Dgraph traversal query
```

```text
semantic_search
   ↓
chroma/client.py
   ↓
GET /chroma/search
   ↓
chroma/resources.py:ChromaResource
   ↓
chroma/chroma_model.py
   ↓
ChromaDB collection query
```

Cassandra commands are different. They are direct CLI commands and do not go through Falcon:

```text
Cassandra CLI command
   ↓
main.py parser
   ↓
cassandra/fixtures.py
   ↓
cassandra/cassandra_model.py
   ↓
Cassandra tables
```

### Local Session Flow

Login creates a local `.session.json` file:

```bash
python3 main.py login --email demo@mail.com --password 1234
```

MongoDB owns the login data. The session file stores the logged-in user's MongoDB id, username, and email. Commands such as `get_profile`, `create_note`, `recommend_events`, and `recommend_content` read that file to know which user is active.

Dgraph also needs a graph user node. Before Dgraph user queries run, `dgraph/client.py` makes sure the logged-in MongoDB user also exists in Dgraph with the same `user_id`. That keeps MongoDB authentication and Dgraph relationship queries connected.

## 3. Database Responsibilities

### MongoDB

MongoDB stores the user-facing document data:

- users
- content
- comments
- notes
- likes
- internal shares
- external shares

MongoDB commands in `main.py` include:

- `register`
- `login`
- `get_profile`
- `create_content`
- `like_content`
- `comment_content`
- `get_comments`
- `get_own_comments`
- `share_content`
- `share_content_ext`
- `create_note`
- `get_notes`
- `update_note`
- `delete_note`

MongoDB runs in Docker Compose:

```text
service: mongodb
container: final-project-mongodb
port: 27017
```

The Python code connects from the host machine using:

```python
MongoClient("mongodb://localhost:27017/")
```

### Cassandra

Cassandra stores activity and analytics-style data. The model is query-driven: the same event is written into tables shaped around the reads we need later.

Implemented tables in `cassandra/cassandra_model.py`:

| Table | Partition key | Main query |
| --- | --- | --- |
| `activity_by_user` | `user_id` | Get a user's activity history ordered by time. |
| `activity_by_day` | `date` | Count daily active users and system activity for a day. |
| `activity_by_content` | `content_id` | Get engagement metrics for one content item. |

The clustering columns use `timestamp` and `activity_id`, so events inside a partition are ordered by time.

Cassandra commands in `main.py` include:

- `log_session`
- `log_activity`
- `get_activity_history`
- `filter_activity`
- `get_daily_active_users`
- `get_content_metrics`
- `get_system_stats`
- `trending_content`

`docker-compose.yml` starts Cassandra together with MongoDB and Dgraph. The Cassandra container exposes CQL on:

```text
localhost:9042
```

The Python client reads `CASSANDRA_CLUSTER_IPS`, which defaults to:

```text
localhost
```

Cassandra usually needs more time to become ready than MongoDB or Dgraph. The container may be running while CQL is still starting, so the Python client waits and retries before giving up.

### Dgraph

Dgraph stores relationship data:

```text
(User)-[follows]->(User)
(User)-[attends]->(Event)
(User)-[interested_in]->(Interest)
(Event)-[event_topic]->(Interest)
```

Dgraph is used for:

- user recommendations by shared interests
- user recommendations by location
- local event lookup
- event recommendations by shared interests
- attendance relationships
- follower counts
- attendee counts

The Dgraph schema defines indexes on lookup fields such as `user_id`, `event_id`, `interest_name`, `location`, and `start_date`. It also uses reverse edges such as `~follows`, `~attends`, `~interested_in`, and `~event_topic`.

Dgraph commands in `main.py` include:

- `dgraph_setup`
- `dgraph_seed`
- `graph_summary`
- `follow_user`
- `recommend_user`
- `recommend_user_loc`
- `local_events`
- `attend_event`
- `recommend_events`

### ChromaDB

ChromaDB stores embedded content for semantic retrieval. The collection stores text documents plus metadata such as title, type, and tags.

ChromaDB is used for:

- semantic search
- content recommendation from preferences
- retrieval context for a RAG-style response

The embedding model is `all-MiniLM-L6-v2` through `sentence-transformers`. The local Chroma database is stored in:

```text
chroma_db/
```

ChromaDB commands in `main.py` include:

- `chroma_setup`
- `chroma_seed`
- `semantic_search`
- `recommend_content`
- `rag_context`

## 4. Clean Reset

Before running the demo from a clean state, we normally reset the local environment using the following steps.

### Stop Compose Containers

```bash
docker compose down
```

This stops the MongoDB, Cassandra, and Dgraph containers created by Compose. It keeps their volumes, so database data remains available for the next run.

### Remove Compose Volumes

```bash
docker compose down -v
```

This removes the containers and deletes the Compose volumes. It resets:

- MongoDB data in `mongo-data`
- Cassandra data in `cassandra-data`
- Dgraph data in `dgraph-data`

Use this when old users, old Dgraph nodes, or duplicate demo records are causing confusing results.

### Remove Local CLI Session

```bash
rm -f .session.json
```

This clears the logged-in CLI user. It affects commands that need the current user, such as `get_profile`, `create_note`, `recommend_events`, and `recommend_content`.

### Remove Local ChromaDB Data

```bash
rm -rf chroma_db
```

This removes the local ChromaDB collection data. After deleting it, run `chroma_setup` and `chroma_seed` again.

### Start Containers Again

```bash
docker compose up -d
```

This starts the services defined in `docker-compose.yml`:

- MongoDB on `localhost:27017`
- Cassandra on `localhost:9042`
- Dgraph on `localhost:8080` and `localhost:9080`

Cassandra can take one or two minutes to become ready. Check its status with:

```bash
docker compose ps cassandra
docker compose exec cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES"
```

If the `cqlsh` command works, Cassandra is ready for the CLI commands.

### Recreate Dgraph and Chroma Data

```bash
python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

These commands reinstall the Dgraph schema, load graph seed data, create the Chroma collection, and load embedded content. Cassandra creates its keyspace and tables automatically the first time a Cassandra CLI command runs.

### Full Reset Command Block

```bash
docker compose down -v
rm -f .session.json
rm -rf chroma_db
docker compose up -d

docker compose ps cassandra
docker compose exec cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES"

python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

## 5. Running From Scratch

Open the project folder:

```bash
cd "/Users/mrmariano/Documents/LEARNING/ITESO/Semestre 4/Bases de Datos No Relacionales/Project/Team"
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Start MongoDB, Cassandra, and Dgraph:

```bash
docker compose up -d
docker compose ps
```

Wait until Cassandra accepts CQL connections:

```bash
docker compose exec cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES"
```

If this fails right after startup, wait a bit and run it again. Cassandra often needs extra time after the container starts.

Prepare Dgraph and ChromaDB:

```bash
python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

Start the Falcon API in one terminal:

```bash
uvicorn main:app --reload
```

Run CLI commands in another terminal.

If port `8000` is already being used:

```bash
uvicorn main:app --reload --port 8001
export PROJECT_API_URL=http://localhost:8001
```

## 6. Full Demo Flow

This is the command sequence we use to test the implemented parts of the project.

### 6.1 Start Services and Seed Data

```bash
docker compose up -d
docker compose exec cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES"
python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

Database involved:

- MongoDB starts through Docker Compose.
- Cassandra starts through Docker Compose and exposes CQL on port `9042`.
- Dgraph starts through Docker Compose and receives schema/seed data.
- ChromaDB creates a local collection and embeds seed content.

Internal flow:

- `dgraph_setup` calls `dgraph/client.py`, then `dgraph/dgraph_model.py`, then Dgraph `/alter`.
- `dgraph_seed` creates users, interests, events, and graph edges.
- `chroma_setup` and `chroma_seed` call `chroma/chroma_model.py` directly to prepare the local collection.
- Cassandra keyspace/table setup runs from `cassandra/fixtures.py` the first time a Cassandra command opens a session.

Rubric coverage:

- database setup scripts
- seed/loading scripts
- Cassandra query-driven tables
- Dgraph schema, indexes, reverse edges
- ChromaDB embeddings and vector collection setup

Expected result:

- `Dgraph schema installed`
- `Dgraph seed data loaded`
- `ChromaDB collection ready`
- `ChromaDB seed content loaded`

### 6.2 Start the API

```bash
uvicorn main:app --reload
```

Most MongoDB, Dgraph, and ChromaDB user commands call the Falcon API. Keep this process running while the CLI commands are executed from another terminal.

Internal flow:

```text
main.py
   ↓
Falcon app
   ↓
/user, /login, /notes, /content, /graph/{action}, /chroma/{action}
```

### 6.3 MongoDB: Register User

```bash
python3 main.py register --username demo --email demo@mail.com --password 1234 --age 21 --location Guadalajara --preferences prayer
```

Database involved:

- MongoDB

Internal flow:

- The parser inside `main.py` identifies the `register` command.
- `mongo/client.py` hashes the password and builds the user document.
- The client sends `POST /user`.
- `UserResource` validates the fields and inserts the document into MongoDB.
- The created user id is printed in the terminal.

Requirement/rubric coverage:

- FR-01 User Registration
- document creation
- API-to-database connection

Expected result:

```text
User demo created with id <mongo_object_id>
```

### 6.4 MongoDB: Login and Session

```bash
python3 main.py login --email demo@mail.com --password 1234
```

Database involved:

- MongoDB
- local `.session.json`

Internal flow:

- The parser routes the command to `mongo/client.py`.
- The client hashes the password and sends `POST /login`.
- `AuthResource` checks MongoDB for the email and password hash.
- The CLI writes `.session.json` with `user_id`, `username`, and `email`.

Requirement/rubric coverage:

- FR-02 User Login
- session handling for CLI commands

Expected result:

```text
User demo logged in successfully
```

### 6.5 MongoDB: Get Profile

```bash
python3 main.py get_profile
```

Database involved:

- MongoDB

Internal flow:

- The CLI reads `.session.json`.
- `mongo/client.py` sends `GET /user?email=demo@mail.com`.
- `UserResource` queries the MongoDB `users` collection.
- Profile fields are printed in the terminal.

Requirement/rubric coverage:

- FR-03 user profile retrieval/update support
- document query

Expected result:

- username
- email
- age
- location
- preferences
- created/updated timestamps

### 6.6 MongoDB: Create and Read Notes

```bash
python3 main.py create_note --title "Demo note" --text "This is a personal note saved in MongoDB."
python3 main.py get_notes
```

Database involved:

- MongoDB

Internal flow:

- `create_note` reads the current session user.
- The Mongo client sends `POST /notes`.
- `NotesResource` inserts the note into `notesResource`.
- `get_notes` sends `GET /notes?user_id=<current_user>`.
- Notes for the logged-in user are printed.

Requirement/rubric coverage:

- FR-21 Create Notes
- FR-22 Retrieve Notes
- document creation and query

Expected result:

```text
Note created with id <note_id>
ID: <note_id>, Title: Demo note, Text: This is a personal note saved in MongoDB.
```

### 6.7 MongoDB: Create Content

```bash
python3 main.py create_content --title "Peaceful Evening Prayer" --type prayer
```

Database involved:

- MongoDB

Internal flow:

- The command reads the logged-in user from `.session.json`.
- The client sends `POST /content`.
- `ContentResource` stores the content document with nested `created_by` user data.

Requirement/rubric coverage:

- FR-06 Create Content
- document modeling with nested fields

Expected result:

```text
Content 'Peaceful Evening Prayer' created successfully!
```

### 6.8 MongoDB: Comments, Likes, and Shares

These commands are implemented, but they require ids from existing MongoDB documents.

Useful commands:

```bash
python3 main.py like_content --content_id <content_id>
python3 main.py comment_content --content_id <content_id> --text "Helpful content."
python3 main.py get_comments --content_id <content_id>
python3 main.py get_own_comments
python3 main.py share_content --content_id <content_id> --user_id <target_user_id>
python3 main.py share_content_ext --content_id <content_id> --platform Instagram
```

Database involved:

- MongoDB

Internal flow:

- The CLI uses the content/user ids passed in the command.
- The Mongo client fetches the content or target user when needed.
- The matching resource writes likes, comments, internal shares, or external shares.

Requirement/rubric coverage:

- FR-07 Like Content
- FR-08 Comment on Content
- FR-09 Get Comments by Content
- FR-10 Get Comments by User
- FR-13 Internal Share
- FR-18 External Share Tracking

Expected result:

- success messages for likes/shares/comments
- comment lists for `get_comments` and `get_own_comments`

### 6.9 Cassandra: Log Session Activity

Use stable UUIDs for the demo:

```bash
USER_UUID=3b014d3f-9e46-4494-b918-ae346e07f910
CONTENT_UUID=5f7d0bc3-4d10-48ba-b711-da31a896fd25
DEMO_DATE=2026-05-10
```

Log a login event:

```bash
python3 main.py log_session --user_id $USER_UUID --event_type login
```

Database involved:

- Cassandra

Internal flow:

- The parser routes `log_session` to `cassandra/fixtures.py`.
- The fixture opens a Cassandra session on `localhost:9042`.
- The keyspace and tables are created if needed.
- `cassandra_model.log_activity()` writes the event into query tables.

Requirement/rubric coverage:

- FR-05 Session Tracking
- query-driven write model

Expected result:

```text
Session event 'login' logged [activity_id=<uuid>].
```

### 6.10 Cassandra: Log Content Activity

```bash
python3 main.py log_activity --user_id $USER_UUID --activity_type like --content_id $CONTENT_UUID --metadata "liked during demo"
python3 main.py log_activity --user_id $USER_UUID --activity_type comment --content_id $CONTENT_UUID --metadata "commented during demo"
```

Database involved:

- Cassandra

Internal flow:

- One activity event is written into `activity_by_user` and `activity_by_day`.
- Because `content_id` is provided, the event is also written into `activity_by_content`.
- This denormalized write pattern matches the later query paths.

Requirement/rubric coverage:

- FR-07 Like activity
- FR-08 Comment activity
- FR-19 Activity Logging
- query-driven data modeling

Expected result:

```text
Activity 'like' logged [activity_id=<uuid>].
Activity 'comment' logged [activity_id=<uuid>].
```

### 6.11 Cassandra: Query Activity and Analytics

```bash
python3 main.py get_activity_history --user_id $USER_UUID --limit 20
python3 main.py filter_activity --user_id $USER_UUID --activity_type like --limit 20
python3 main.py get_daily_active_users --date $DEMO_DATE
python3 main.py get_content_metrics --content_id $CONTENT_UUID
python3 main.py get_system_stats --date $DEMO_DATE
python3 main.py trending_content --date $DEMO_DATE --limit 5
```

Database involved:

- Cassandra

Internal flow:

- Activity history reads from `activity_by_user`.
- Daily active users and system stats read from `activity_by_day`.
- Content metrics read from `activity_by_content`.
- Trending content counts content ids from daily activity rows.

Requirement/rubric coverage:

- FR-16 Retrieve Activity History
- FR-17 Filter Activity History
- FR-20 Daily Active Users
- FR-32 Content Engagement Metrics
- FR-33 System-wide Activity Stats
- FR-34 Trending Content
- partition keys and clustering keys for query-driven reads

Expected result:

- activity rows ordered by timestamp
- filtered activity rows
- daily active user count
- engagement counts by activity type
- system stats for the selected date
- ranked content ids by interaction count

### 6.12 Dgraph: Graph Summary

```bash
python3 main.py graph_summary
```

Database involved:

- Dgraph

Internal flow:

- The CLI checks `.session.json`.
- The Dgraph client ensures the logged-in MongoDB user also exists as a Dgraph user.
- The request goes to `GET /graph/summary`.
- `dgraph_model.graph_summary()` runs aggregate counts with reverse edges.

Requirement/rubric coverage:

- graph relationships
- reverse traversal
- aggregation

Expected result:

- users with `follower_count`
- events with `attendee_count`
- the logged-in MongoDB user included as a Dgraph user

### 6.13 Dgraph: Recommend Users

```bash
python3 main.py recommend_user
python3 main.py recommend_user_loc
```

Database involved:

- Dgraph

Internal flow:

- The parser routes the command to the Dgraph client.
- The client loads the current session user from `.session.json`.
- The request is sent to `/graph/recommend-users` or `/graph/recommend-users-by-location`.
- The Dgraph query starts from the logged-in user node.
- `recommend_user` traverses shared interests.
- `recommend_user_loc` filters users by the same city.

Requirement/rubric coverage:

- FR-14 Recommend Users
- FR-15 Recommend Users by Location
- graph traversal
- indexed location filtering

Expected result:

- JSON arrays of user recommendations

### 6.14 Dgraph: Local and Recommended Events

```bash
python3 main.py local_events
python3 main.py recommend_events
```

Database involved:

- Dgraph

Internal flow:

- `local_events` reads the logged-in user's location and filters future events by city.
- `recommend_events` starts from the user, traverses `interested_in`, then uses `~event_topic` to find matching events.
- Results are returned as JSON.

Requirement/rubric coverage:

- FR-25 Local Events
- FR-27 Recommend Events
- graph traversal through shared interests
- indexed filtering by location and start date

Expected result:

- local Guadalajara events
- prayer-related event recommendations for the demo user

### 6.15 Dgraph: Attend Event

```bash
python3 main.py attend_event --event_id e1
python3 main.py graph_summary
```

Database involved:

- Dgraph

Internal flow:

- The first command creates a `User -> attends -> Event` edge.
- The second command reruns aggregate counts.
- `count(~attends)` shows how many users attend each event.

Requirement/rubric coverage:

- FR-26 Attend Event
- relationship mutation
- reverse traversal aggregation

Expected result:

- attendance relationship created
- updated attendee count in `graph_summary`

### 6.16 ChromaDB: Semantic Search

```bash
python3 main.py semantic_search --query "anxiety and peace"
```

Database involved:

- ChromaDB

Internal flow:

- The parser routes the command to `chroma/client.py`.
- The client sends `GET /chroma/search`.
- `ChromaResource` calls `chroma_model.semantic_search()`.
- ChromaDB embeds the query and compares it to stored content embeddings.
- The closest semantic matches are returned.

Requirement/rubric coverage:

- FR-30 Semantic Search
- embeddings
- vector retrieval

Expected result:

- content related to anxiety, meditation, calm, or peace

### 6.17 ChromaDB: Recommend Content

```bash
python3 main.py recommend_content --preferences "prayer meditation"
```

Database involved:

- ChromaDB

Internal flow:

- Preferences are used as the query text.
- ChromaDB compares that preference text against embedded content.
- Matching content is returned by semantic distance.

Requirement/rubric coverage:

- FR-24 Recommend Content
- semantic recommendation
- vector query-driven modeling

Expected result:

- prayer and meditation related content

### 6.18 ChromaDB: RAG Context Retrieval

```bash
python3 main.py rag_context --query "How can I feel calm when stressed?"
```

Database involved:

- ChromaDB

Internal flow:

- The query is embedded.
- ChromaDB retrieves the closest content.
- The backend returns a `context` field plus the source results.

Requirement/rubric coverage:

- FR-31 RAG Response Generation support
- retrieval step for RAG
- semantic context selection

Expected result:

- a context string built from relevant retrieved content

## 7. Requirement / Rubric Mapping

| Command | Feature | Database | Requirement / rubric item | Explanation |
| --- | --- | --- | --- | --- |
| `register` | User registration | MongoDB | FR-01, document CRUD | Inserts a user document into MongoDB. |
| `login` | User login/session | MongoDB | FR-02, functional authentication flow | Authenticates against MongoDB and writes `.session.json`. |
| `get_profile` | Profile retrieval | MongoDB | FR-03 support, document query | Reads the logged-in user's profile document. |
| `create_content` | Content creation | MongoDB | FR-06, document modeling | Stores content with nested creator data. |
| `like_content` | Like content | MongoDB | FR-07 | Records a like for an existing content item. |
| `comment_content` | Comment on content | MongoDB | FR-08 | Stores a comment connected to content and user data. |
| `get_comments` | Comments by content | MongoDB | FR-09 | Retrieves comments for a content item. |
| `get_own_comments` | Comments by user | MongoDB | FR-10 | Retrieves comments written by the logged-in user. |
| `share_content` | Internal share | MongoDB | FR-13 | Stores a share between two users. |
| `share_content_ext` | External share | MongoDB / Cassandra activity concept | FR-18 | Stores an external share document; Cassandra can also log share activity. |
| `create_note` | Create note | MongoDB | FR-21 | Stores a note document for the logged-in user. |
| `get_notes` | Retrieve notes | MongoDB | FR-22 | Reads notes by user id. |
| `update_note`, `delete_note` | Manage notes | MongoDB | FR-23 | Updates or deletes note documents. |
| `log_session` | Session activity log | Cassandra | FR-05 | Writes login/logout activity events. |
| `log_activity` | Generic activity log | Cassandra | FR-07, FR-08, FR-13, FR-18, FR-19 | Writes user activity into denormalized query tables. |
| `get_activity_history` | User activity history | Cassandra | FR-16 | Reads from `activity_by_user`. |
| `filter_activity` | Filter activity history | Cassandra | FR-17 | Filters user activity by type/date. |
| `get_daily_active_users` | Daily active users | Cassandra | FR-20 | Counts unique users from `activity_by_day`. |
| `get_content_metrics` | Content engagement | Cassandra | FR-32 | Counts interactions from `activity_by_content`. |
| `get_system_stats` | System stats | Cassandra | FR-33 | Aggregates activity for a date. |
| `trending_content` | Trending content | Cassandra | FR-34 | Ranks content by interaction count. |
| `dgraph_setup` | Graph schema | Dgraph | Graph schema, indexes, reverse edges | Defines predicates, indexes, types, and reverse traversals. |
| `dgraph_seed` | Graph seed data | Dgraph | Data loading | Loads users, interests, events, follows, and attendance. |
| `graph_summary` | Graph counts | Dgraph | Aggregation, reverse traversal | Uses `count(~follows)` and `count(~attends)`. |
| `follow_user` | Follow relationship | Dgraph | FR-11 | Creates a `User -> follows -> User` edge. |
| `recommend_user` | User recommendation | Dgraph | FR-14 | Traverses shared interests to find users. |
| `recommend_user_loc` | Location recommendation | Dgraph | FR-15 | Filters users by indexed location. |
| `local_events` | Local event lookup | Dgraph | FR-25 | Finds future events in the user's city. |
| `attend_event` | Attend event | Dgraph | FR-26 | Creates a `User -> attends -> Event` edge. |
| `recommend_events` | Event recommendation | Dgraph | FR-27 | Traverses user interests to matching event topics. |
| `chroma_setup` | Vector collection setup | ChromaDB | Vector database setup | Creates the persistent collection. |
| `chroma_seed` | Embedded content seed | ChromaDB | Embeddings + loading | Loads documents and creates embeddings. |
| `semantic_search` | Semantic search | ChromaDB | FR-30 | Searches by meaning instead of exact text. |
| `recommend_content` | Content recommendation | ChromaDB | FR-24 | Uses preferences as a semantic query. |
| `rag_context` | RAG context retrieval | ChromaDB | FR-31 support | Returns retrieved context for a future generated answer. |

## 8. Troubleshooting

### Docker Containers Are Not Running

Symptom:

```text
Cannot connect to the Docker daemon
```

Likely cause:

- Docker Desktop is closed.
- The Compose services were stopped.

Fix:

```bash
docker compose up -d
docker compose ps
```

### MongoDB Connection Fails

Symptom:

```text
ServerSelectionTimeoutError
```

Likely cause:

- MongoDB container is not running.
- Port `27017` is already used by another MongoDB process.

Fix:

```bash
docker compose up -d mongodb
lsof -i :27017
```

### Email Already Exists

Symptom:

```text
Email already registered
```

Likely cause:

- MongoDB still has old demo data.

Fix:

```bash
docker compose down -v
docker compose up -d
python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

### API Port Conflict

Symptom:

```text
address already in use
```

Likely cause:

- Another process is using port `8000`.

Fix:

```bash
uvicorn main:app --reload --port 8001
export PROJECT_API_URL=http://localhost:8001
```

### Missing Session

Symptom:

```text
Error: User not logged in. Please login first.
```

Likely cause:

- `.session.json` does not exist.
- It was removed during reset.

Fix:

```bash
python3 main.py login --email demo@mail.com --password 1234
```

### Stale Session

Symptom:

- commands run as the wrong user
- Dgraph recommendations return empty arrays

Likely cause:

- `.session.json` points to an old MongoDB user id.

Fix:

```bash
rm -f .session.json
python3 main.py login --email demo@mail.com --password 1234
python3 main.py graph_summary
```

### Dgraph Schema or Seed Data Missing

Symptom:

- graph commands fail
- graph commands return empty results
- Dgraph complains about predicates or indexes

Likely cause:

- `dgraph_setup` or `dgraph_seed` was not run after reset.

Fix:

```bash
python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py graph_summary
```

### ChromaDB Collection Missing or Empty

Symptom:

- semantic search returns no useful results
- Chroma complains about a missing collection

Likely cause:

- `chroma_db/` was deleted or never seeded.

Fix:

```bash
python3 main.py chroma_setup
python3 main.py chroma_seed
```

### Chroma Embedding Dependency Error

Symptom:

- import error for `chromadb`
- import error for `sentence_transformers`
- model download errors

Likely cause:

- dependencies are missing
- the embedding model has not been downloaded yet

Fix:

```bash
python3 -m pip install -r requirements.txt
python3 main.py chroma_seed
```

### Cassandra Connection Fails

Symptom:

- Cassandra commands fail with `NoHostAvailable`
- connection refused on `127.0.0.1:9042`

Likely cause:

- Cassandra is still starting.
- The Cassandra container is not running.
- `CASSANDRA_CLUSTER_IPS` points to the wrong host.

Fix:

```bash
export CASSANDRA_CLUSTER_IPS=localhost
docker compose up -d cassandra
docker compose ps cassandra
docker compose exec cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES"
```

Then run:

```bash
python3 main.py log_session --user_id 3b014d3f-9e46-4494-b918-ae346e07f910 --event_type login
```

If `cqlsh` fails immediately after `docker compose up -d`, wait 30-60 seconds and try again. Cassandra takes longer to accept CQL connections than the other containers.

## 9. Final Demo Command Sequence

Reset and prepare data:

```bash
docker compose down -v
rm -f .session.json
rm -rf chroma_db
docker compose up -d
docker compose ps cassandra
docker compose exec cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES"

python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

Start the API:

```bash
uvicorn main:app --reload
```

Run MongoDB commands:

```bash
python3 main.py register --username demo --email demo@mail.com --password 1234 --age 21 --location Guadalajara --preferences prayer
python3 main.py login --email demo@mail.com --password 1234
python3 main.py get_profile
python3 main.py create_note --title "Demo note" --text "This is a personal note saved in MongoDB."
python3 main.py get_notes
python3 main.py create_content --title "Peaceful Evening Prayer" --type prayer
```

Run Cassandra commands:

```bash
USER_UUID=3b014d3f-9e46-4494-b918-ae346e07f910
CONTENT_UUID=5f7d0bc3-4d10-48ba-b711-da31a896fd25
DEMO_DATE=2026-05-10

python3 main.py log_session --user_id $USER_UUID --event_type login
python3 main.py log_activity --user_id $USER_UUID --activity_type like --content_id $CONTENT_UUID --metadata "liked during demo"
python3 main.py log_activity --user_id $USER_UUID --activity_type comment --content_id $CONTENT_UUID --metadata "commented during demo"
python3 main.py get_activity_history --user_id $USER_UUID --limit 20
python3 main.py filter_activity --user_id $USER_UUID --activity_type like --limit 20
python3 main.py get_daily_active_users --date $DEMO_DATE
python3 main.py get_content_metrics --content_id $CONTENT_UUID
python3 main.py get_system_stats --date $DEMO_DATE
python3 main.py trending_content --date $DEMO_DATE --limit 5
```

Run Dgraph commands:

```bash
python3 main.py graph_summary
python3 main.py recommend_user
python3 main.py recommend_user_loc
python3 main.py local_events
python3 main.py recommend_events
python3 main.py attend_event --event_id e1
python3 main.py graph_summary
```

Run ChromaDB commands:

```bash
python3 main.py semantic_search --query "anxiety and peace"
python3 main.py recommend_content --preferences "prayer meditation"
python3 main.py rag_context --query "How can I feel calm when stressed?"
```
