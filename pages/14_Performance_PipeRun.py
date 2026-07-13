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

STAGE_COLS = {
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
}

BASE_COLS = {
    "leads_recebidos",
    "cards_total",
    "leads_remanejados",
    "acoes_total",
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
        "acoes_total": "Ações realizadas",
        "leads_remanejados": "Leads remanejados",
        "analises_enviadas": "Análises enviadas",
        "pendencias": "Pendências",
        "aprovacoes": "Aprovações",
        "reprovados": "Reprovados",
        "em_atendimento": "Em atendimento",
        "cadencia": "Cadência",
        "acompanhamento": "Acompanhamento",
        "visita_agendada": "Visitas agendadas",
        "visita_realizada": "Visitas realizadas",
        "aguardando_documentos": "Aguardando docs.",
        "recusa_pasteiro": "Recusa Pasteiro",
        "conferencia_pasteiro": "Conferência Pasteiro",
        "condicionados": "Condicionados",
        "restricoes": "Restrições",
        "novo_lead": "Novo lead",
        "aguardando_atendimento": "Aguardando atendimento",
        "recuperacao_lead": "Recuperação de lead",
    }
    return labels.get(value, value.replace("_", " ").title())


def sum_row(df: pd.DataFrame, metric_cols: list[str]) -> dict:
    if df.empty:
        return {col: 0 for col in metric_cols}
    return {col: int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum()) for col in metric_cols}


def show_metric_grid(metrics: dict, items: list[tuple[str, str]], per_row: int = 5):
    cols = st.columns(per_row)
    for idx, (label, key) in enumerate(items):
        cols[idx % per_row].metric(label, to_int(metrics.get(key, 0)))


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
st.caption("Resumo da imobiliária, desempenho por corretor, leads no funil e todas as atividades registradas no CRM.")

perfil = st.session_state.get("perfil", "")
nome_usuario = st.session_state.get("nome_usuario", "").upper().strip()
token_secrets = get_piperun_token()

st.sidebar.title("Filtros")
hoje = date.today()
atalho = st.sidebar.selectbox("Período rápido", ["Últimos 30 dias", "Hoje", "Últimos 7 dias", "Este mês", "Personalizado"])

if atalho == "Hoje":
    default_ini = hoje
elif atalho == "Últimos 7 dias":
    default_ini = hoje - timedelta(days=7)
elif atalho == "Este mês":
    default_ini = hoje.replace(day=1)
else:
    default_ini = hoje - timedelta(days=30)

data_ini = st.sidebar.date_input("Data inicial", value=default_ini, format="DD/MM/YYYY")
data_fim = st.sidebar.date_input("Data final", value=hoje, format="DD/MM/YYYY")

if data_ini > data_fim:
    st.error("A data inicial nao pode ser maior que a data final.")
    st.stop()

base_url = st.sidebar.text_input("Base da API", value=get_piperun_base_url())
token_digitado = st.sidebar.text_input("Token PipeRun temporario", value="", type="password")
token = (token_digitado or token_secrets or "").strip()

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
action_status = carga["action_status"]
users_result = carga["users_result"]
stages_result = carga["stages_result"]
pipelines_result = carga["pipelines_result"]
activity_types_result = carga["activity_types_result"]
corretor_equipe_map, corretor_nome_map = carregar_referencias_corretores()

if not deals_result.ok:
    st.error("Nao consegui carregar leads/cards/oportunidades do PipeRun.")
    st.write(deals_result.error)
    st.dataframe(action_status, use_container_width=True, hide_index=True)
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
df_cards_coluna = metricas.get("cards_por_coluna", pd.DataFrame())
deals_norm = metricas.get("deals_normalizados", pd.DataFrame())
acoes_norm = metricas.get("acoes_normalizadas", pd.DataFrame())

if perfil == "corretor" and nome_usuario and "responsavel" in df_corretor.columns:
    df_corretor = df_corretor[df_corretor["responsavel"] == nome_usuario].copy()
    df_equipe = df_equipe[df_equipe["equipe"].isin(df_corretor["equipe"].unique().tolist())].copy()

metric_cols = [c for c in df_corretor.columns if c not in ["equipe", "responsavel"]]
activity_cols = [c for c in metric_cols if c not in BASE_COLS]

corretores = sorted(df_corretor["responsavel"].dropna().unique().tolist()) if not df_corretor.empty else []
col_filtro_1, col_filtro_2 = st.columns([1, 2])
with col_filtro_1:
    corretor_sel = st.selectbox("Ver corretor", ["Toda imobiliária"] + corretores)
with col_filtro_2:
    st.caption(
        f"Periodo: {data_ini.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')} | "
        f"Leads carregados: {len(deals_result.data)} | Atividades carregadas: {len(actions_df)}"
    )

df_view = df_corretor.copy()
if corretor_sel != "Toda imobiliária":
    df_view = df_view[df_view["responsavel"] == corretor_sel].copy()

resumo = sum_row(df_view, metric_cols)
titulo_resumo = "Resumo geral da imobiliária" if corretor_sel == "Toda imobiliária" else f"Resumo de {corretor_sel}"
st.subheader(titulo_resumo)

show_metric_grid(
    resumo,
    [
        ("Cards no funil", "cards_total"),
        ("Leads recebidos", "leads_recebidos"),
        ("Ações realizadas", "acoes_total"),
        ("Análises enviadas", "analises_enviadas"),
        ("Pendências", "pendencias"),
    ],
)
show_metric_grid(
    resumo,
    [
        ("Aprovações", "aprovacoes"),
        ("Reprovados", "reprovados"),
        ("Em atendimento", "em_atendimento"),
        ("Cadência", "cadencia"),
        ("Acompanhamento", "acompanhamento"),
    ],
)

st.markdown("---")

tab_resumo, tab_atividades, tab_funil, tab_corretores, tab_diagnostico = st.tabs(
    ["Resumo", "Atividades", "Funil", "Corretores", "Diagnóstico"]
)

with tab_resumo:
    st.subheader("Indicadores do período")
    principais = [
        "cards_total",
        "leads_recebidos",
        "leads_remanejados",
        "acoes_total",
        "analises_enviadas",
        "pendencias",
        "aprovacoes",
        "reprovados",
        "visita_agendada",
        "visita_realizada",
        "aguardando_documentos",
        "condicionados",
        "restricoes",
    ]
    resumo_tabela = pd.DataFrame(
        [{"indicador": pretty_label(col), "quantidade": to_int(resumo.get(col, 0))} for col in principais]
    )
    st.dataframe(resumo_tabela, use_container_width=True, hide_index=True)

    st.subheader("Por equipe")
    st.dataframe(df_equipe, use_container_width=True, hide_index=True)

with tab_atividades:
    st.subheader("Todas as atividades registradas")
    if activity_cols:
        atividade_tabela = pd.DataFrame(
            [{"atividade": pretty_label(col), "quantidade": to_int(resumo.get(col, 0))} for col in activity_cols]
        ).sort_values("quantidade", ascending=False)
        st.dataframe(atividade_tabela, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma atividade detalhada foi identificada no retorno da API.")

    st.subheader("Atividades por corretor")
    cols_show = ["equipe", "responsavel", "acoes_total"] + activity_cols
    cols_show = [col for col in cols_show if col in df_corretor.columns]
    st.dataframe(df_corretor[cols_show], use_container_width=True, hide_index=True)

with tab_funil:
    st.subheader("Cards por etapa do funil")
    if df_cards_coluna.empty:
        st.info("Sem cards por coluna para exibir.")
    else:
        st.dataframe(df_cards_coluna, use_container_width=True, hide_index=True)

    st.subheader("Etapas por corretor")
    stage_show = ["equipe", "responsavel", "cards_total"] + [col for col in STAGE_COLS if col in df_corretor.columns]
    st.dataframe(df_view[stage_show], use_container_width=True, hide_index=True)

with tab_corretores:
    st.subheader("Ranking de corretores")
    ranking = df_corretor.sort_values(["cards_total", "acoes_total", "leads_recebidos"], ascending=False)
    st.dataframe(ranking, use_container_width=True, hide_index=True)

with tab_diagnostico:
    st.subheader("Diagnóstico da integração")
    st.write(
        {
            "endpoint_leads": deals_result.endpoint,
            "leads_carregados": len(deals_result.data),
            "acoes_carregadas": len(actions_df),
            "usuarios": len(users_result.data) if users_result.ok else 0,
            "etapas": len(stages_result.data) if stages_result.ok else 0,
            "pipelines": len(pipelines_result.data) if pipelines_result.ok else 0,
            "tipos_atividade": len(activity_types_result.data) if activity_types_result.ok else 0,
        }
    )
    st.markdown("**Endpoints de ações**")
    st.dataframe(action_status, use_container_width=True, hide_index=True)

    with st.expander("Responsáveis encontrados"):
        if deals_norm.empty:
            st.info("Sem responsáveis normalizados para exibir.")
        else:
            responsaveis = (
                deals_norm.groupby(["equipe", "responsavel"], as_index=False)["lead_id"]
                .nunique()
                .rename(columns={"lead_id": "cards"})
                .sort_values("cards", ascending=False)
            )
            st.dataframe(responsaveis, use_container_width=True, hide_index=True)

    with st.expander("Amostra de leads/cards"):
        st.dataframe(deals_result.data.head(30), use_container_width=True)

    with st.expander("Amostra de atividades"):
        st.dataframe(actions_df.head(30), use_container_width=True)

    with st.expander("Atividades normalizadas"):
        st.dataframe(acoes_norm.head(50), use_container_width=True)
