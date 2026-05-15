# Multi_NRDB_Implementation


We use different NoSQL databases because the data is not all queried in the same way. MongoDB stores the main application documents. Dgraph stores connected data such as follows, interests, events, and attendance. Cassandra stores analytics tables that are shaped around metrics queries. ChromaDB stores embeddings so the app can search by meaning instead of only exact words.

## Architecture

Most commands start in `main.py`. The CLI parser chooses a command, calls the matching client file, and the client usually sends a request to the Falcon API.

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
terminal output
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
Chroma collection query
```

Cassandra commands are direct CLI commands. They do not go through Falcon because they are only used for metrics/analytics:

```text
Cassandra CLI command
   ↓
main.py parser
   ↓
cassandra/fixtures.py
   ↓
cassandra/cassandra_model.py
   ↓
Cassandra analytics tables
```

Login writes a local `.session.json` file. Commands like `get_profile`, `create_note`, `recommend_user`, `local_events`, and `recommend_content` read that file to know which user is active.

Normal application events such as login, logout, like, comment, share, follow, and event attendance are appended to `app_events.log` as JSON lines. Cassandra is reserved for commands where we explicitly want analytics data.

## Database Responsibilities

| Database | Role in this project | Main files |
| --- | --- | --- |
| MongoDB | Main application data: users, profiles, content, comments, notes, likes, shares, login/session support. | `mongo/client.py`, `mongo/resources.py` |
| Cassandra | Metrics and analytics: activity by user, activity by day, activity by content, daily active users, trending content. | `cassandra/fixtures.py`, `cassandra/cassandra_model.py` |
| Dgraph | Relationship data: follows, interests, events, attendance, reverse traversals, recommendations, aggregate counts. | `dgraph/client.py`, `dgraph/resources.py`, `dgraph/dgraph_model.py` |
| ChromaDB | Vector retrieval: semantic search, content recommendation by preferences, RAG context retrieval, local template-based RAG answer. | `chroma/client.py`, `chroma/resources.py`, `chroma/chroma_model.py` |

## Query-Driven Design

| Query / feature | Database | Data model support | Demo evidence |
| --- | --- | --- | --- |
| Login and profile lookup | MongoDB | `users` collection indexed by `email`, `username`, and `location`. | `python3 main.py login`, `python3 main.py get_profile` |
| Personal notes | MongoDB | `notesResource` documents reference `user.user_id`. | `python3 main.py create_note`, `python3 main.py get_notes` |
| Content engagement summary | MongoDB | Aggregation pipeline joins `content`, `contentLikes`, and `commentResource`. | `python3 main.py content_stats` |
| Activity history by user | Cassandra | `activity_by_user` partitioned by `user_id`, clustered by time. | `python3 main.py get_activity_history --user_id ...` |
| Daily platform activity | Cassandra | `activity_by_day` partitioned by `date`. | `python3 main.py get_daily_active_users --date ...` |
| Content analytics | Cassandra | `activity_by_content` partitioned by `content_id`. | `python3 main.py get_content_metrics --content_id ...` |
| User recommendations | Dgraph | Traverse from user to interests, then reverse from interests to users. | `python3 main.py recommend_user` |
| Local user recommendations | Dgraph | Indexed `location` predicate on `User` nodes. | `python3 main.py recommend_user_loc` |
| Event recommendations | Dgraph | Traverse from user interests to events through `~event_topic`. | `python3 main.py recommend_events` |
| Follower and attendee counts | Dgraph | Reverse edge aggregations: `count(~follows)` and `count(~attends)`. | `python3 main.py graph_summary` |
| Semantic content search | ChromaDB | Embedded content queried by nearest semantic match. | `python3 main.py semantic_search --query "anxiety and peace"` |
| Local RAG-style answer | ChromaDB | Retrieve semantic context and build a template answer from sources. | `python3 main.py rag_answer --query "I need a peaceful prayer"` |

## Important Files

| File or folder | Purpose |
| --- | --- |
| `main.py` | Builds the Falcon API and registers every CLI command. |
| `docker-compose.yml` | Starts MongoDB, Dgraph, and Cassandra containers. |
| `Makefile` | Provides the main setup commands: `make start`, `make stop`, `make reset`, `make seed`. |
| `seed_data.py` | Shared demo records used by MongoDB and Dgraph so user ids match. |
| `event_log.py` | Writes normal application events to `app_events.log`. |
| `.session.json` | Local logged-in user session created by `login`. Ignored by Git. |
| `chroma_db/` | Local persistent ChromaDB data. Ignored by Git. |

## Environment Variables

| Variable | Default | Used by |
| --- | --- | --- |
| `PROJECT_API_URL` | `http://localhost:8000` | CLI clients that call the Falcon API. |
| `DGRAPH_ALPHA_URL` | `http://localhost:8080` | Dgraph setup, seed, and query code. |
| `CHROMA_PATH` | `./chroma_db` | Local ChromaDB storage path. |
| `CASSANDRA_CLUSTER_IPS` | `localhost` | Cassandra Python client. |
| `CASSANDRA_KEYSPACE` | `hallow_db` | Cassandra keyspace name. |
| `CASSANDRA_CONNECT_RETRIES` | `12` | Cassandra startup retry count. |
| `CASSANDRA_CONNECT_DELAY_SECONDS` | `10` | Seconds between Cassandra connection retries. |
| `APP_EVENT_LOG` | `app_events.log` | Local JSON-lines application event log. |

## Clean Reset

Before running a demo from a clean state, we usually reset local data and then start again.

```bash
make reset
```

That command runs:

```bash
docker compose down -v
rm -f .session.json app_events.log
rm -rf chroma_db
```

What each part resets:

| Command | Effect |
| --- | --- |
| `docker compose down -v` | Stops containers and removes Docker volumes for MongoDB, Dgraph, and Cassandra. |
| `rm -f .session.json` | Clears the current logged-in CLI user. |
| `rm -f app_events.log` | Clears the local application event log. |
| `rm -rf chroma_db` | Clears the local ChromaDB collection data. |

Use `make stop` when we only want to stop containers and keep the data:

```bash
make stop
```

## Run From Scratch

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Start everything:

```bash
make start
```

`make start` uses `.venv/bin/python` by default. It runs the Docker services, waits for Cassandra to accept CQL connections, runs the shared seed command, and starts the Falcon API with Uvicorn.

```text
make start
   ↓
docker compose up -d
   ↓
wait for Cassandra
   ↓
.venv/bin/python main.py seed
   ↓
.venv/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Keep that terminal open. Run the CLI commands from a second terminal with the virtual environment activated.

If we only need to reload seed data while services are already running:

```bash
make seed
```

The seed command loads:

- MongoDB indexes for the fields used by CLI/API filters
- MongoDB users and content
- Dgraph schema, users, interests, follows, events, and attendance
- ChromaDB collection and embedded content

It also clears `.session.json` if one exists, because an old session can point to a user id that was removed or replaced during seeding. After `make seed`, login again before running user-specific commands.

Cassandra creates its keyspace and analytics tables the first time a Cassandra command runs.

## Seed Consistency Between MongoDB and Dgraph

MongoDB owns the real user profiles. Dgraph owns graph relationships. When the same person exists in both databases, the id must match.

The shared seed lives in `seed_data.py`. For example, the demo user has this id in both places:

```text
6a00ba6fe204703196b479ec
```

MongoDB stores it as the user document `_id`. Dgraph stores it as the `user_id` predicate on the `User` node. This lets graph commands start from the logged-in Mongo user and find the matching Dgraph node.

The seed user we normally use for demos is:

```text
email: demo@mail.com
password: 1234
location: Guadalajara
preferences: prayer
```

When a user registers or updates profile fields from MongoDB, the client tries to sync the relevant graph fields into Dgraph:

- `user_id`
- `username`
- `location`
- `preferences` as `interested_in` edges

If Dgraph is not running yet, the MongoDB action still succeeds. The Dgraph client also performs a safety sync before graph commands by reading the Mongo profile for the current session user.

Full preference removal from Dgraph is still a pending cleanup item. The current sync adds or updates the user and interest edges, but it does not delete old `interested_in` edges when a preference is removed.

## Demo Flow

Run `make start` in one terminal first. Then use a second terminal for the commands below.

### MongoDB: Login With Seeded Demo User

```bash
python3 main.py login --email demo@mail.com --password 1234
```

Flow:

- `main.py` routes the command to `mongo/client.py`.
- The client hashes the password and sends `POST /login`.
- `AuthResource` checks the MongoDB `users` collection.
- The CLI writes `.session.json`.
- A login event is appended to `app_events.log`.

Expected result: the terminal confirms that `demo` logged in.

### MongoDB: Read Profile

```bash
python3 main.py get_profile
```

Flow:

- The CLI reads `.session.json`.
- `mongo/client.py` requests the profile by email.
- `UserResource` reads the MongoDB document and returns it.

Expected result: the profile includes Guadalajara and `prayer`.

### MongoDB: Register Another User

```bash
python3 main.py register --username visitor --email visitor@mail.com --password 1234 --age 20 --location Guadalajara --preferences prayer
```

Flow:

- The CLI hashes the password.
- `POST /user` creates a MongoDB document.
- The client tries to create/update the matching Dgraph user node with the same MongoDB id.
- A register event is appended to `app_events.log`.

Expected result: MongoDB prints the created user id. If the email already exists, MongoDB returns a conflict.

### MongoDB: Create Content

```bash
python3 main.py create_content --title "Prayer Before Class" --type prayer
```

Flow:

- The CLI reads the logged-in user from `.session.json`.
- `POST /content` inserts a MongoDB content document.
- The content references the MongoDB user id and username.
- A `create_content` event is appended to `app_events.log`.

Expected result: the terminal confirms that the content was created.

### MongoDB: Create and Read Notes

```bash
python3 main.py create_note --title "Reflection" --text "Remember the event recommendation flow."
python3 main.py get_notes
```

Flow:

- `create_note` inserts a note document connected to the logged-in MongoDB user.
- `get_notes` queries notes by the same session user id.
- A `note` event is appended to `app_events.log`.

Expected result: `get_notes` prints the note id, title, text, and creation date.

### MongoDB: Like, Comment, and Share Seeded Content

The shared seed creates a MongoDB content item with this id:

```text
7000ba6fe204703196b479e1
```

Run:

```bash
python3 main.py like_content --content_id 7000ba6fe204703196b479e1
python3 main.py comment_content --content_id 7000ba6fe204703196b479e1 --text "Useful for the demo."
python3 main.py get_comments --content_id 7000ba6fe204703196b479e1
python3 main.py share_content_ext --content_id 7000ba6fe204703196b479e1 --platform instagram
```

Flow:

- The CLI fetches the content from MongoDB.
- The action is inserted into the corresponding MongoDB collection.
- Counts or recent activity fields are updated where the resource supports them.
- The action is also appended to `app_events.log`.

Expected result: the commands confirm the like, comment, comments list, and external share.

### MongoDB: Aggregation Pipeline

```bash
python3 main.py content_stats
```

Flow:

- `main.py` runs a MongoDB aggregation pipeline.
- The pipeline starts from `content`.
- `$lookup` joins matching likes from `contentLikes`.
- `$lookup` joins matching comments from `commentResource`.
- `$project` calculates like count, comment count, and total engagement.

Expected result: content items print with like/comment totals. This is the MongoDB aggregation evidence for the rubric.

### Dgraph: Graph Summary

```bash
python3 main.py graph_summary
```

Flow:

- If a user is logged in, `dgraph/client.py` syncs the Mongo profile into Dgraph.
- The client calls `/graph/summary`.
- Dgraph counts reverse edges such as `~follows` and `~attends`.

Expected result: JSON with seeded users, seeded events, follower counts, and attendee counts.

### Dgraph: Recommend Users

```bash
python3 main.py recommend_user
python3 main.py recommend_user_loc
```

Flow:

- The command starts from the logged-in Mongo user id.
- Dgraph finds the matching `User` node.
- `recommend_user` traverses shared `Interest` nodes.
- `recommend_user_loc` filters users by the same location.
- Existing direct follows and the current user are excluded.

Expected result: non-empty recommendations for the demo user because seeded graph users share `prayer` and `Guadalajara`.

### Dgraph: Events and Attendance

```bash
python3 main.py local_events
python3 main.py recommend_events
python3 main.py attend_event --event_id e1
python3 main.py graph_summary
```

Flow:

- `local_events` filters future events by the logged-in user's location.
- `recommend_events` traverses from the user to interests, then from interests to events.
- `attend_event` creates a `User -> attends -> Event` edge.
- `graph_summary` shows updated attendee counts through `count(~attends)`.
- Attendance is also appended to `app_events.log`.

Expected result: Guadalajara/prayer events appear before attendance, and the summary count changes after attending.

### ChromaDB: Semantic Search

```bash
python3 main.py semantic_search --query "anxiety and peace"
```

Flow:

- The parser routes the command to `chroma/client.py`.
- The client calls `/chroma/search`.
- ChromaDB embeds the query and compares it with stored content embeddings.
- The closest semantic results are returned as JSON.

Expected result: meditation or peace-related content appears even if the words do not match exactly.

### ChromaDB: Recommendation and RAG Context

```bash
python3 main.py recommend_content --preferences prayer --limit 3
python3 main.py rag_context --query "I need a peaceful prayer for my family" --limit 2
python3 main.py rag_answer --query "I need a peaceful prayer for my family" --limit 2
```

Flow:

- `recommend_content` uses preferences as the semantic query.
- `rag_context` retrieves the most relevant documents and returns them as context.
- `rag_answer` retrieves context and returns a local template-based answer with source documents.
- No external paid LLM is required for this demo.

Expected result: prayer or peace-related documents are returned, and `rag_answer` clearly labels the answer as local/template-based.

### Cassandra: Analytics Commands

Cassandra is used when we explicitly want analytics data. The regular Mongo/Dgraph app actions already go to `app_events.log`; the commands below create analytics records in Cassandra tables.

```bash
DEMO_DATE=$(date +%F)

python3 main.py log_session --user_id 6a00ba6fe204703196b479ec --event_type login
python3 main.py log_activity --user_id 6a00ba6fe204703196b479ec --activity_type like --content_id 7000ba6fe204703196b479e1 --metadata demo-like
python3 main.py get_activity_history --user_id 6a00ba6fe204703196b479ec
python3 main.py filter_activity --user_id 6a00ba6fe204703196b479ec --activity_type like
python3 main.py get_content_metrics --content_id 7000ba6fe204703196b479e1
python3 main.py get_daily_active_users --date "$DEMO_DATE"
python3 main.py get_system_stats --date "$DEMO_DATE"
python3 main.py trending_content --date "$DEMO_DATE"
```

Flow:

- `main.py` routes directly to `cassandra/fixtures.py`.
- The Cassandra client connects to `localhost:9042`.
- The keyspace and tables are created if needed.
- Events are written to query-driven tables: by user, by day, and by content.
- Metrics commands read from the table that matches the query.

Expected result: activity history and content metrics reflect the events logged through the Cassandra commands.

## Requirement / Rubric Mapping

| Command | Database | Feature | Rubric area |
| --- | --- | --- | --- |
| `make start` | All services | Starts containers, waits for Cassandra, seeds data, starts API. | Runnable setup and execution steps. |
| `python3 main.py seed` | MongoDB, Dgraph, ChromaDB | Loads shared demo data. | Data loading scripts and repeatable demo data. |
| `register` | MongoDB + Dgraph sync | Creates a user document and attempts graph user sync. | CRUD, document model, database integration. |
| `login` / `get_profile` | MongoDB | Authenticates user and reads profile document. | User/session flow and document reads. |
| `create_content`, `create_note`, `like_content`, `comment_content`, `share_content_ext` | MongoDB + `.log` | Main app document actions and local app event logging. | Document CRUD and application event trace. |
| `content_stats` | MongoDB | Aggregates content engagement through `$lookup` joins. | MongoDB aggregation pipelines and collection relationships. |
| `graph_summary` | Dgraph | Counts followers and attendees with reverse edges. | Graph aggregation and reverse traversal. |
| `recommend_user` | Dgraph | Recommends users through shared interests. | Relationship traversal and query-driven graph model. |
| `recommend_user_loc` | Dgraph | Recommends users by same city. | Indexed graph filtering. |
| `local_events` / `recommend_events` | Dgraph | Finds events by location and shared interests. | Graph relationships and traversal queries. |
| `attend_event` | Dgraph + `.log` | Creates attendance edge and logs app event. | Graph mutation and event trace. |
| `semantic_search` | ChromaDB | Searches embedded content by meaning. | Embeddings and semantic retrieval. |
| `recommend_content` | ChromaDB | Uses preferences as vector search input. | Vector recommendation use case. |
| `rag_context` / `rag_answer` | ChromaDB | Returns retrieved context and a local template-based answer. | RAG-style retrieval and answer workflow. |
| `log_session`, `log_activity` | Cassandra | Writes explicit analytics events. | Query-driven analytics writes. |
| `get_activity_history`, `filter_activity`, `get_daily_active_users`, `get_content_metrics`, `get_system_stats`, `trending_content` | Cassandra | Reads metrics from analytics tables. | Cassandra partition/clustering/query design. |

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `Connection refused` for MongoDB | Containers are not running. | `docker compose up -d` or `make start`. |
| `NoHostAvailable` for Cassandra | Cassandra container is running but CQL is not ready yet. | `make wait-cassandra` or wait and retry. |
| Dgraph commands return empty arrays | Dgraph was not seeded, or the logged-in user does not exist in Dgraph. | `python3 main.py seed`, then login as `demo@mail.com`. |
| Chroma search returns empty results | Local Chroma collection was deleted or not seeded. | `python3 main.py chroma_setup` and `python3 main.py chroma_seed`. |
| CLI says user is not logged in | `.session.json` is missing. | Run `python3 main.py login --email demo@mail.com --password 1234`. |
| Login uses an old user | Stale `.session.json`. | `rm -f .session.json`, then login again. |
| API calls fail on port `8000` | Uvicorn is not running or another process uses the port. | Start with `make start`, or run Uvicorn on another port and set `PROJECT_API_URL`. |

## Testing / Verification Commands

Use these commands before recording the demo:

```bash
docker compose config --services
make wait-cassandra
python3 main.py seed
python3 main.py login --email demo@mail.com --password 1234
python3 main.py get_profile
python3 main.py content_stats
python3 main.py graph_summary
python3 main.py recommend_user
python3 main.py semantic_search --query "anxiety and peace"
python3 main.py rag_answer --query "I need a peaceful prayer for my family" --limit 2
python3 main.py log_session --user_id 6a00ba6fe204703196b479ec --event_type login
python3 main.py get_activity_history --user_id 6a00ba6fe204703196b479ec
```

## Known Limitations

- MongoDB to Dgraph sync updates graph-relevant user data, but preference removal does not delete old Dgraph interest edges.
- Cassandra analytics are written through explicit analytics commands. Regular app actions go to `app_events.log`.
- `rag_answer` is a local template-based RAG answer. It does not call an external LLM.
- `make start` starts the API on port `8000`; if that port is busy, use the manual Uvicorn command below with another port.

## Useful Manual Commands

Start only containers:

```bash
docker compose up -d
```

Check containers:

```bash
docker compose ps
```

Check Cassandra readiness:

```bash
docker compose exec cassandra cqlsh 127.0.0.1 9042 -e "DESCRIBE KEYSPACES"
```

Start API manually:

```bash
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Use another API port:

```bash
python3 -m uvicorn main:app --reload --port 8001
export PROJECT_API_URL=http://localhost:8001
```
