#!/usr/bin/env python3
import falcon

from dgraph import dgraph_model


class DgraphResource:
    def __init__(self):
        pass

    async def on_get(self, req, resp, action):
        # This resource is the HTTP/API side of the Dgraph implementation.
        # It receives a simple action name and calls the matching Dgraph function.
        if action == "summary":
            resp.media = dgraph_model.graph_summary()
            resp.status = falcon.HTTP_200
            return

        user_id = req.get_param("user_id", required=True)

        if action == "recommend-users":
            resp.media = dgraph_model.recommend_users(user_id)
        elif action == "recommend-users-by-location":
            resp.media = dgraph_model.recommend_users_by_location(user_id)
        elif action == "local-events": # AQUI ME QUEDE
            resp.media = dgraph_model.local_events(user_id)
        elif action == "recommend-events":
            resp.media = dgraph_model.recommend_events(user_id)
        else:
            raise falcon.HTTPNotFound()

        resp.status = falcon.HTTP_200

    async def on_post(self, req, resp, action):
        data = await req.media

        try:
            if action == "follow":
                dgraph_model.follow_user(data["user_id"], data["target_user_id"])
                resp.media = {"message": "Follow relationship created"}
            elif action == "attend":
                dgraph_model.attend_event(data["user_id"], data["event_id"])
                resp.media = {"message": "Attendance relationship created"}
            else:
                raise falcon.HTTPNotFound()
        except KeyError as error:
            raise falcon.HTTPBadRequest(
                title="Missing field",
                description=f"{error.args[0]} is required",
            )
        except ValueError as error:
            raise falcon.HTTPBadRequest(
                title="Invalid graph request",
                description=str(error),
            )
        except RuntimeError as error:
            raise falcon.HTTPBadRequest(
                title="Dgraph backend error",
                description=str(error),
            )

        resp.status = falcon.HTTP_201
