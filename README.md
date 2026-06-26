# GraphQL vs REST — Um Experimento Controlado

Experimento controlado que compara **GraphQL** e **REST** quanto a duas
métricas, respondendo às questões de pesquisa do laboratório:

- **RQ1.** Respostas GraphQL são mais rápidas que respostas REST? (tempo de resposta)
- **RQ2.** Respostas GraphQL têm tamanho menor que respostas REST? (tamanho do payload)

**Autores:** Luiz Paulo Saud, Arthur Curi e Helio Teixeira.

## Resumo do desenho experimental

| Item | Definição |
|------|-----------|
| Variável independente | Estilo de API (REST \| GraphQL) |
| Fator de bloqueio | Cenário de consulta (C1–C4) |
| Variáveis dependentes | `latency_ms` (tempo) e `size_bytes` (tamanho) |
| Projeto | Fatorial 2×4 com medições repetidas |
| Medições | 200 por tratamento + 20 de aquecimento → **1.600 observações** |
| Estatística | Mann–Whitney U + Cliff's delta (α = 0,05) |

Ambos os paradigmas são servidos pelo **mesmo processo, mesma stack e mesma base
de dados**, isolando o estilo de API como única variável independente.

### Cenários

- **C1** — Recurso único completo (controle)
- **C2** — Recurso único parcial (expõe *over-fetching* do REST)
- **C3** — Consulta aninhada (expõe o problema *N+1* do REST)
- **C4** — Coleção de 50 usuários (controle de volume)

## Estrutura

```
.
├── src/
│   ├── data_gen.py      # gera a base sintética determinística
│   ├── server.py        # Flask: REST + GraphQL sobre a mesma base
│   ├── experiment.py    # executa as medições -> data/results.csv
│   └── analysis.py      # estatística + figuras -> results/
├── data/                # dataset.json e results.csv
├── results/             # stats_summary.csv, descriptive.csv, figures/
├── report/
│   ├── relatorio.tex    # artigo no formato IEEE
│   └── relatorio.pdf    # relatório final compilado
├── dashboard/
│   └── app.py           # dashboard Streamlit interativo
└── requirements.txt
```

## Como reproduzir

### 1. Ambiente

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Pipeline do experimento

```powershell
.\.venv\Scripts\python.exe src\data_gen.py      # 1) gera a base
.\.venv\Scripts\python.exe src\experiment.py    # 2) executa as medições
.\.venv\Scripts\python.exe src\analysis.py      # 3) estatística + figuras
```

### 3. Dashboard

```powershell
.\.venv\Scripts\streamlit.exe run dashboard\app.py
```

### 4. Recompilar o relatório (opcional)

```powershell
cd report
pdflatex relatorio.tex
pdflatex relatorio.tex
```

## Principais resultados

| Cenário | Tempo (REST→GraphQL) | Tamanho (REST→GraphQL) |
|---------|----------------------|------------------------|
| C1 completo | 2,39 → 4,31 ms (REST melhor) | 554 → 574 B (≈ igual) |
| C2 parcial  | 2,26 → 3,76 ms (REST melhor) | 554 → 87 B (**−84%**) |
| C3 aninhada | 16,42 → 5,26 ms (**−68%**)   | 18.380 → 13.238 B (**−28%**) |
| C4 coleção  | 2,64 → 5,96 ms (REST melhor) | 29.943 → 30.062 B (≈ igual) |

**Conclusão:** a vantagem do GraphQL não é absoluta — ela depende do padrão de
acesso aos dados. GraphQL vence claramente quando há *over-fetching* (C2) ou
agregação de recursos relacionados / problema N+1 (C3); REST é mais eficiente
em consultas simples, devido à sobrecarga de *parsing*/validação do schema
GraphQL (medida sem latência de rede).
