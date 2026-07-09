from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.bootstrap import iniciar_app
from utils.piperun_client import PiperunClient, date_params, get_piperun_base_url, get_piperun_token
from utils.piperun_metrics import build_performance


st.set_page_config(
    page_title="Performance PipeRun",
    page_icon="PR",
    layout="wide",
)

iniciar_app()


DEAL_ENDPOINTS = [
    "deals",
    "opportunities",
    "cards",
    "leads",
]

ACTION_ENDPOINTS = [
    "activities",
    "notes",
    "tasks",
    "visits",
    "events",
    "actions",
]


def to_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0


@st.cache_data(ttl=300, show_spinner=False)
def carregar_piperun(
    token: str,
    base_url: str,
    data_ini: date,
    data_fim: date,
    usar_filtro_api: bool,
    max_pages: int,
    per_page: int,
):
    client = PiperunClient(token=token, base_url=base_url)
    params = date_params(data_ini, data_fim) if usar_filtro_api else {}

    deals_result = client.fetch_first_available(
        DEAL_ENDPOINTS,
        params=params,
        max_pages=max_pages,
        per_page=per_page,
    )

    action_frames = []
    action_status = []

    for endpoint in ACTION_ENDPOINTS:
        result = client.fetch_first_available(
            [endpoint],
            params=params,
            max_pages=max_pages,
            per_page=per_page,
        )
        action_status.append(
            {
                "endpoint": endpoint,
                "ok": result.ok,
                "linhas": len(result.data) if result.ok else 0,
                "erro": result.error,
            }
        )
        if result.ok and not result.data.empty:
            tmp = result.data.copy()
            tmp["_endpoint_origem"] = endpoint
            action_frames.append(tmp)

    actions_df = pd.concat(action_frames, ignore_index=True) if action_frames else pd.DataFrame()

    return {
        "deals_result": deals_result,
        "actions_df": actions_df,
        "action_status": pd.DataFrame(action_status),
    }


st.title("Performance PipeRun")
st.caption("Leads, remanejamentos, acoes e etapas do funil por visao geral, equipe e corretor.")

perfil = st.session_state.get("perfil", "")
nome_usuario = st.session_state.get("nome_usuario", "").upper().strip()

token_secrets = get_piperun_token()

st.sidebar.title("Filtros")

hoje = date.today()
data_ini = st.sidebar.date_input("Data inicial", value=hoje - timedelta(days=30), format="DD/MM/YYYY")
data_fim = st.sidebar.date_input("Data final", value=hoje, format="DD/MM/YYYY")

if data_ini > data_fim:
    st.error("A data inicial nao pode ser maior que a data final.")
    st.stop()

base_url = st.sidebar.text_input("Base da API", value=get_piperun_base_url())
token_digitado = st.sidebar.text_input(
    "Token PipeRun temporario",
    value="",
    type="password",
    help="Opcional. Use apenas para teste. O ideal e configurar PIPERUN_TOKEN em secrets ou variavel de ambiente.",
)

token = (token_digitado or token_secrets or "").strip()

with st.sidebar.expander("Configuracao segura do token"):
    st.code(
        '[secrets]\nPIPERUN_TOKEN = "cole_o_token_aqui"\nPIPERUN_API_BASE = "https://api.pipe.run/v1"',
        language="toml",
    )
    st.caption("Nao salve o token direto nos arquivos .py do projeto.")

usar_filtro_api = st.sidebar.checkbox(
    "Enviar filtro de data para API",
    value=False,
    help="Deixe desligado se a API rejeitar parametros de data. A pagina filtra localmente quando encontra campos de data.",
)

max_pages = st.sidebar.number_input("Paginas maximas por endpoint", min_value=1, max_value=50, value=5, step=1)
per_page = st.sidebar.number_input("Registros por pagina", min_value=20, max_value=500, value=100, step=20)
remanejo_dias = st.sidebar.number_input("Regra de remanejo: dias sem acao", min_value=1, max_value=30, value=2, step=1)

if not token:
    st.warning("Configure o token do PipeRun em st.secrets, variavel PIPERUN_TOKEN ou informe temporariamente na barra lateral.")
    st.stop()

with st.spinner("Consultando PipeRun..."):
    carga = carregar_piperun(
        token=token,
        base_url=base_url,
        data_ini=data_ini,
        data_fim=data_fim,
        usar_filtro_api=usar_filtro_api,
        max_pages=int(max_pages),
        per_page=int(per_page),
    )

deals_result = carga["deals_result"]
actions_df = carga["actions_df"]
action_status = carga["action_status"]

if not deals_result.ok:
    st.error("Nao consegui carregar leads/cards/oportunidades do PipeRun.")
    st.write(deals_result.error)
    with st.expander("Diagnostico de endpoints de acoes"):
        st.dataframe(action_status, use_container_width=True, hide_index=True)
    st.stop()

metricas = build_performance(
    deals_raw=deals_result.data,
    actions_raw=actions_df,
    data_ini=data_ini,
    data_fim=data_fim,
    remanejo_dias=int(remanejo_dias),
)

df_geral = metricas["geral"]
df_equipe = metricas["equipe"]
df_corretor = metricas["corretor"]

if perfil == "corretor" and nome_usuario and "responsavel" in df_corretor.columns:
    df_corretor = df_corretor[df_corretor["responsavel"] == nome_usuario].copy()
    equipes_visiveis = df_corretor["equipe"].unique().tolist()
    df_equipe = df_equipe[df_equipe["equipe"].isin(equipes_visiveis)].copy()
    numeric_cols = [c for c in df_corretor.columns if c not in ["equipe", "responsavel"]]
    df_geral = pd.DataFrame([{**{"visao": "GERAL"}, **{c: int(df_corretor[c].sum()) for c in numeric_cols}}])

st.caption(
    f"Periodo: {data_ini.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')} | "
    f"Endpoint principal: {deals_result.endpoint} | "
    f"Leads carregados: {len(deals_result.data)} | Acoes carregadas: {len(actions_df)}"
)

metric_cols = [c for c in df_geral.columns if c != "visao"]
geral_row = df_geral.iloc[0].to_dict() if not df_geral.empty else {}

cards_principais = [
    ("Leads recebidos", "leads_recebidos"),
    ("Leads remanejados", "leads_remanejados"),
    ("Acoes totais", "acoes_total"),
    ("Analises enviadas", "analises_enviadas"),
    ("Aprovacoes", "aprovacoes"),
    ("Reprovados", "reprovados"),
]

cols = st.columns(6)
for idx, (label, key) in enumerate(cards_principais):
    cols[idx].metric(label, to_int(geral_row.get(key, 0)))

st.markdown("---")

acao_cols = [
    c
    for c in metric_cols
    if c
    not in {
        "leads_recebidos",
        "leads_remanejados",
        "acoes_total",
        "analises_enviadas",
        "aprovacoes",
        "reprovados",
    }
]

if acao_cols:
    st.subheader("Acoes registradas pelo CRM")
    cols = st.columns(min(6, max(1, len(acao_cols))))
    for i, col in enumerate(acao_cols):
        cols[i % len(cols)].metric(col.replace("_", " ").title(), to_int(geral_row.get(col, 0)))

st.markdown("---")

visao = st.radio("Visao", ["Geral", "Por equipe", "Por corretor", "Diagnostico"], horizontal=True)

if visao == "Geral":
    st.subheader("Resumo geral")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

elif visao == "Por equipe":
    st.subheader("Performance por equipe")
    if df_equipe.empty:
        st.info("Sem equipes identificadas no retorno da API.")
    else:
        st.dataframe(df_equipe, use_container_width=True, hide_index=True)

elif visao == "Por corretor":
    st.subheader("Performance por corretor")
    if df_corretor.empty:
        st.info("Sem corretores identificados no retorno da API.")
    else:
        equipe_sel = st.selectbox("Filtrar equipe", ["Todas"] + sorted(df_corretor["equipe"].dropna().unique().tolist()))
        df_view = df_corretor.copy()
        if equipe_sel != "Todas":
            df_view = df_view[df_view["equipe"] == equipe_sel]
        st.dataframe(df_view, use_container_width=True, hide_index=True)

else:
    st.subheader("Diagnostico da integracao")
    st.write("Use esta aba na primeira conexao para confirmar quais endpoints e campos o PipeRun esta entregando.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Endpoint de leads/cards**")
        st.write(
            {
                "endpoint": deals_result.endpoint,
                "ok": deals_result.ok,
                "linhas": len(deals_result.data),
                "status_code": deals_result.status_code,
            }
        )
        st.markdown("**Colunas de leads/cards**")
        st.dataframe(pd.DataFrame({"coluna": list(deals_result.data.columns)}), use_container_width=True, hide_index=True)

    with c2:
        st.markdown("**Endpoints de acoes**")
        st.dataframe(action_status, use_container_width=True, hide_index=True)
        st.markdown("**Colunas de acoes**")
        st.dataframe(pd.DataFrame({"coluna": list(actions_df.columns)}), use_container_width=True, hide_index=True)

    with st.expander("Amostra de leads/cards"):
        st.dataframe(deals_result.data.head(20), use_container_width=True)

    with st.expander("Amostra de acoes"):
        st.dataframe(actions_df.head(20), use_container_width=True)
