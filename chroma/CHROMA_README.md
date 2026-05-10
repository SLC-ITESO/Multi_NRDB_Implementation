# ChromaDB Part of the Project

This README explains the ChromaDB part of the project in simple English.

The main idea is easy:

- Dgraph stores relationships between users and events.
- ChromaDB stores text content as embeddings.
- Embeddings let us search by meaning, not only by exact words.

## 1. What ChromaDB Is Used For

ChromaDB is the vector database part of the project.

It stores short content items like prayer, meditation, hope, and community text. In this project, a MiniLM sentence embedding model turns each item into a vector, and then ChromaDB compares the query vector against the stored document vectors.

That is why ChromaDB is useful for:

- semantic search
- content recommendation
- RAG retrieval context

## 2. What Semantic Search Means

Semantic search means searching by meaning, not only by exact keyword match.

Example:

```text
Query: "I feel anxious and need peace"
```

Even if the database does not contain that exact sentence, ChromaDB can still return content like:

- Meditation for Anxiety
- Evening Prayer
- Hope in Difficult Times

Why?

Because the query and the documents are both converted into embeddings, and the system compares how close those vectors are.

So the search is based on similarity in meaning, not just shared words.

Simple version:

```text
text -> MiniLM embedding -> compare vectors -> return the closest matches
```

## 3. Requirements Covered

| Requirement | Name | Why ChromaDB fits |
|---|---|---|
| FR-24 | Recommend Content | Content can be recommended by matching user preferences to embedded content. |
| FR-30 | Semantic Search | ChromaDB searches by meaning using embeddings. |
| FR-31 | RAG Response Generation | The code retrieves relevant context that could be sent to an LLM later. |

## 4. Data Model

The Chroma collection is called:

```text
religious_content
```

Each record stores:

- `id`: content id
- `document`: the text that gets embedded
- `metadata.title`
- `metadata.type`
- `metadata.tags`
- `embedding`: the vector representation of the document

The seed data includes simple religious and wellness content such as:

- Hope in Difficult Times
- Evening Prayer
- Meditation for Anxiety
- Serving the Community
- Learning Forgiveness

## 5. What Gets Embedded

The project embeds a combined text like this:

```text
Title. Tags: tag1, tag2. Main content text.
```

This is useful because the search can match against:

- the title
- the tags
- the body of the content

## 6. How the Embedding Works

This project uses a real local embedding model: `all-MiniLM-L6-v2`.

That model takes text and converts it into a vector automatically. You do not count words by hand.

The basic idea is still the same:

- text becomes a vector
- similar vectors are close together
- close vectors mean similar meaning

MiniLM is a good fit here because it is small, fast, and easy to run locally.

## 7. Main Flow

### Admin flow

These commands prepare the collection directly:

```text
CLI command
  -> main.py parser
  -> chroma/client.py
  -> chroma/chroma_model.py
  -> local ChromaDB collection
```

### User/API flow

These commands go through the Falcon API first:

```text
CLI command
  -> main.py parser
  -> chroma/client.py
  -> Falcon API /chroma/{action}
  -> chroma/resources.py
  -> chroma/chroma_model.py
  -> ChromaDB collection query
  -> result printed to terminal
```

## 8. Main Commands

Create the collection:

```bash
python3 main.py chroma_setup
```

Load seed content:

```bash
python3 main.py chroma_seed
```

Run semantic search:

```bash
python3 main.py semantic_search --query "stress and anxiety"
```

Retrieve RAG context:

```bash
python3 main.py rag_context --query "I need peace before sleeping"
```

Recommend content:

```bash
python3 main.py recommend_content --preferences "prayer peace"
```

You can also use a session file with preferences:

```bash
printf '{"user_id":"u1","username":"mariano","preferences":["prayer","meditation"]}' > .session.json
python3 main.py recommend_content
```

## 9. Example Searches

### Semantic Search

Command:

```bash
python3 main.py semantic_search --query "anxiety and calm breathing"
```

Expected kind of result:

```json
[
  {
    "id": "content_meditation",
    "title": "Meditation for Anxiety",
    "type": "meditation",
    "tags": "meditation,anxiety,peace",
    "distance": 0.25,
    "document": "Meditation for Anxiety. Tags: meditation,anxiety,peace..."
  }
]
```

### RAG Context

Command:

```bash
python3 main.py rag_context --query "How can I deal with stress?"
```

Expected kind of result:

```json
{
  "query": "How can I deal with stress?",
  "context": "Hope in Difficult Times: ...",
  "results": [...],
  "note": "This is the retrieval/context step for a future RAG response."
}
```

## 10. API Endpoints

The Chroma API uses one route pattern:

```text
/chroma/{action}
```

GET endpoints:

```text
GET /chroma/search?query=stress
GET /chroma/rag-context?query=peace
GET /chroma/recommend-content?preferences=prayer
```

## 11. How to Run

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Create and seed the collection:

```bash
python3 main.py chroma_setup
python3 main.py chroma_seed
```

Run the backend:

```bash
uvicorn main:app --reload
```

Test the commands:

```bash
python3 main.py semantic_search --query "anxiety and peace"
python3 main.py rag_context --query "I need hope"
python3 main.py recommend_content --preferences "community service"
```

## 12. Rubric Alignment

This ChromaDB implementation covers the vector database rubric:

- Embeddings are integrated: each content item is stored as a vector.
- Semantic retrieval is implemented: `semantic_search` searches by meaning.
- RAG-style retrieval is implemented: `rag_context` returns context for a future LLM answer.
- Query-driven modeling: the collection is designed around semantic search and recommendations.
- Functional implementation: CLI commands and API endpoints are connected.
- Clear seed/load logic: `chroma_seed` loads sample content.

