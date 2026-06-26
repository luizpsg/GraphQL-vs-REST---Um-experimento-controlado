"""Analise estatistica dos resultados e geracao de figuras.

Para cada cenario e cada variavel dependente (latency_ms, size_bytes):
  1. Estatisticas descritivas (media, mediana, desvio, IQR).
  2. Teste de normalidade (Shapiro-Wilk).
  3. Teste de hipotese comparando REST vs GraphQL:
       - Mann-Whitney U (nao-parametrico, robusto) como teste principal.
       - t de Welch como complemento.
  4. Tamanho de efeito (Cliff's delta e reducao percentual).

Gera figuras (boxplots, barras com IC95%) e tabelas resumo em CSV.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
RESULTS_DIR = os.path.join(ROOT, "results")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")

SCEN_LABELS = {
    "C1_single_full": "C1\nRecurso unico\ncompleto",
    "C2_single_partial": "C2\nRecurso unico\nparcial",
    "C3_nested_n1": "C3\nAninhada\n(N+1)",
    "C4_collection": "C4\nColecao\n(50 usuarios)",
}
PALETTE = {"REST": "#E4572E", "GraphQL": "#E10098"}

sns.set_theme(style="whitegrid", context="talk")


def cliffs_delta(a, b):
    """Cliff's delta entre amostras a e b (a-b). Robusto a outliers."""
    a = np.asarray(a)
    b = np.asarray(b)
    n, m = len(a), len(b)
    # Comparacao por ranks (eficiente).
    all_vals = np.concatenate([a, b])
    ranks = stats.rankdata(all_vals)
    ra = ranks[:n].sum()
    u = ra - n * (n + 1) / 2.0
    delta = (2.0 * u) / (n * m) - 1.0
    return delta


def interpret_delta(d):
    ad = abs(d)
    if ad < 0.147:
        return "negligivel"
    if ad < 0.33:
        return "pequeno"
    if ad < 0.474:
        return "medio"
    return "grande"


def ci95(x):
    x = np.asarray(x)
    m = x.mean()
    se = x.std(ddof=1) / np.sqrt(len(x))
    return m, m - 1.96 * se, m + 1.96 * se


def analyze_metric(df, metric):
    rows = []
    for scenario in SCEN_LABELS:
        sub = df[df["scenario"] == scenario]
        rest = sub[sub["api"] == "REST"][metric].values
        gql = sub[sub["api"] == "GraphQL"][metric].values

        # Normalidade (em amostra de ate 500 p/ Shapiro).
        sw_rest = stats.shapiro(rest[:500]).pvalue
        sw_gql = stats.shapiro(gql[:500]).pvalue

        u_stat, p_mw = stats.mannwhitneyu(rest, gql, alternative="two-sided")
        t_stat, p_t = stats.ttest_ind(rest, gql, equal_var=False)
        delta = cliffs_delta(rest, gql)

        rest_med = np.median(rest)
        gql_med = np.median(gql)
        reduction = (rest_med - gql_med) / rest_med * 100.0

        rows.append({
            "scenario": scenario,
            "metric": metric,
            "rest_mean": rest.mean(),
            "rest_median": rest_med,
            "rest_std": rest.std(ddof=1),
            "gql_mean": gql.mean(),
            "gql_median": gql_med,
            "gql_std": gql.std(ddof=1),
            "shapiro_p_rest": sw_rest,
            "shapiro_p_gql": sw_gql,
            "mannwhitney_U": u_stat,
            "p_value_mw": p_mw,
            "welch_t": t_stat,
            "p_value_welch": p_t,
            "cliffs_delta": delta,
            "effect_size": interpret_delta(delta),
            "graphql_reduction_pct": reduction,
            "significant_5pct": p_mw < 0.05,
        })
    return pd.DataFrame(rows)


def fig_boxplots(df, metric, ylabel, title, fname, logy=False):
    plt.figure(figsize=(13, 7))
    order = list(SCEN_LABELS.keys())
    ax = sns.boxplot(
        data=df, x="scenario", y=metric, hue="api",
        order=order, palette=PALETTE, showfliers=False, width=0.6,
    )
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([SCEN_LABELS[s] for s in order])
    if logy:
        ax.set_yscale("log")
        ylabel += " (escala log)"
    ax.set_xlabel("")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold", pad=15)
    ax.legend(title="API", loc="upper left")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, fname), dpi=160)
    plt.close()


def fig_bars_ci(df, metric, ylabel, title, fname, logy=False):
    order = list(SCEN_LABELS.keys())
    apis = ["REST", "GraphQL"]
    x = np.arange(len(order))
    w = 0.38
    plt.figure(figsize=(13, 7))
    ax = plt.gca()
    for i, api in enumerate(apis):
        means, los, his = [], [], []
        for s in order:
            vals = df[(df["scenario"] == s) & (df["api"] == api)][metric].values
            m, lo, hi = ci95(vals)
            means.append(m)
            los.append(m - lo)
            his.append(hi - m)
        ax.bar(x + (i - 0.5) * w, means, w, label=api, color=PALETTE[api],
               yerr=[los, his], capsize=5, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels([SCEN_LABELS[s] for s in order])
    if logy:
        ax.set_yscale("log")
        ylabel += " (escala log)"
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontweight="bold", pad=15)
    ax.legend(title="API")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, fname), dpi=160)
    plt.close()


def fig_distribution(df, fname):
    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    for ax, scenario in zip(axes.ravel(), SCEN_LABELS):
        sub = df[df["scenario"] == scenario]
        for api in ["REST", "GraphQL"]:
            vals = sub[sub["api"] == api]["latency_ms"].values
            sns.kdeplot(vals, ax=ax, label=api, color=PALETTE[api],
                        fill=True, alpha=0.25, linewidth=2)
        ax.set_title(SCEN_LABELS[scenario].replace("\n", " "), fontsize=13)
        ax.set_xlabel("Latencia (ms)")
        ax.legend()
    fig.suptitle("Distribuicao da latencia por cenario", fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, fname), dpi=160)
    plt.close()


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    df = pd.read_csv(os.path.join(DATA_DIR, "results.csv"))

    lat_stats = analyze_metric(df, "latency_ms")
    size_stats = analyze_metric(df, "size_bytes")
    summary = pd.concat([lat_stats, size_stats], ignore_index=True)
    summary.to_csv(os.path.join(RESULTS_DIR, "stats_summary.csv"), index=False)

    # Tabela descritiva agregada.
    desc = (df.groupby(["scenario", "api"])
              .agg(latency_mean=("latency_ms", "mean"),
                   latency_median=("latency_ms", "median"),
                   latency_p95=("latency_ms", lambda s: np.percentile(s, 95)),
                   size_mean=("size_bytes", "mean"),
                   size_median=("size_bytes", "median"))
              .reset_index())
    desc.to_csv(os.path.join(RESULTS_DIR, "descriptive.csv"), index=False)

    # Figuras.
    fig_boxplots(df, "latency_ms", "Latencia (ms)",
                 "RQ1 - Tempo de resposta: REST vs GraphQL",
                 "fig_latency_box.png", logy=True)
    fig_bars_ci(df, "latency_ms", "Latencia media (ms)",
                "RQ1 - Latencia media com IC95%",
                "fig_latency_bars.png", logy=True)
    fig_boxplots(df, "size_bytes", "Tamanho (bytes)",
                 "RQ2 - Tamanho da resposta: REST vs GraphQL",
                 "fig_size_box.png", logy=True)
    fig_bars_ci(df, "size_bytes", "Tamanho medio (bytes)",
                "RQ2 - Tamanho medio com IC95%",
                "fig_size_bars.png", logy=True)
    fig_distribution(df, "fig_latency_dist.png")

    print("Analise concluida.")
    print("Resumo estatistico:")
    cols = ["scenario", "metric", "rest_median", "gql_median",
            "graphql_reduction_pct", "p_value_mw", "effect_size"]
    with pd.option_context("display.width", 200, "display.max_columns", None):
        print(summary[cols].to_string(index=False))


if __name__ == "__main__":
    main()
