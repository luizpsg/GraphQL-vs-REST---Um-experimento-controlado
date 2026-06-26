"""Gerador de dataset sintetico para o experimento GraphQL vs REST.

Cria uma base de dados relacional (usuarios -> posts -> comentarios) que e
servida de forma identica pelos endpoints REST e GraphQL. Por ser gerada com
semente fixa, o dataset e deterministico e o experimento e reproduzivel.
"""

import json
import os
import random

SEED = 42
N_USERS = 50
POSTS_PER_USER = 5
COMMENTS_PER_POST = 8

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

FIRST_NAMES = [
    "Ana", "Bruno", "Carla", "Diego", "Elisa", "Felipe", "Gabriela", "Heitor",
    "Isabela", "Joao", "Karina", "Lucas", "Marina", "Nicolas", "Olivia",
    "Pedro", "Quesia", "Rafael", "Sofia", "Thiago", "Ursula", "Vinicius",
    "Wagner", "Xenia", "Yara", "Zeca",
]
LAST_NAMES = [
    "Silva", "Souza", "Oliveira", "Santos", "Pereira", "Lima", "Carvalho",
    "Ferreira", "Rodrigues", "Almeida", "Costa", "Gomes", "Martins", "Araujo",
    "Ribeiro", "Teixeira", "Curi", "Saud",
]
CITIES = [
    "Belo Horizonte", "Sao Paulo", "Rio de Janeiro", "Curitiba", "Salvador",
    "Recife", "Porto Alegre", "Fortaleza", "Brasilia", "Manaus",
]
LOREM = (
    "lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua ut enim ad minim "
    "veniam quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat duis aute irure dolor in reprehenderit in voluptate"
).split()


def _sentence(rnd, min_w=6, max_w=18):
    n = rnd.randint(min_w, max_w)
    words = rnd.choices(LOREM, k=n)
    return " ".join(words).capitalize() + "."


def _paragraph(rnd, min_s=3, max_s=7):
    return " ".join(_sentence(rnd) for _ in range(rnd.randint(min_s, max_s)))


def generate():
    rnd = random.Random(SEED)
    users = []
    posts = []
    comments = []

    post_id = 1
    comment_id = 1

    for uid in range(1, N_USERS + 1):
        first = rnd.choice(FIRST_NAMES)
        last = rnd.choice(LAST_NAMES)
        name = f"{first} {last}"
        username = f"{first.lower()}.{last.lower()}{uid}"
        users.append({
            "id": uid,
            "name": name,
            "username": username,
            "email": f"{username}@example.com",
            "phone": f"+55 (31) 9{rnd.randint(1000,9999)}-{rnd.randint(1000,9999)}",
            "website": f"https://{username}.example.com",
            "company": f"{last} {rnd.choice(['LTDA','SA','ME','EIRELI'])}",
            "city": rnd.choice(CITIES),
            "bio": _paragraph(rnd, 3, 6),
            "createdAt": f"20{rnd.randint(18,24):02d}-{rnd.randint(1,12):02d}-"
                         f"{rnd.randint(1,28):02d}",
        })

        for _ in range(POSTS_PER_USER):
            posts.append({
                "id": post_id,
                "userId": uid,
                "title": _sentence(rnd, 4, 10).rstrip("."),
                "body": _paragraph(rnd, 5, 10),
                "tags": rnd.sample(
                    ["tech", "graphql", "rest", "api", "web", "db", "perf",
                     "research"], k=rnd.randint(2, 4)),
                "likes": rnd.randint(0, 5000),
                "createdAt": f"202{rnd.randint(0,4)}-{rnd.randint(1,12):02d}-"
                             f"{rnd.randint(1,28):02d}",
            })

            for _ in range(COMMENTS_PER_POST):
                comments.append({
                    "id": comment_id,
                    "postId": post_id,
                    "name": rnd.choice(FIRST_NAMES) + " " + rnd.choice(LAST_NAMES),
                    "email": f"user{comment_id}@example.com",
                    "body": _paragraph(rnd, 2, 5),
                })
                comment_id += 1
            post_id += 1

    return {"users": users, "posts": posts, "comments": comments}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    data = generate()
    out = os.path.join(DATA_DIR, "dataset.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Dataset gerado: {out}")
    print(f"  usuarios:    {len(data['users'])}")
    print(f"  posts:       {len(data['posts'])}")
    print(f"  comentarios: {len(data['comments'])}")


if __name__ == "__main__":
    main()
