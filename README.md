# Multi_NRDB_Implementation

## 1. Project Overview

This project is a multi-database backend for a religious/wellness application. The app represents users who can register, log in, save personal notes, create content, follow other users, attend events, and search for helpful content.

The main idea of the project is to show how different NoSQL databases can work together in one system. We do not use only one database because the data is not all the same shape:

- MongoDB is useful for flexible JSON-style documents like users, notes, and content.
- Dgraph is useful when the data is mostly relationships, like users following users or events connected to interests.
- ChromaDB is useful when the query is semantic, meaning we search by meaning instead of exact text.
- Cassandra is included as a design direction for activity/log data, but its runnable integration is still partial, so it is not part of the main demo.

This is a university final project, not a production system. The code is intentionally simple so we can run it locally, explain it clearly, and connect each database choice to the requirements.

## 2. How the Project Is Organized

The project is controlled mainly from `main.py`.

`main.py` has two jobs:

1. It creates the Falcon API and registers routes like `/user`, `/notes`, `/graph/{action}`, and `/chroma/{action}`.
2. It creates CLI commands with `argparse`, so we can run commands such as:

```bash
python3 main.py register ...
python3 main.py dgraph_seed
python3 main.py semantic_search --query "anxiety and peace"
```

Most user commands follow this pattern:

```text
terminal command
  -> main.py parser
  -> database client file
  -> Falcon API resource
  -> database model/query logic
  -> database
  -> JSON or printed result
```

There are two exceptions:

- `dgraph_setup` and `dgraph_seed` talk directly to Dgraph because they are setup/admin commands.
- `chroma_setup` and `chroma_seed` talk directly to ChromaDB because they prepare the local vector collection.

The CLI stores login state in:

```text
.session.json
```

That file is created by:

```bash
python3 main.py login --email demo@mail.com --password 1234
```

Dgraph detail: login happens through MongoDB, so the logged-in user has a MongoDB ObjectId. Before Dgraph user commands run, the Dgraph CLI makes sure that same user also exists as a Dgraph `User` node. This lets graph queries work with the real logged-in session user instead of only with hardcoded seed users like `u1`.

## 3. Technologies and Database Responsibilities

| Technology | Role in this project |
| --- | --- |
| Python | Main language for the CLI, API, and database logic. |
| Falcon | API framework used by the resource classes. |
| Uvicorn | Runs the Falcon ASGI app locally. |
| Docker Compose | Starts MongoDB and Dgraph containers. |
| MongoDB | Stores document-style data: users, notes, content, comments, likes, and shares. |
| PyMongo | Python library used to connect API resources to MongoDB. |
| Dgraph | Stores graph relationships: follows, attendance, interests, event topics, and recommendations. |
| ChromaDB | Stores embeddings for semantic search, content recommendation, and RAG-style context retrieval. |
| sentence-transformers | Provides the `all-MiniLM-L6-v2` embedding model used by ChromaDB. |
| requests | Used by CLI clients to call the local API. |
| Cassandra | Planned for activity history/logging tables; current runnable integration is partial. |

### MongoDB

MongoDB stores data that naturally looks like documents:

- users
- notes
- content
- comments
- likes
- internal shares
- external shares

The app connects to MongoDB with:

```python
MongoClient("mongodb://localhost:27017/")
```

This is correct for our setup because Python runs locally on the host machine while MongoDB runs in Docker. If the Python app were inside Docker too, the connection string would normally use the Compose service name:

```text
mongodb://mongodb:27017/
```

### Dgraph

Dgraph stores relationship data:

```text
(User)-[follows]->(User)
(User)-[attends]->(Event)
(User)-[interested_in]->(Interest)
(Event)-[event_topic]->(Interest)
```

This supports graph queries such as:

- recommending users who share interests
- recommending users in the same location
- finding local events
- recommending events based on interests
- counting followers and attendees using reverse edges

### ChromaDB

ChromaDB stores content as embeddings. In this project, we embed sample religious/wellness content and use it for:

- semantic search
- content recommendation from preferences
- retrieval context for a future RAG answer

ChromaDB stores local data in:

```text
chroma_db/
```

### Cassandra

Cassandra is intended for activity history, activity logging, and analytics-style queries. The current repository has Cassandra files and a parser placeholder, but the runnable command flow is not complete. For that reason, Cassandra is documented as partial and is not included in the main demo sequence.

## 4. Folder Structure

```text
main.py                    Main API app and CLI parser
docker-compose.yml         Starts MongoDB and Dgraph containers
requirements.txt           Python dependencies
README.md                  General project README

mongo/client.py            CLI helper functions for Mongo commands
mongo/resources.py         Falcon resources for Mongo routes

dgraph/dgraph_model.py     Dgraph schema, seed data, queries, and mutations
dgraph/client.py           CLI helper functions for Dgraph commands
dgraph/resources.py        Falcon resource for /graph/{action}
dgraph/DGRAPH_README.md    Dgraph-specific notes

chroma/chroma_model.py     Chroma collection, seed data, and semantic search logic
chroma/client.py           CLI helper functions for Chroma commands
chroma/resources.py        Falcon resource for /chroma/{action}
chroma/CHROMA_README.md    Chroma-specific notes

cassandra/cassandra_model.py   Cassandra design/model file, partial integration
cassandra/fixtures.py          Cassandra fixture placeholder

.session.json              Local CLI login/session file
chroma_db/                 Local ChromaDB data folder created after seeding
```

## 5. Clean Start / Reset Instructions

Before running the demo from a clean state, we normally reset the local environment with the following commands.

Stop and remove the running Compose containers:

```bash
docker compose down
```

This stops MongoDB and Dgraph containers, but keeps their Docker volumes. Data is not deleted.

For a full reset, remove the containers and the Docker volumes:

```bash
docker compose down -v
```

This deletes MongoDB and Dgraph data stored in Docker volumes. Use it when old demo data is causing conflicts, for example when `demo@mail.com` already exists.

Remove the local CLI session:

```bash
rm -f .session.json
```

This logs out the local CLI user. It does not delete database data.

Remove local ChromaDB data:

```bash
rm -rf chroma_db
```

This deletes the local vector database folder. After this, run Chroma setup and seed again.

Start MongoDB and Dgraph again:

```bash
docker compose up -d
```

Recreate Dgraph and Chroma demo data:

```bash
python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

Quick reset summary:

| Command | What it does |
| --- | --- |
| `docker compose down` | Stops/removes containers but keeps MongoDB and Dgraph data. |
| `docker compose down -v` | Stops/removes containers and deletes MongoDB/Dgraph volumes. |
| `rm -f .session.json` | Removes local login state. |
| `rm -rf chroma_db` | Deletes local ChromaDB vector data. |
| `docker compose up -d` | Starts MongoDB and Dgraph again. |

## 6. Initial Setup From Scratch

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

Start the database containers:

```bash
docker compose up -d
docker compose ps
```

MongoDB should be available at:

```text
mongodb://localhost:27017/
```

Dgraph should be available at:

```text
http://localhost:8080
```

Optional Dgraph health check:

```bash
curl http://localhost:8080/health
```

Prepare Dgraph:

```bash
python3 main.py dgraph_setup
python3 main.py dgraph_seed
```

Prepare ChromaDB:

```bash
python3 main.py chroma_setup
python3 main.py chroma_seed
```

Start the API server in one terminal and leave it running:

```bash
uvicorn main:app --reload
```

Use a second terminal for CLI commands.

If port `8000` is already busy, run the API on another port:

```bash
uvicorn main:app --reload --port 8001
```

Then point the CLI to that port:

```bash
export PROJECT_API_URL=http://localhost:8001
```

## 7. Complete Demo Flow

The main demo focuses on the implemented parts that currently work: MongoDB, Dgraph, and ChromaDB.

### Step 1 - Start the databases

```bash
docker compose up -d
```

This starts the database services used by the project. MongoDB stores document data and Dgraph stores graph data. ChromaDB is local and does not need a Docker container.

### Step 2 - Prepare Dgraph and ChromaDB

```bash
python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

`dgraph_setup` installs the graph schema: predicates, indexes, reverse edges, and types. `dgraph_seed` inserts sample users, events, interests, and relationships.

`chroma_setup` creates the local Chroma collection. `chroma_seed` stores sample content and generates embeddings with `all-MiniLM-L6-v2`.

### Step 3 - Start the API server

```bash
uvicorn main:app --reload
```

Most CLI commands call the API first. The API then routes the request to the correct resource and database logic.

General flow:

```text
CLI command -> main.py parser -> client file -> Falcon resource -> database logic
```

### Step 4 - MongoDB: register, login, and read profile

```bash
python3 main.py register --username demo --email demo@mail.com --password 1234 --age 21 --location Guadalajara --preferences prayer
python3 main.py login --email demo@mail.com --password 1234
python3 main.py get_profile
```

This creates a MongoDB user document, authenticates that user, and reads the profile back from MongoDB. Login also creates `.session.json`, which later commands use as the current user.

Internal flow:

```text
main.py parser
  -> mongo/client.py
  -> /user or /login API route
  -> mongo/resources.py
  -> MongoDB users collection
```

If `demo@mail.com` already exists, either use another email or run a full reset with `docker compose down -v`.

### Step 5 - MongoDB: create and retrieve a note

```bash
python3 main.py create_note --title "Demo note" --text "This is a personal note saved in MongoDB."
python3 main.py get_notes
```

This is the clearest document-style operation in the demo. The note is stored as a MongoDB document with nested user information, title, text, and timestamps.

Internal flow:

```text
main.py parser
  -> mongo/client.py
  -> /notes API route
  -> NotesResource
  -> MongoDB notesResource collection
```

### Step 6 - MongoDB: create content

```bash
python3 main.py create_content --title "Peaceful Evening Prayer" --type prayer
```

This stores a content document in MongoDB. It shows another JSON-style record connected to the logged-in user.

Internal flow:

```text
main.py parser
  -> mongo/client.py
  -> /content API route
  -> ContentResource
  -> MongoDB content collection
```

### Step 7 - Dgraph: graph summary

```bash
python3 main.py graph_summary
```

This verifies that graph data exists and that reverse traversal counts are working. The output includes users with `follower_count` and events with `attendee_count`.

The logged-in MongoDB user is also copied into Dgraph before this command runs, using the same `user_id`. This is why the session user can participate in graph recommendations.

Internal flow:

```text
main.py parser
  -> dgraph/client.py
  -> ensure session user exists in Dgraph
  -> /graph/summary API route
  -> DgraphResource
  -> dgraph_model.graph_summary()
  -> Dgraph query with count(~follows) and count(~attends)
```

### Step 8 - Dgraph: user recommendations

```bash
python3 main.py recommend_user
python3 main.py recommend_user_loc
```

`recommend_user` recommends users who share interests with the logged-in user. `recommend_user_loc` recommends users in the same location.

These commands are graph-oriented because they start from the current user and traverse relationships or filters:

```text
User -> interested_in -> Interest -> ~interested_in -> other Users
```

Internal flow:

```text
main.py parser
  -> dgraph/client.py
  -> /graph/{action} API route
  -> DgraphResource
  -> Dgraph query
  -> graph traversal result as JSON
```

### Step 9 - Dgraph: local and recommended events

```bash
python3 main.py local_events
python3 main.py recommend_events
```

`local_events` finds future events in the user's city. `recommend_events` finds future events that share interests with the user.

For the demo user in Guadalajara with preference `prayer`, these commands should return Guadalajara/prayer-related data from the seed graph.

Graph idea for event recommendations:

```text
User -> interested_in -> Interest -> ~event_topic -> Event
```

### Step 10 - Dgraph: attend an event

```bash
python3 main.py attend_event --event_id e1
python3 main.py graph_summary
```

The first command creates a `User -> attends -> Event` edge. Running `graph_summary` again lets us see attendee counts using the reverse edge `~attends`.

### Step 11 - ChromaDB: semantic search

```bash
python3 main.py semantic_search --query "anxiety and peace"
```

This command searches by meaning. ChromaDB embeds the query and compares it against the stored content embeddings. Results are returned by semantic similarity, not exact keyword matching.

Internal flow:

```text
main.py parser
  -> chroma/client.py
  -> /chroma/search API route
  -> ChromaResource
  -> chroma_model.semantic_search()
  -> Chroma collection query
  -> nearest semantic results
```

### Step 12 - ChromaDB: recommend content

```bash
python3 main.py recommend_content --preferences "prayer meditation"
```

This uses preferences as a semantic query. Instead of writing a manual filter for every tag, ChromaDB compares the meaning of the preferences against the embedded content.

### Step 13 - ChromaDB: RAG-style context retrieval

```bash
python3 main.py rag_context --query "How can I feel calm when stressed?"
```

This returns retrieved context that could be passed to an LLM in a full RAG pipeline. The project does not call an LLM here; it implements the retrieval part.

Internal flow:

```text
main.py parser
  -> chroma/client.py
  -> /chroma/rag-context API route
  -> ChromaResource
  -> chroma_model.rag_context()
  -> semantic search
  -> context string + source results
```

## 8. Command Reference

### MongoDB commands

| Command | Purpose |
| --- | --- |
| `register` | Creates a user document in MongoDB. |
| `login` | Authenticates a user and writes `.session.json`. |
| `logout` | Removes local session state. |
| `get_profile` | Reads the logged-in user's MongoDB profile. |
| `create_note` | Creates a personal note document. |
| `get_notes` | Reads notes for the logged-in user. |
| `update_note` | Updates an existing note by id. |
| `delete_note` | Deletes an existing note by id. |
| `create_content` | Creates a content document. |
| `like_content` | Likes an existing content item by id. |
| `comment_content` | Adds a comment to an existing content item. |
| `get_comments` | Reads comments for a content item. |
| `get_own_comments` | Reads comments written by the logged-in user. |
| `share_content` | Shares content with another user. |
| `share_content_ext` | Records an external share. |

### Dgraph commands

| Command | Purpose |
| --- | --- |
| `dgraph_setup` | Installs the Dgraph schema. |
| `dgraph_seed` | Loads sample graph data. |
| `graph_summary` | Shows follower and attendee counts. |
| `follow_user --user_id <id>` | Creates a user-to-user follow edge. |
| `recommend_user` | Recommends users by shared interests. |
| `recommend_user_loc` | Recommends users by location. |
| `local_events` | Finds future events in the user's city. |
| `recommend_events` | Recommends events by shared interests. |
| `attend_event --event_id <id>` | Creates a user-to-event attendance edge. |

### ChromaDB commands

| Command | Purpose |
| --- | --- |
| `chroma_setup` | Creates the ChromaDB collection. |
| `chroma_seed` | Loads embedded sample content. |
| `semantic_search --query "..."` | Searches content by semantic meaning. |
| `recommend_content --preferences "..."` | Recommends content from preferences. |
| `rag_context --query "..."` | Retrieves context for a future RAG answer. |

## 9. Requirements / Rubric Mapping

| Command | Database | Feature | Requirement covered | Rubric item | Short explanation |
| --- | --- | --- | --- | --- | --- |
| `register` | MongoDB | User registration | FR-01 | Document CRUD | Creates a user document with profile fields. |
| `login` | MongoDB | User login/session | FR-02 | Functional implementation | Authenticates with MongoDB and writes `.session.json`. |
| `get_profile` | MongoDB | Read profile | FR-03 support | Document query | Retrieves the current user's document. |
| `create_note` | MongoDB | Personal notes | FR-21 | Document creation | Stores a nested user note document. |
| `get_notes` | MongoDB | Retrieve notes | FR-22 | Document query | Reads notes by logged-in user. |
| `create_content` | MongoDB | Create content | FR-06 | Document creation | Stores content as a MongoDB document. |
| `dgraph_setup` | Dgraph | Graph schema | Dgraph rubric | Schema, indexes, reverse edges | Defines node predicates, indexes, and reverse traversals. |
| `dgraph_seed` | Dgraph | Graph seed data | Dgraph rubric | Data loading | Creates users, events, interests, follows, attendance, and topic edges. |
| `graph_summary` | Dgraph | Counts | Dgraph rubric | Aggregation + reverse traversal | Uses `count(~follows)` and `count(~attends)`. |
| `recommend_user` | Dgraph | User recommendation | FR-14 | Graph traversal | Finds users connected through shared interests. |
| `recommend_user_loc` | Dgraph | Location recommendation | FR-15 | Indexed query | Filters users by indexed location. |
| `local_events` | Dgraph | Local events | FR-25 | Query-driven graph modeling | Finds future events in the user's city. |
| `attend_event` | Dgraph | Attend event | FR-26 | Relationship mutation | Creates a `User attends Event` edge. |
| `recommend_events` | Dgraph | Event recommendation | FR-27 | Graph traversal | Traverses from user interests to event topics. |
| `chroma_setup` | ChromaDB | Vector collection | Vector rubric | Setup logic | Creates the persistent Chroma collection. |
| `chroma_seed` | ChromaDB | Embedded content | Vector rubric | Embeddings + loading | Loads documents and generates embeddings. |
| `semantic_search` | ChromaDB | Semantic search | FR-30 | Vector retrieval | Searches by meaning instead of exact text. |
| `recommend_content` | ChromaDB | Content recommendation | FR-24 | Vector retrieval | Uses preferences as a semantic query. |
| `rag_context` | ChromaDB | Retrieval context | FR-31 partial | RAG foundation | Returns retrieved context, but does not call an LLM. |

## 10. Troubleshooting

### Docker is not running

Symptom:

```text
Cannot connect to the Docker daemon
```

Fix:

```bash
docker compose up -d
```

If that fails, open Docker Desktop and try again.

### MongoDB connection error

Symptom:

```text
ServerSelectionTimeoutError
```

Likely cause: MongoDB is not running or port `27017` is already in use.

Fix:

```bash
docker compose ps
docker compose up -d mongodb
```

Check the port if needed:

```bash
lsof -i :27017
```

### Email already registered

Symptom:

```text
Email already registered
```

Fix: use another email or reset MongoDB data:

```bash
docker compose down -v
docker compose up -d
```

Then run setup/seed commands again.

### API server is not running

Symptom: CLI commands fail with connection errors to `localhost:8000`.

Fix:

```bash
uvicorn main:app --reload
```

If port `8000` is busy:

```bash
uvicorn main:app --reload --port 8001
export PROJECT_API_URL=http://localhost:8001
```

### User not logged in

Symptom:

```text
Error: User not logged in. Please login first.
```

Fix:

```bash
python3 main.py login --email demo@mail.com --password 1234
```

If the user does not exist yet:

```bash
python3 main.py register --username demo --email demo@mail.com --password 1234 --age 21 --location Guadalajara --preferences prayer
python3 main.py login --email demo@mail.com --password 1234
```

### Dgraph is not responding

Symptom: Dgraph setup or query commands cannot connect to `localhost:8080`.

Fix:

```bash
docker compose up -d dgraph
curl http://localhost:8080/health
python3 main.py dgraph_setup
python3 main.py dgraph_seed
```

### Empty Dgraph results

Likely causes:

- `dgraph_seed` was not run.
- The API server is not running.
- The session user has not been copied into Dgraph yet.

Fix:

```bash
python3 main.py dgraph_seed
python3 main.py login --email demo@mail.com --password 1234
python3 main.py graph_summary
```

`graph_summary` is a useful check because it also ensures the logged-in Mongo user exists as a Dgraph user.

### ChromaDB returns empty or weak results

Likely cause: Chroma was not seeded or the local Chroma folder is stale.

Fix:

```bash
rm -rf chroma_db
python3 main.py chroma_setup
python3 main.py chroma_seed
```

### Chroma dependency/model error

Symptom: errors mentioning `chromadb`, `sentence_transformers`, or model download.

Fix:

```bash
python3 -m pip install -r requirements.txt
```

The first Chroma run may download the embedding model, so it can take longer than later runs.

## 11. Known Limitations

- This is a school project, not production software.
- Error handling is basic and kept simple on purpose.
- Demo data is small and sample-based.
- ChromaDB implements retrieval/context for RAG, but it does not call an LLM.
- Cassandra is only partially integrated and is not part of the main runnable demo.
- Some MongoDB commands require existing ObjectIds, such as liking or commenting on content, so the main demo uses simpler Mongo flows that are easier to run cleanly.

## 12. Recommended Demo Sequence

For the final demo, this is the safest order:

```bash
docker compose down -v
rm -f .session.json
rm -rf chroma_db
docker compose up -d

python3 main.py dgraph_setup
python3 main.py dgraph_seed
python3 main.py chroma_setup
python3 main.py chroma_seed
```

Start the API in one terminal:

```bash
uvicorn main:app --reload
```

Run the demo commands in another terminal:

```bash
python3 main.py register --username demo --email demo@mail.com --password 1234 --age 21 --location Guadalajara --preferences prayer
python3 main.py login --email demo@mail.com --password 1234
python3 main.py get_profile

python3 main.py create_note --title "Demo note" --text "This is a personal note saved in MongoDB."
python3 main.py get_notes
python3 main.py create_content --title "Peaceful Evening Prayer" --type prayer

python3 main.py graph_summary
python3 main.py recommend_user
python3 main.py recommend_user_loc
python3 main.py local_events
python3 main.py recommend_events
python3 main.py attend_event --event_id e1
python3 main.py graph_summary

python3 main.py semantic_search --query "anxiety and peace"
python3 main.py recommend_content --preferences "prayer meditation"
python3 main.py rag_context --query "How can I feel calm when stressed?"
```

This sequence covers the working MongoDB, Dgraph, and ChromaDB parts without relying on incomplete Cassandra functionality.
