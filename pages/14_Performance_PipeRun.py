from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.bootstrap import iniciar_app
from utils.data_loader import carregar_dados_planilha
from utils.piperun_client import PiperunClient, date_params, get_piperun_base_url, get_piperun_token
from utils.piperun_metrics import build_performance, build_reference_maps, normalize_text


st.set_page_config(page_title="Performance PipeRun", page_icon="PR", layout="wide")
iniciar_app()


DEAL_ENDPOINTS = ["deals", "opportunities", "cards", "leads"]
ACTION_ENDPOINTS = ["activities", "notes", "tasks", "visits", "events", "actions"]
USER_ENDPOINTS = ["users", "account/users", "user"]
STAGE_ENDPOINTS = ["stages", "pipeline-stages", "pipeline_stages", "pipelines/stages"]
PIPELINE_ENDPOINTS = ["pipelines", "pipeline", "funnels"]
ACTIVITY_TYPE_ENDPOINTS = ["activityTypes", "activity-types", "activity_types", "activities/types"]

STAGE_COLS = [
    "novo_lead",
    "aguardando_atendimento",
    "em_atendimento",
    "cadencia",
    "recuperacao_lead",
    "acompanhamento",
    "visita_agendada",
    "visita_realizada",
    "aguardando_documentos",
    "recusa_pasteiro",
    "analises_enviadas",
    "conferencia_pasteiro",
    "pendencias",
    "condicionados",
    "restricoes",
    "aprovacoes",
    "reprovados",
]

BASE_COLS = {
    "leads_recebidos",
    "cards_total",
    "leads_remanejados",
    "acoes_total",
    "leads_com_atividade",
    "analise_enviada_atividade",
    *STAGE_COLS,
}


def to_int(value) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def pretty_label(value: str) -> str:
    labels = {
        "cards_total": "Cards no funil",
        "leads_recebidos": "Leads recebidos",
        "acoes_total": "Registros de atividade",
        "leads_com_atividade": "Leads com atividade",
        "analise_enviada_atividade": "Analise enviada por atividade",
        "1_analise": "1 analise",
        "1_analise_enviada": "1 analise enviada",
        "1_analise_confirmada": "1 analise confirmada",
        "analise_credito_confirmada": "Analise credito confirmada",
        "leads_remanejados": "Leads remanejados",
        "analises_enviadas": "Analises enviadas",
        "pendencias": "Pendencias",
        "aprovacoes": "Aprovacoes",
        "reprovados": "Reprovados",
        "em_atendimento": "Em atendimento",
        "cadencia": "Cadencia",
        "acompanhamento": "Acompanhamento",
        "visita_agendada": "Visitas agendadas",
        "visita_realizada": "Visitas realizadas",
        "aguardando_documentos": "Aguardando documentos",
        "recusa_pasteiro": "Recusa Pasteiro",
        "conferencia_pasteiro": "Conferencia Pasteiro",
        "condicionados": "Condicionados",
        "restricoes": "Restricoes",
        "novo_lead": "Novo lead",
        "aguardando_atendimento": "Aguardando atendimento",
        "recuperacao_lead": "Recuperacao de lead",
    }
    return labels.get(value, value.replace("_", " ").title())


def sum_row(df: pd.DataFrame, metric_cols: list[str]) -> dict:
    if df.empty:
        return {col: 0 for col in metric_cols}
    return {col: int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum()) for col in metric_cols}


def show_metric_grid(metrics: dict, items: list[tuple[str, str]], per_row: int = 4):
    if not items:
        return
    cols = st.columns(per_row)
    for idx, (label, key) in enumerate(items):
        cols[idx % per_row].metric(label, to_int(metrics.get(key, 0)))


def show_entity_cards(df: pd.DataFrame, title_col: str, metric_col: str, limit: int = 12):
    if df.empty or metric_col not in df.columns:
        st.info("Sem dados para exibir.")
        return

    view = df.copy()
    view[metric_col] = pd.to_numeric(view[metric_col], errors="coerce").fillna(0).astype(int)
    view = view.sort_values(metric_col, ascending=False).head(limit)

    for start in range(0, len(view), 4):
        cols = st.columns(4)
        for idx, (_, row) in enumerate(view.iloc[start : start + 4].iterrows()):
            label = str(row.get(title_col, "Sem nome"))
            subtitle = str(row.get("equipe", "")) if title_col != "equipe" else ""
            with cols[idx]:
                st.metric(label, to_int(row.get(metric_col, 0)))
                if subtitle:
                    st.caption(subtitle)


@st.cache_data(ttl=300, show_spinner=False)
def carregar_referencias_corretores() -> tuple[dict, dict]:
    try:
        df = carregar_dados_planilha()
    except Exception:
        return {}, {}

    if df is None or df.empty:
        return {}, {}

    df = df.copy()
    df.columns = df.columns.str.upper().str.strip()

    if "CORRETOR" not in df.columns or "EQUIPE" not in df.columns:
        return {}, {}

    base = df[["CORRETOR", "EQUIPE"]].dropna().copy()
    base["CORRETOR_KEY"] = base["CORRETOR"].apply(normalize_text)
    base["EQUIPE_VAL"] = base["EQUIPE"].apply(normalize_text)
    base = base[(base["CORRETOR_KEY"] != "") & (base["EQUIPE_VAL"] != "")]

    if base.empty:
        return {}, {}

    equipe_map = base.groupby("CORRETOR_KEY")["EQUIPE_VAL"].agg(lambda s: s.value_counts().index[0]).to_dict()
    nome_map = {nome: nome for nome in base["CORRETOR_KEY"].unique()}

    primeiro_nome = base["CORRETOR_KEY"].str.split().str[0]
    nomes_unicos = primeiro_nome.value_counts()
    for nome in base["CORRETOR_KEY"].unique():
        primeiro = nome.split()[0]
        if nomes_unicos.get(primeiro, 0) == 1:
            nome_map[primeiro] = nome

    return equipe_map, nome_map


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

    deals_result = client.fetch_first_available(DEAL_ENDPOINTS, params=params, max_pages=max_pages, per_page=per_page)

    action_frames = []
    action_status = []
    for endpoint in ACTION_ENDPOINTS:
        result = client.fetch_first_available([endpoint], params=params, max_pages=max_pages, per_page=per_page)
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

    return {
        "deals_result": deals_result,
        "actions_df": pd.concat(action_frames, ignore_index=True) if action_frames else pd.DataFrame(),
        "action_status": pd.DataFrame(action_status),
        "users_result": client.fetch_first_available(USER_ENDPOINTS, params={}, max_pages=5, per_page=per_page),
        "stages_result": client.fetch_first_available(STAGE_ENDPOINTS, params={}, max_pages=10, per_page=per_page),
        "pipelines_result": client.fetch_first_available(PIPELINE_ENDPOINTS, params={}, max_pages=5, per_page=per_page),
        "activity_types_result": client.fetch_first_available(ACTIVITY_TYPE_ENDPOINTS, params={}, max_pages=5, per_page=per_page),
    }


st.title("Performance PipeRun")
st.caption("Painel por periodo, corretor, atividades e etapas do funil.")

perfil = st.session_state.get("perfil", "")
nome_usuario = st.session_state.get("nome_usuario", "").upper().strip()
token_secrets = get_piperun_token()

st.sidebar.title("Filtros")
hoje = date.today()
atalho = st.sidebar.selectbox(
    "Periodo rapido",
    ["Ultimos 7 dias", "Hoje", "Ultimos 30 dias", "Este mes", "Personalizado"],
)

if atalho == "Hoje":
    default_ini = hoje
elif atalho == "Ultimos 7 dias":
    default_ini = hoje - timedelta(days=7)
elif atalho == "Este mes":
    default_ini = hoje.replace(day=1)
else:
    default_ini = hoje - timedelta(days=30)

data_ini = st.sidebar.date_input("Data inicial", value=default_ini, format="DD/MM/YYYY")
data_fim = st.sidebar.date_input("Data final", value=hoje, format="DD/MM/YYYY")

if data_ini > data_fim:
    st.error("A data inicial nao pode ser maior que a data final.")
    st.stop()

base_url = get_piperun_base_url()
token = (token_secrets or "").strip()

usar_filtro_api = st.sidebar.checkbox(
    "Enviar filtro de data para API",
    value=False,
    help="Deixe desligado se a API rejeitar parametros de data. A pagina filtra localmente quando encontra campos de data.",
)
max_pages = st.sidebar.number_input("Paginas maximas por endpoint", min_value=1, max_value=100, value=30, step=1)
per_page = st.sidebar.number_input("Registros por pagina", min_value=20, max_value=500, value=500, step=20)
remanejo_dias = st.sidebar.number_input("Regra de remanejo: dias sem acao", min_value=1, max_value=30, value=2, step=1)

if not token:
    st.warning("Configure o token do PipeRun em Secrets ou informe temporariamente na barra lateral.")
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
users_result = carga["users_result"]
stages_result = carga["stages_result"]
pipelines_result = carga["pipelines_result"]
activity_types_result = carga["activity_types_result"]
corretor_equipe_map, corretor_nome_map = carregar_referencias_corretores()

if not deals_result.ok:
    st.error("Nao consegui carregar leads/cards/oportunidades do PipeRun.")
    st.write(deals_result.error)
    st.stop()

reference_maps = build_reference_maps(
    users_raw=users_result.data if users_result.ok else pd.DataFrame(),
    stages_raw=stages_result.data if stages_result.ok else pd.DataFrame(),
    pipelines_raw=pipelines_result.data if pipelines_result.ok else pd.DataFrame(),
    activity_types_raw=activity_types_result.data if activity_types_result.ok else pd.DataFrame(),
    corretor_equipe_map=corretor_equipe_map,
    corretor_nome_map=corretor_nome_map,
)

metricas = build_performance(
    deals_raw=deals_result.data,
    actions_raw=actions_df,
    data_ini=data_ini,
    data_fim=data_fim,
    remanejo_dias=int(remanejo_dias),
    reference_maps=reference_maps,
)

df_corretor = metricas["corretor"]
df_equipe = metricas["equipe"]

if perfil == "corretor" and nome_usuario and "responsavel" in df_corretor.columns:
    df_corretor = df_corretor[df_corretor["responsavel"] == nome_usuario].copy()
    df_equipe = df_equipe[df_equipe["equipe"].isin(df_corretor["equipe"].unique().tolist())].copy()

metric_cols = [c for c in df_corretor.columns if c not in ["equipe", "responsavel"]]
activity_cols = sorted([c for c in metric_cols if c not in BASE_COLS])
stage_cols_available = [c for c in STAGE_COLS if c in df_corretor.columns]

corretores = sorted(df_corretor["responsavel"].dropna().unique().tolist()) if not df_corretor.empty else []
col1, col2, col3 = st.columns([1.2, 1.2, 2])
with col1:
    corretor_sel = st.selectbox("Ver corretor", ["Toda imobiliaria"] + corretores)
with col2:
    menu = st.selectbox("Menu", ["Resumo", "Atividades", "Funil", "Corretores"])
with col3:
    st.caption(
        f"Periodo: {data_ini.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')} | "
        f"Leads: {len(deals_result.data)} | Atividades: {len(actions_df)}"
    )

df_view = df_corretor.copy()
if corretor_sel != "Toda imobiliaria":
    df_view = df_view[df_view["responsavel"] == corretor_sel].copy()

resumo = sum_row(df_view, metric_cols)
st.subheader("Toda imobiliaria" if corretor_sel == "Toda imobiliaria" else corretor_sel)

show_metric_grid(
    resumo,
    [
        ("Cards no funil", "cards_total"),
        ("Leads recebidos", "leads_recebidos"),
        ("Analises enviadas", "analises_enviadas"),
        ("Pendencias", "pendencias"),
    ],
)
show_metric_grid(
    resumo,
    [
        ("Aprovacoes", "aprovacoes"),
        ("Reprovados", "reprovados"),
        ("Leads com atividade", "leads_com_atividade"),
        ("Registros de atividade", "acoes_total"),
    ],
)

st.markdown("---")

if menu == "Resumo":
    st.subheader("Indicadores principais")
    show_metric_grid(
        resumo,
        [
            ("Leads remanejados", "leads_remanejados"),
            ("Analise por atividade", "analise_enviada_atividade"),
            ("Visitas agendadas", "visita_agendada"),
            ("Visitas realizadas", "visita_realizada"),
            ("Aguardando documentos", "aguardando_documentos"),
            ("Condicionados", "condicionados"),
            ("Restricoes", "restricoes"),
            ("Recusa Pasteiro", "recusa_pasteiro"),
        ],
    )

    st.subheader("Equipes")
    show_entity_cards(df_equipe, "equipe", "cards_total", limit=12)

elif menu == "Atividades":
    st.subheader("Leads unicos por atividade")
    if activity_cols:
        atividade_sel = st.selectbox(
            "Escolha a atividade",
            activity_cols,
            format_func=pretty_label,
        )
        show_metric_grid(
            resumo,
            [
                (pretty_label(atividade_sel), atividade_sel),
                ("Leads com atividade", "leads_com_atividade"),
                ("Registros de atividade", "acoes_total"),
                ("Analise por atividade", "analise_enviada_atividade"),
            ],
        )

        st.subheader(f"Corretores em {pretty_label(atividade_sel)}")
        show_entity_cards(df_view, "responsavel", atividade_sel, limit=16)
    else:
        st.info("Nenhuma atividade detalhada foi identificada no retorno da API.")

elif menu == "Funil":
    st.subheader("Itens do funil")
    if stage_cols_available:
        item_funil = st.selectbox(
            "Escolha o item do funil",
            stage_cols_available,
            format_func=pretty_label,
        )
        show_metric_grid(
            resumo,
            [
                (pretty_label(item_funil), item_funil),
                ("Cards no funil", "cards_total"),
                ("Leads recebidos", "leads_recebidos"),
                ("Analises enviadas", "analises_enviadas"),
            ],
        )

        st.subheader(f"Corretores em {pretty_label(item_funil)}")
        show_entity_cards(df_view, "responsavel", item_funil, limit=16)

        st.subheader(f"Equipes em {pretty_label(item_funil)}")
        show_entity_cards(df_equipe, "equipe", item_funil, limit=12)
    else:
        st.info("Sem etapas do funil para exibir.")

elif menu == "Corretores":
    st.subheader("Ranking por corretor")
    col_rank_1, col_rank_2 = st.columns(2)
    with col_rank_1:
        ranking_metric = st.selectbox(
            "Escolha o indicador do ranking",
            ["cards_total", "leads_recebidos", "analises_enviadas", "acoes_total", "leads_com_atividade"]
            + stage_cols_available
            + activity_cols,
            format_func=pretty_label,
        )
    with col_rank_2:
        corretor_ranking = st.selectbox(
            "Escolha o corretor",
            ["Todos os corretores"] + corretores,
        )

    ranking_view = df_corretor.copy()
    if corretor_ranking != "Todos os corretores":
        ranking_view = ranking_view[ranking_view["responsavel"] == corretor_ranking].copy()

    show_entity_cards(ranking_view, "responsavel", ranking_metric, limit=24)
