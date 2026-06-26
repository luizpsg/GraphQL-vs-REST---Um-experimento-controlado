"""Servidor unico que expoe a MESMA base de dados via REST e GraphQL.

Manter os dois paradigmas no mesmo processo, mesma stack (Flask) e mesma fonte
de dados garante um experimento controlado: a unica diferenca entre os
tratamentos e o estilo de API, nao a infraestrutura.

REST  -> rotas tradicionais baseadas em recursos (/users, /posts, ...).
GraphQL -> endpoint unico /graphql com schema tipado.
"""

import json
import os

from ariadne import (
    QueryType, ObjectType, make_executable_schema, graphql_sync,
)
from flask import Flask, jsonify, request, abort

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "dataset.json")

with open(DATA_PATH, "r", encoding="utf-8") as _f:
    DB = json.load(_f)

USERS = {u["id"]: u for u in DB["users"]}
POSTS = {p["id"]: p for p in DB["posts"]}
COMMENTS = {c["id"]: c for c in DB["comments"]}
POSTS_BY_USER = {}
for _p in DB["posts"]:
    POSTS_BY_USER.setdefault(_p["userId"], []).append(_p)
COMMENTS_BY_POST = {}
for _c in DB["comments"]:
    COMMENTS_BY_POST.setdefault(_c["postId"], []).append(_c)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# REST
# ---------------------------------------------------------------------------


@app.get("/rest/users")
def rest_users():
    return jsonify(DB["users"])


@app.get("/rest/users/<int:uid>")
def rest_user(uid):
    user = USERS.get(uid)
    if user is None:
        abort(404)
    return jsonify(user)


@app.get("/rest/users/<int:uid>/posts")
def rest_user_posts(uid):
    return jsonify(POSTS_BY_USER.get(uid, []))


@app.get("/rest/posts/<int:pid>")
def rest_post(pid):
    post = POSTS.get(pid)
    if post is None:
        abort(404)
    return jsonify(post)


@app.get("/rest/posts/<int:pid>/comments")
def rest_post_comments(pid):
    return jsonify(COMMENTS_BY_POST.get(pid, []))


# ---------------------------------------------------------------------------
# GraphQL
# ---------------------------------------------------------------------------

type_defs = """
    type User {
        id: ID!
        name: String!
        username: String!
        email: String!
        phone: String!
        website: String!
        company: String!
        city: String!
        bio: String!
        createdAt: String!
        posts: [Post!]!
    }

    type Post {
        id: ID!
        userId: ID!
        title: String!
        body: String!
        tags: [String!]!
        likes: Int!
        createdAt: String!
        comments: [Comment!]!
    }

    type Comment {
        id: ID!
        postId: ID!
        name: String!
        email: String!
        body: String!
    }

    type Query {
        users: [User!]!
        user(id: ID!): User
        post(id: ID!): Post
    }
"""

query = QueryType()
user_type = ObjectType("User")
post_type = ObjectType("Post")


@query.field("users")
def resolve_users(*_):
    return DB["users"]


@query.field("user")
def resolve_user(_, __, id):
    return USERS.get(int(id))


@query.field("post")
def resolve_post(_, __, id):
    return POSTS.get(int(id))


@user_type.field("posts")
def resolve_user_posts(obj, _):
    return POSTS_BY_USER.get(obj["id"], [])


@post_type.field("comments")
def resolve_post_comments(obj, _):
    return COMMENTS_BY_POST.get(obj["id"], [])


schema = make_executable_schema(type_defs, query, user_type, post_type)


@app.post("/graphql")
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(schema, data, context_value={"request": request})
    status = 200 if success else 400
    return jsonify(result), status


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


def run(host="127.0.0.1", port=5055):
    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)


if __name__ == "__main__":
    run()
