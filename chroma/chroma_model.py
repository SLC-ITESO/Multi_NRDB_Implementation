#!/usr/bin/env python3
import os

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
COLLECTION_NAME = "religious_content_minilm"


SEED_CONTENT = [
    {
        "id": "content_hope",
        "title": "Hope in Difficult Times",
        "type": "reflection",
        "tags": "hope,faith,stress",
        "text": "A short reflection about keeping hope and faith during stressful moments.",
    },
    {
        "id": "content_prayer",
        "title": "Evening Prayer",
        "type": "prayer",
        "tags": "prayer,peace,family",
        "text": "A peaceful evening prayer for family, gratitude, and guidance.",
    },
    {
        "id": "content_meditation",
        "title": "Meditation for Anxiety",
        "type": "meditation",
        "tags": "meditation,anxiety,peace",
        "text": "A calming meditation for anxiety, stress, breathing, and inner peace.",
    },
    {
        "id": "content_service",
        "title": "Serving the Community",
        "type": "article",
        "tags": "community,service,faith",
        "text": "An article about service, community support, and living faith through action.",
    },
    {
        "id": "content_forgiveness",
        "title": "Learning Forgiveness",
        "type": "reflection",
        "tags": "forgiveness,reflection,peace",
        "text": "A reflection about forgiveness, emotional healing, and finding peace.",
    },
]


def setup_collection():
    # This creates the Chroma collection if it does not exist yet.
    _collection()
    return {"message": "ChromaDB collection ready"}


def seed_collection():
    # This function loads a small group of documents so semantic search can be tested.
    collection = _collection()
    ids = [item["id"] for item in SEED_CONTENT]
    documents = [_document_text(item) for item in SEED_CONTENT]
    metadatas = [
        {
            "title": item["title"],
            "type": item["type"],
            "tags": item["tags"],
        }
        for item in SEED_CONTENT
    ]

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )
    return {"message": "ChromaDB seed content loaded", "count": len(ids)}


def semantic_search(query, limit=3):
    # This is the main vector search query.
    collection = _collection()
    result = collection.query(
        query_texts=[query],
        n_results=limit,
        include=["documents", "metadatas", "distances"],
    )
    return _format_results(result)


def recommend_content(preferences, limit=3):
    # This uses the user's preferences as a semantic query.
    # Example: "prayer meditation" should find prayer/meditation content.
    if isinstance(preferences, list):
        query = " ".join(preferences)
    else:
        query = str(preferences)
    return semantic_search(query, limit)


def rag_context(query, limit=3):
    # This is the retrieval part of RAG.
    # We are not calling an LLM here; we return the context that an LLM could use.
    results = semantic_search(query, limit)
    context = "\n\n".join(
        f"{item['title']}: {item['document']}" for item in results
    )
    return {
        "query": query,
        "context": context,
        "results": results,
        "note": "This is the retrieval/context step for a future RAG response.",
    }


def rag_answer(query, limit=3):
    # This is a local demo RAG answer.
    # It retrieves semantic context from ChromaDB and builds a small template answer.
    # No paid API key or external LLM is required for the class demo.
    results = semantic_search(query, limit)
    if not results:
        return {
            "query": query,
            "answer": "Local demo RAG answer: no matching context was found.",
            "sources": [],
        }

    sources = [
        {
            "id": item["id"],
            "title": item["title"],
            "type": item["type"],
            "tags": item["tags"],
        }
        for item in results
    ]
    top_titles = ", ".join(item["title"] for item in results[:2])
    answer = (
        "Local demo RAG answer (template-based, not an external LLM): "
        f"the closest retrieved content is {top_titles}. "
        "Use these sources as the context for answering the question."
    )
    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "context": "\n\n".join(f"{item['title']}: {item['document']}" for item in results),
    }


def _collection():
    chromadb = _chromadb()
    embedding_function = _embedding_function()
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
    )


def _chromadb():
    # Import Chroma only when this file actually needs it.
    # This keeps the rest of the CLI working even before ChromaDB is installed.
    try:
        import chromadb
    except ImportError as error:
        raise RuntimeError(
            "ChromaDB is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error
    return chromadb


def _embedding_function():
    # MiniLM gives us real semantic embeddings without writing embedding math by hand.
    try:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    except ImportError as error:
        raise RuntimeError(
            "sentence-transformers is not installed. Run: python3 -m pip install -r requirements.txt"
        ) from error

    return SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


def _document_text(item):
    # We embed title, tags, and text together because all three help semantic search.
    return f"{item['title']}. Tags: {item['tags']}. {item['text']}"


def _format_results(result):
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    formatted = []
    for index, document in enumerate(documents):
        metadata = metadatas[index]
        formatted.append(
            {
                "id": result["ids"][0][index],
                "title": metadata.get("title"),
                "type": metadata.get("type"),
                "tags": metadata.get("tags"),
                "distance": distances[index],
                "document": document,
            }
        )
    return formatted
