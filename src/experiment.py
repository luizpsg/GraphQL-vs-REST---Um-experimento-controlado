"""Execucao do experimento controlado GraphQL vs REST.

Para cada CENARIO de consulta e cada TRATAMENTO (REST | GraphQL) realiza N
medicoes, registrando duas variaveis dependentes:

  * latency_ms   -> tempo de resposta de ponta a ponta (ms)
  * size_bytes   -> tamanho total do payload recebido (bytes)

Os cenarios foram escolhidos para exercitar situacoes onde a teoria preve
diferencas (over-fetching e o problema N+1) e tambem casos simples de controle.

O servidor (src/server.py) e iniciado automaticamente como subprocesso, de modo
que basta executar este arquivo para reproduzir o experimento.
"""

import csv
import os
import subprocess
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

HOST = "127.0.0.1"
PORT = 5055
BASE = f"http://{HOST}:{PORT}"

N_MEASUREMENTS = 200      # medicoes por (cenario x tratamento)
N_WARMUP = 20             # execucoes descartadas (aquecimento JIT/cache/conexao)

# Cenarios: id, descricao curta, e quantos usuarios/posts envolve.
SCENARIOS = {
    "C1_single_full": "Recurso unico completo (1 usuario, todos os campos)",
    "C2_single_partial": "Recurso unico parcial (1 usuario, 3 campos)",
    "C3_nested_n1": "Consulta aninhada (usuario + posts + comentarios)",
    "C4_collection": "Colecao (50 usuarios completos)",
}

TARGET_USER_ID = 7   # usuario alvo para cenarios de recurso unico/aninhado


# ---------------------------------------------------------------------------
# Sessoes HTTP reutilizaveis (keep-alive para nao medir handshake repetido)
# ---------------------------------------------------------------------------
session = requests.Session()


# ---------------------------------------------------------------------------
# Implementacao dos tratamentos por cenario.
# Cada funcao retorna o numero total de bytes recebidos no payload.
# ---------------------------------------------------------------------------

def rest_c1():
    r = session.get(f"{BASE}/rest/users/{TARGET_USER_ID}")
    return len(r.content)


def gql_c1():
    q = """
    query($id: ID!) {
      user(id: $id) {
        id name username email phone website company city bio createdAt
      }
    }"""
    r = session.post(f"{BASE}/graphql",
                     json={"query": q, "variables": {"id": TARGET_USER_ID}})
    return len(r.content)


def rest_c2():
    # REST nao seleciona campos -> retorna objeto completo (over-fetching).
    r = session.get(f"{BASE}/rest/users/{TARGET_USER_ID}")
    return len(r.content)


def gql_c2():
    q = """
    query($id: ID!) {
      user(id: $id) { id name email }
    }"""
    r = session.post(f"{BASE}/graphql",
                     json={"query": q, "variables": {"id": TARGET_USER_ID}})
    return len(r.content)


def rest_c3():
    # Problema N+1: 1 req do usuario + 1 dos posts + 1 por post para comentarios.
    total = 0
    r = session.get(f"{BASE}/rest/users/{TARGET_USER_ID}")
    total += len(r.content)
    rp = session.get(f"{BASE}/rest/users/{TARGET_USER_ID}/posts")
    total += len(rp.content)
    for post in rp.json():
        rc = session.get(f"{BASE}/rest/posts/{post['id']}/comments")
        total += len(rc.content)
    return total


def gql_c3():
    q = """
    query($id: ID!) {
      user(id: $id) {
        id name email
        posts {
          id title likes
          comments { id name body }
        }
      }
    }"""
    r = session.post(f"{BASE}/graphql",
                     json={"query": q, "variables": {"id": TARGET_USER_ID}})
    return len(r.content)


def rest_c4():
    r = session.get(f"{BASE}/rest/users")
    return len(r.content)


def gql_c4():
    q = """
    query {
      users {
        id name username email phone website company city bio createdAt
      }
    }"""
    r = session.post(f"{BASE}/graphql", json={"query": q})
    return len(r.content)


TREATMENTS = {
    "C1_single_full": {"REST": rest_c1, "GraphQL": gql_c1},
    "C2_single_partial": {"REST": rest_c2, "GraphQL": gql_c2},
    "C3_nested_n1": {"REST": rest_c3, "GraphQL": gql_c3},
    "C4_collection": {"REST": rest_c4, "GraphQL": gql_c4},
}


def wait_for_server(timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = session.get(f"{BASE}/health", timeout=1)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            time.sleep(0.3)
    return False


def measure(fn):
    """Executa fn uma vez e retorna (latency_ms, size_bytes)."""
    t0 = time.perf_counter()
    size = fn()
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0, size


def run_experiment():
    out_path = os.path.join(DATA_DIR, "results.csv")
    rows = []
    run_id = 0

    # Ordem intercalada (REST/GraphQL alternados) para diluir efeitos temporais.
    for scenario in SCENARIOS:
        for api in ("REST", "GraphQL"):
            fn = TREATMENTS[scenario][api]
            for _ in range(N_WARMUP):
                fn()

    for i in range(N_MEASUREMENTS):
        for scenario in SCENARIOS:
            for api in ("REST", "GraphQL"):
                fn = TREATMENTS[scenario][api]
                latency, size = measure(fn)
                run_id += 1
                rows.append({
                    "run_id": run_id,
                    "iteration": i + 1,
                    "scenario": scenario,
                    "scenario_desc": SCENARIOS[scenario],
                    "api": api,
                    "latency_ms": round(latency, 4),
                    "size_bytes": size,
                })
        if (i + 1) % 25 == 0:
            print(f"  progresso: {i + 1}/{N_MEASUREMENTS} iteracoes")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResultados salvos em: {out_path}")
    print(f"Total de medicoes: {len(rows)}")
    return out_path


def main():
    # Garante dataset.
    if not os.path.exists(os.path.join(DATA_DIR, "dataset.json")):
        print("Dataset nao encontrado, gerando...")
        subprocess.run([sys.executable, os.path.join(ROOT, "src", "data_gen.py")],
                       check=True)

    print("Iniciando servidor...")
    server_proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "src", "server.py")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_for_server():
            raise RuntimeError("Servidor nao respondeu a tempo.")
        print("Servidor no ar. Iniciando medicoes...\n")
        run_experiment()
    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        print("Servidor encerrado.")


if __name__ == "__main__":
    main()
