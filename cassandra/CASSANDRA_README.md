# Cassandra Part of the Project

The main idea is:

- MongoDB stores the operational application documents.
- Dgraph stores graph relationships.
- ChromaDB stores vectorized text search data.
- Cassandra stores high-volume activity logs and analytics-friendly event data.

## 1. What Cassandra Is Used For

Cassandra handles the event history and analytics features of the app.

It is a good fit here because activity logs are:

- append-heavy
- time-based
- queried by user, by day, and by content

That matches Cassandra well.

## 2. Requirements Covered

| Requirement | Feature |
|---|---|
| FR-05 | Session tracking |
| FR-16 | Activity history |
| FR-17 | Filter activity history |
| FR-20 | Daily active users |
| FR-32 | Content engagement metrics |
| FR-33 | System-wide activity stats |
| FR-34 | Trending content |

The same logging tables also support activity types related to:

- likes
- comments
- internal shares
- external shares
- views
- notes

## 3. Data Model

The Cassandra schema is denormalized on purpose.

Instead of one normalized table, the project writes the same event into multiple query tables so reads stay simple and fast.

### Table 1: `activity_by_user`

Used for:

- full user activity history
- filtering by type
- filtering by date after fetching the user's timeline

Partition key:

```text
user_id
```

Clustering columns:

```text
timestamp, activity_id
```

### Table 2: `activity_by_day`

Used for:

- daily active users
- daily system stats
- trending content by day

Partition key:

```text
date
```

Clustering columns:

```text
timestamp, activity_id
```

### Table 3: `activity_by_content`

Used for:

- engagement metrics for one content item

Partition key:

```text
content_id
```

Clustering columns:

```text
timestamp, activity_id
```

## 4. What One Event Looks Like

Each logged activity stores data like:

```text
user_id
timestamp
activity_id
activity_type
content_id
metadata
```

Examples of `activity_type`:

- `login`
- `logout`
- `like`
- `comment`
- `share_internal`
- `share_external`
- `view`
- `note`

## 5. Key Files

| File | Purpose |
|---|---|
| `cassandra/cassandra_model.py` | Pure Cassandra schema, inserts, and analytics queries |
| `cassandra/fixtures.py` | CLI handlers used by `main.py` |
| `cassandra/cassandra_client.py` | Compatibility wrapper that re-exports the CLI handlers |
| `main.py` | Registers Cassandra CLI commands |

## 6. Connection Settings

The Cassandra code reads these environment variables:

| Variable | Default |
|---|---|
| `CASSANDRA_CLUSTER_IPS` | `localhost,node01` |
| `CASSANDRA_KEYSPACE` | `hallow_db` |
| `CASSANDRA_REPLICATION_FACTOR` | `1` |

In your Docker setup, Cassandra is exposed on:

```text
9042:9042
```

and the container name is:

```text
node01
```

Because of that, the default contact points already support both:

- `localhost`
- `node01`

## 7. Main Flow

The Cassandra path is a direct CLI flow.

Unlike the Dgraph and Chroma user actions, these commands do not go through Falcon HTTP resources first.

Flow:

```text
Terminal
  -> main.py parser
  -> cassandra/fixtures.py handler
  -> cassandra/cassandra_model.py
  -> Cassandra tables
```

When a Cassandra command runs:

1. `main.py` parses the command.
2. It calls the matching function in `cassandra/fixtures.py`.
3. The fixture code opens a Cassandra session if needed.
4. The schema is created if it does not exist yet.
5. The event is inserted or the query is executed.
6. The result is printed in the terminal.

There is also an automatic integration path now:

```text
Mongo CLI action
  -> mongo/client.py
  -> Mongo/Falcon API request succeeds
  -> Cassandra event is logged automatically
```

That means actions such as login, logout, like, comment, share, and note creation now populate Cassandra without needing a separate manual `log_activity` command.

## 8. Available Commands

### Log login or logout

```bash
python main.py log_session --user_id 3b014d3f-9e46-4494-b918-ae346e07f910 --event_type login
```

### Log a general activity

```bash
python main.py log_activity --user_id 3b014d3f-9e46-4494-b918-ae346e07f910 --activity_type like --content_id 5f7d0bc3-4d10-48ba-b711-da31a896fd25 --metadata "manual test"
```

### Get full activity history

```bash
python main.py get_activity_history --user_id 3b014d3f-9e46-4494-b918-ae346e07f910 --limit 20
```

### Filter activity history

By type:

```bash
python main.py filter_activity --user_id 3b014d3f-9e46-4494-b918-ae346e07f910 --activity_type like --limit 20
```

By date:

```bash
python main.py filter_activity --user_id 3b014d3f-9e46-4494-b918-ae346e07f910 --date 2026-05-10 --limit 20
```

### Daily active users

```bash
python main.py get_daily_active_users --date 2026-05-10
```

### Content metrics

```bash
python main.py get_content_metrics --content_id 5f7d0bc3-4d10-48ba-b711-da31a896fd25
```

### System stats

```bash
python main.py get_system_stats --date 2026-05-10
```

### Trending content

```bash
python main.py trending_content --date 2026-05-10 --limit 5
```

## 9. Tested Functional Flow

The Cassandra integration was tested successfully with Python `3.11` using the CLI commands in `main.py`.

The smoke test covered:

- Mongo-driven automatic logging for:
  - `login`
  - `logout`
  - `like_content`
  - `comment_content`
  - `share_content`
  - `share_content_ext`
  - `create_note`
- logging a `login` event
- logging `like` and `comment` events with a `content_id`
- retrieving full activity history
- filtering by `activity_type`
- counting daily active users
- reading content engagement metrics
- reading daily system stats
- reading trending content

Observed successful results included:

- 7 automatic events written for one Mongo user in one smoke run
- correct activity history for `login`, `like`, `comment`, `share_internal`, `share_external`, `note`, and `logout`
- 4 interactions counted for the test content
- correct trending ranking for the test content
- end-to-end verification that Mongo actions generated Cassandra analytics automatically

## 10. Important Implementation Notes

### Keyspace name

The keyspace is intentionally lowercase:

```text
hallow_db
```

This avoids case-sensitivity issues when the driver switches keyspaces.

### Lazy connection

The Cassandra driver is imported lazily inside `cassandra/fixtures.py`.

That is useful because:

- `main.py --help` can still work even if Cassandra is temporarily unavailable
- the rest of the project is not blocked just by importing the Cassandra module

### UUIDs

The Cassandra tables still use UUID partition keys internally, but the CLI now accepts regular Mongo ObjectId strings too.

That means you can run commands like:

```bash
python main.py get_activity_history --user_id 6a013ffaddd1aecef4e360f7 --limit 20
python main.py get_content_metrics --content_id 6a014002ddd1aecef4e360f9
```

The Cassandra fixture layer deterministically maps those Mongo ids to internal UUID keys and also stores the original ids as readable references, so output and analytics stay understandable.

## 11. Troubleshooting

### Error: keyspace does not exist

This was caused by mixed-case keyspace naming before the fix.

The current code now uses:

```text
hallow_db
```

### Error: driver fails to initialize

Use Python `3.11` for this project environment.

Some Cassandra driver builds fail on newer Python versions because of event loop compatibility issues.

### Error: cannot connect to Cassandra

Check:

- Cassandra container is running
- port `9042` is exposed
- `CASSANDRA_CLUSTER_IPS` points to `localhost`, `node01`, or both

Example:

```powershell
$env:CASSANDRA_CLUSTER_IPS="localhost,node01"
venv\Scripts\python.exe main.py get_daily_active_users --date 2026-05-10
```

## 12. Quick Summary

Cassandra in this project is the analytics and activity-log database.

It stores events in multiple query-shaped tables so the app can answer:

- what did this user do?
- who was active today?
- how much engagement did this content get?
- what content is trending today?
