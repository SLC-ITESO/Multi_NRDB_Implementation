#!/usr/bin/env python3
import falcon

from chroma import chroma_model


class ChromaResource:
    def __init__(self):
        pass

    async def on_get(self, req, resp, action):
        # This resource exposes simple ChromaDB queries through the API.
        query = req.get_param("query")
        limit = int(req.get_param("limit") or 3)

        if action == "search":
            if not query:
                raise falcon.HTTPBadRequest(title="Missing query")
            resp.media = chroma_model.semantic_search(query, limit)
        elif action == "rag-context":
            if not query:
                raise falcon.HTTPBadRequest(title="Missing query")
            resp.media = chroma_model.rag_context(query, limit)
        elif action == "recommend-content":
            preferences = req.get_param("preferences")
            if not preferences:
                raise falcon.HTTPBadRequest(title="Missing preferences")
            resp.media = chroma_model.recommend_content(preferences, limit)
        else:
            raise falcon.HTTPNotFound()

        resp.status = falcon.HTTP_200
