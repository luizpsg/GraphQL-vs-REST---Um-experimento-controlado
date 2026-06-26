"""Dashboard interativo - GraphQL vs REST (experimento controlado).

Execucao:
    streamlit run dashboard/app.py

Importa os dados do experimento (data/results.csv), processa com Pandas e
gera visualizacoes interativas (Plotly) para interpretar as diferencas entre
REST e GraphQL nas metricas das RQ1 (tempo) e RQ2 (tamanho).
"""

import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

# ---------------------------------------------------------------------------
# Configuracao da pagina
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="GraphQL vs REST | Experimento Controlado",
    page_icon="dna",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

REST_COLOR = "#E4572E"
GQL_COLOR = "#E10098"
COLOR_MAP = {"REST": REST_COLOR, "GraphQL": GQL_COLOR}

SCEN_NAME = {
    "C1_single_full": "C1 - Recurso unico completo",
    "C2_single_partial": "C2 - Recurso unico parcial",
    "C3_nested_n1": "C3 - Consulta aninhada (N+1)",
    "C4_collection": "C4 - Colecao (50 usuarios)",
}
SCEN_SHORT = {
    "C1_single_full": "C1",
    "C2_single_partial": "C2",
    "C3_nested_n1": "C3",
    "C4_collection": "C4",
}

# ---------------------------------------------------------------------------
# Estilo
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .block-container { padding-top: 2rem; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; }
    .hero {
        background: linear-gradient(120deg, #E10098 0%, #7b2ff7 50%, #E4572E 100%);
        padding: 28px 32px; border-radius: 16px; margin-bottom: 8px;
        color: white;
    }
    .hero h1 { color: white; margin: 0; font-size: 2.1rem; }
    .hero p { color: #f0f0f0; margin: 6px 0 0 0; font-size: 1.05rem; }
    div[data-testid="stMetric"] {
        background: #161a23; border: 1px solid #2a2f3a;
        border-radius: 14px; padding: 16px 18px;
    }
    .winner-rest { color: #E4572E; font-weight: 700; }
    .winner-gql { color: #E10098; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    df = pd.read_csv(os.path.join(DATA_DIR, "results.csv"))
    df["scenario_name"] = df["scenario"].map(SCEN_NAME)
    df["scenario_short"] = df["scenario"].map(SCEN_SHORT)
    return df


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    n, m = len(a), len(b)
    ranks = stats.rankdata(np.concatenate([a, b]))
    u = ranks[:n].sum() - n * (n + 1) / 2.0
    return (2.0 * u) / (n * m) - 1.0


def interpret_delta(d):
    ad = abs(d)
    if ad < 0.147:
        return "negligivel"
    if ad < 0.33:
        return "pequeno"
    if ad < 0.474:
        return "medio"
    return "grande"


def stat_test(df, scenario, metric):
    sub = df[df["scenario"] == scenario]
    rest = sub[sub["api"] == "REST"][metric].values
    gql = sub[sub["api"] == "GraphQL"][metric].values
    _, p = stats.mannwhitneyu(rest, gql, alternative="two-sided")
    delta = cliffs_delta(rest, gql)
    rest_med, gql_med = np.median(rest), np.median(gql)
    reduction = (rest_med - gql_med) / rest_med * 100 if rest_med else 0
    return {
        "rest_med": rest_med, "gql_med": gql_med, "reduction": reduction,
        "p": p, "delta": delta, "effect": interpret_delta(delta),
    }


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------
if not os.path.exists(os.path.join(DATA_DIR, "results.csv")):
    st.error("Arquivo data/results.csv nao encontrado. Rode antes: "
             "`python src/experiment.py`.")
    st.stop()

df = load_data()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <h1>GraphQL vs REST &mdash; Experimento Controlado</h1>
        <p>Tempo de resposta (RQ1) e tamanho de payload (RQ2) sob
        infraestrutura e base de dados identicas &middot; Luiz Paulo Saud,
        Arthur Curi e Helio Teixeira</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.header("Filtros")
scenarios_sel = st.sidebar.multiselect(
    "Cenarios",
    options=list(SCEN_NAME.keys()),
    default=list(SCEN_NAME.keys()),
    format_func=lambda s: SCEN_NAME[s],
)
apis_sel = st.sidebar.multiselect(
    "APIs", options=["REST", "GraphQL"], default=["REST", "GraphQL"],
)
metric_choice = st.sidebar.radio(
    "Metrica em destaque",
    options=["latency_ms", "size_bytes"],
    format_func=lambda m: "Tempo (ms) - RQ1" if m == "latency_ms"
    else "Tamanho (bytes) - RQ2",
)
log_scale = st.sidebar.checkbox("Escala logaritmica", value=True)

st.sidebar.markdown("---")
st.sidebar.caption(
    f"Total de medicoes: **{len(df):,}**  \n"
    f"Iteracoes por tratamento: **{df['iteration'].max()}**  \n"
    f"Cenarios: **{df['scenario'].nunique()}**"
)

if not scenarios_sel or not apis_sel:
    st.warning("Selecione ao menos um cenario e uma API.")
    st.stop()

fdf = df[df["scenario"].isin(scenarios_sel) & df["api"].isin(apis_sel)]

# ---------------------------------------------------------------------------
# KPIs gerais
# ---------------------------------------------------------------------------
st.subheader("Visao geral")
c1, c2, c3, c4 = st.columns(4)

rest_lat = df[df["api"] == "REST"]["latency_ms"].median()
gql_lat = df[df["api"] == "GraphQL"]["latency_ms"].median()
rest_sz = df[df["api"] == "REST"]["size_bytes"].median()
gql_sz = df[df["api"] == "GraphQL"]["size_bytes"].median()

c1.metric("Latencia mediana REST", f"{rest_lat:.2f} ms")
c2.metric("Latencia mediana GraphQL", f"{gql_lat:.2f} ms",
          delta=f"{(rest_lat - gql_lat):.2f} ms vs REST")
c3.metric("Payload mediano REST", f"{rest_sz:,.0f} B")
c4.metric("Payload mediano GraphQL", f"{gql_sz:,.0f} B",
          delta=f"{(rest_sz - gql_sz):,.0f} B vs REST")

# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    ["Comparativo", "Distribuicoes", "Analise estatistica", "Dados brutos"]
)

# ============================ TAB 1 ========================================
with tab1:
    metric_label = ("Tempo de resposta (ms)" if metric_choice == "latency_ms"
                    else "Tamanho do payload (bytes)")
    st.markdown(f"#### {metric_label} por cenario")

    agg = (fdf.groupby(["scenario_short", "api"])[metric_choice]
              .agg(["mean", "median", "std", "count"]).reset_index())
    agg["ci95"] = 1.96 * agg["std"] / np.sqrt(agg["count"])

    fig = go.Figure()
    for api in apis_sel:
        a = agg[agg["api"] == api].sort_values("scenario_short")
        fig.add_trace(go.Bar(
            x=a["scenario_short"], y=a["mean"],
            name=api, marker_color=COLOR_MAP[api],
            error_y=dict(type="data", array=a["ci95"], visible=True),
            hovertemplate=(f"<b>{api}</b><br>%{{x}}<br>media: "
                           "%{y:.2f}<br><extra></extra>"),
        ))
    fig.update_layout(
        barmode="group", template="plotly_dark", height=460,
        yaxis_title=metric_label, xaxis_title="Cenario",
        yaxis_type="log" if log_scale else "linear",
        legend_title="API", margin=dict(t=30),
    )
    st.plotly_chart(fig, use_container_width=True)

    colL, colR = st.columns(2)
    with colL:
        st.markdown("#### RQ1 - Tempo medio (ms)")
        a1 = (fdf.groupby(["scenario_short", "api"])["latency_ms"]
                 .mean().reset_index())
        f1 = px.bar(a1, x="scenario_short", y="latency_ms", color="api",
                    barmode="group", color_discrete_map=COLOR_MAP,
                    template="plotly_dark",
                    labels={"latency_ms": "ms", "scenario_short": "Cenario"})
        f1.update_layout(height=360, yaxis_type="log" if log_scale else "linear",
                         legend_title="API", margin=dict(t=20))
        st.plotly_chart(f1, use_container_width=True)
    with colR:
        st.markdown("#### RQ2 - Tamanho medio (bytes)")
        a2 = (fdf.groupby(["scenario_short", "api"])["size_bytes"]
                 .mean().reset_index())
        f2 = px.bar(a2, x="scenario_short", y="size_bytes", color="api",
                    barmode="group", color_discrete_map=COLOR_MAP,
                    template="plotly_dark",
                    labels={"size_bytes": "bytes", "scenario_short": "Cenario"})
        f2.update_layout(height=360, yaxis_type="log" if log_scale else "linear",
                         legend_title="API", margin=dict(t=20))
        st.plotly_chart(f2, use_container_width=True)

# ============================ TAB 2 ========================================
with tab2:
    st.markdown("#### Distribuicao das medicoes")
    viz = st.radio("Tipo de grafico", ["Boxplot", "Violino", "Histograma"],
                   horizontal=True)
    metric_label = ("Tempo de resposta (ms)" if metric_choice == "latency_ms"
                    else "Tamanho do payload (bytes)")

    if viz == "Boxplot":
        figd = px.box(fdf, x="scenario_short", y=metric_choice, color="api",
                      color_discrete_map=COLOR_MAP, template="plotly_dark",
                      points=False,
                      labels={metric_choice: metric_label,
                              "scenario_short": "Cenario"})
    elif viz == "Violino":
        figd = px.violin(fdf, x="scenario_short", y=metric_choice, color="api",
                         color_discrete_map=COLOR_MAP, template="plotly_dark",
                         box=True, points=False,
                         labels={metric_choice: metric_label,
                                 "scenario_short": "Cenario"})
    else:
        figd = px.histogram(fdf, x=metric_choice, color="api", barmode="overlay",
                            color_discrete_map=COLOR_MAP, template="plotly_dark",
                            opacity=0.65, nbins=60,
                            labels={metric_choice: metric_label})
    figd.update_layout(height=520, legend_title="API",
                       yaxis_type="log" if (log_scale and viz != "Histograma")
                       else "linear")
    st.plotly_chart(figd, use_container_width=True)

    st.markdown("#### Evolucao ao longo das iteracoes (estabilidade)")
    scen_line = st.selectbox("Cenario", options=scenarios_sel,
                             format_func=lambda s: SCEN_NAME[s])
    line_df = fdf[fdf["scenario"] == scen_line]
    figl = px.scatter(line_df, x="iteration", y=metric_choice, color="api",
                      color_discrete_map=COLOR_MAP, template="plotly_dark",
                      opacity=0.5,
                      labels={metric_choice: metric_label,
                              "iteration": "Iteracao"})
    figl.update_layout(height=360, legend_title="API")
    st.plotly_chart(figl, use_container_width=True)

# ============================ TAB 3 ========================================
with tab3:
    st.markdown("#### Testes de hipotese (Mann-Whitney U) e tamanho de efeito")
    st.caption("H0: nao ha diferenca entre REST e GraphQL. "
               "Rejeita-se H0 quando p < 0,05. Reducao positiva = vantagem do "
               "GraphQL.")

    for metric, title in [("latency_ms", "RQ1 - Tempo de resposta"),
                          ("size_bytes", "RQ2 - Tamanho do payload")]:
        st.markdown(f"##### {title}")
        rows = []
        for sc in scenarios_sel:
            r = stat_test(df, sc, metric)
            winner = "GraphQL" if r["reduction"] > 0 else "REST"
            rows.append({
                "Cenario": SCEN_NAME[sc],
                "REST (mediana)": round(r["rest_med"], 2),
                "GraphQL (mediana)": round(r["gql_med"], 2),
                "Reducao GraphQL (%)": round(r["reduction"], 1),
                "p-valor": f"{r['p']:.2e}",
                "Significativo (5%)": "Sim" if r["p"] < 0.05 else "Nao",
                "Tamanho de efeito": r["effect"],
                "Vencedor": winner,
            })
        res_df = pd.DataFrame(rows)

        def _hl(val):
            if val == "GraphQL":
                return "color: #E10098; font-weight: 700;"
            if val == "REST":
                return "color: #E4572E; font-weight: 700;"
            return ""
        st.dataframe(
            res_df.style.map(_hl, subset=["Vencedor"]),
            use_container_width=True, hide_index=True,
        )

    st.markdown("#### Reducao proporcionada pelo GraphQL por cenario")
    red_rows = []
    for metric, label in [("latency_ms", "Tempo"), ("size_bytes", "Tamanho")]:
        for sc in scenarios_sel:
            r = stat_test(df, sc, metric)
            red_rows.append({"Cenario": SCEN_SHORT[sc], "Metrica": label,
                             "Reducao (%)": r["reduction"]})
    red_df = pd.DataFrame(red_rows)
    figr = px.bar(red_df, x="Cenario", y="Reducao (%)", color="Metrica",
                  barmode="group", template="plotly_dark",
                  color_discrete_sequence=["#00b4d8", "#90be6d"],
                  text_auto=".1f")
    figr.add_hline(y=0, line_dash="dash", line_color="white")
    figr.update_layout(height=420,
                       yaxis_title="Reducao do GraphQL vs REST (%)")
    st.plotly_chart(figr, use_container_width=True)
    st.info("Valores acima de 0 indicam que o GraphQL foi melhor; abaixo de 0, "
            "o REST foi melhor naquele cenario/metrica.")

# ============================ TAB 4 ========================================
with tab4:
    st.markdown("#### Dados brutos do experimento")
    st.dataframe(fdf, use_container_width=True, height=480)
    csv = fdf.to_csv(index=False).encode("utf-8")
    st.download_button("Baixar CSV filtrado", data=csv,
                       file_name="results_filtrado.csv", mime="text/csv")

    st.markdown("#### Estatisticas descritivas")
    desc = (fdf.groupby(["scenario_name", "api"])
               .agg(lat_media=("latency_ms", "mean"),
                    lat_mediana=("latency_ms", "median"),
                    lat_p95=("latency_ms", lambda s: np.percentile(s, 95)),
                    tam_media=("size_bytes", "mean"),
                    tam_mediana=("size_bytes", "median"))
               .round(2).reset_index())
    st.dataframe(desc, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Laboratorio de Experimentacao de Software - PUC Minas | "
           "Dados gerados por src/experiment.py")
