import re
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from utils.bootstrap import iniciar_app
from utils.data_loader import carregar_dados_planilha
from utils.piperun_client import PiperunClient, date_params, get_piperun_base_url, get_piperun_token
from utils.piperun_metrics import build_performance, build_reference_maps, normalize_id, normalize_text


st.set_page_config(page_title="Performance PipeRun", page_icon="PR", layout="wide")
iniciar_app()


DEAL_ENDPOINTS = ["deals", "opportunities", "cards", "leads"]
ACTION_ENDPOINTS = ["activities", "notes", "histories", "history", "timeline", "timelines", "tasks", "visits", "events", "actions"]
USER_ENDPOINTS = ["users", "account/users", "user"]
STAGE_ENDPOINTS = ["stages", "pipeline-stages", "pipeline_stages", "pipelines/stages"]
PIPELINE_ENDPOINTS = ["pipelines", "pipeline", "funnels"]
ACTIVITY_TYPE_ENDPOINTS = ["activityTypes", "activity-types", "activity_types", "activities/types"]
PERSON_ENDPOINTS = ["persons", "people", "contacts", "customers", "clients"]

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
        "lead_remanejado": "Lead remanejado",
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


def is_generic_client_name(value) -> bool:
    text = normalize_text(value)
    return text in {
        "",
        "NONE",
        "NAN",
        "NULL",
        "CLIENTE SEM NOME",
        "NOME NAO INFORMADO",
        "NAO INFORMADO",
        "E-MAIL NAO INFORMADO",
        "EMAIL NAO INFORMADO",
        "ACAO",
    }


def clean_client_series(series: pd.Series) -> pd.Series:
    cleaned = series.fillna("").astype(str).str.strip()
    return cleaned.mask(cleaned.map(is_generic_client_name), pd.NA)


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


def metric_key(value) -> str:
    return normalize_text(value).lower().replace(" ", "_")


def contains_text(series: pd.Series, words: list[str]) -> pd.Series:
    text = series.fillna("").astype(str).map(normalize_text)
    mask = pd.Series(False, index=series.index)
    for word in words:
        mask = mask | text.str.contains(normalize_text(word), na=False)
    return mask


def extract_nome_cliente(text: str) -> str:
    if not isinstance(text, str):
        return ""

    match = re.search(r"nome\s+do\s+cliente\s*:\s*([^\n\r]+)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ""


def filter_stage_clients(deals_df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    if deals_df.empty:
        return deals_df

    etapa = deals_df["etapa"].fillna("")
    pipeline = deals_df["pipeline"].fillna("")
    filters = {
        "novo_lead": contains_text(etapa, ["NOVO LEAD", "NOVA VENDA"]),
        "aguardando_atendimento": contains_text(etapa, ["AGUARDANDO ATENDIMENTO"]),
        "em_atendimento": contains_text(etapa, ["EM ATENDIMENTO", "ATENDIMENTO"]),
        "cadencia": contains_text(pipeline, ["CADENCIA"]) | contains_text(etapa, ["DIA 1", "DIA 2", "DIA 3", "DIA 4", "DIA 5"]),
        "recuperacao_lead": contains_text(pipeline, ["RECUPERACAO DE LEAD"]),
        "acompanhamento": contains_text(etapa, ["ACOMPANHAMENTO"]),
        "visita_agendada": contains_text(etapa, ["VISITA AGENDADA"]),
        "visita_realizada": contains_text(etapa, ["VISITA REALIZADA"]),
        "aguardando_documentos": contains_text(etapa, ["AGUARDANDO DOCUMENTOS"]),
        "recusa_pasteiro": contains_text(etapa, ["RECUSA PASTEIRO"]),
        "analises_enviadas": contains_text(etapa, ["ANALISE DE CREDITO", "1 ANALISE", "1A ANALISE", "NOVA ANALISE"]),
        "conferencia_pasteiro": contains_text(etapa, ["CONFERENCIA DO PASTEIRO"]),
        "pendencias": contains_text(etapa, ["DOC PENDENTE", "PENDENCIA", "PENDENTE"]),
        "condicionados": contains_text(etapa, ["CONDICIONADO"]),
        "restricoes": contains_text(etapa, ["RESTRICAO"]),
        "aprovacoes": contains_text(etapa, ["APROVADO", "APROVACAO"]),
        "reprovados": contains_text(etapa, ["REPROVADO", "REPROVACAO", "RECUSADO", "RECUSADA"]),
    }
    mask = filters.get(metric_col)
    return deals_df[mask].copy() if mask is not None else deals_df


def build_client_table(
    metric_col: str,
    corretor_nome: str,
    deals_df: pd.DataFrame,
    actions_df: pd.DataFrame,
    data_ini: date,
    data_fim: date,
    activity_cols: list[str],
) -> pd.DataFrame:
    deals = deals_df.copy()
    actions = actions_df.copy()

    if corretor_nome != "Todos os corretores":
        deals = deals[deals["responsavel"] == corretor_nome].copy()
        actions = actions[actions["responsavel"] == corretor_nome].copy()

    if metric_col == "leads_recebidos" and "created_at" in deals.columns:
        created = pd.to_datetime(deals["created_at"], errors="coerce")
        deals = deals[created.isna() | ((created.dt.date >= data_ini) & (created.dt.date <= data_fim))].copy()
    elif metric_col in STAGE_COLS:
        deals = filter_stage_clients(deals, metric_col)
    elif metric_col in {"acoes_total", "leads_com_atividade", "analise_enviada_atividade"} or metric_col in activity_cols:
        if actions.empty:
            return pd.DataFrame(columns=["id_lead", "cliente", "responsavel", "equipe", "atividade", "data"])

        action_keys = actions["tipo_acao"].fillna("").astype(str).map(metric_key)
        if metric_col in activity_cols:
            actions = actions[action_keys == metric_col].copy()
        elif metric_col == "analise_enviada_atividade":
            text = (actions["tipo_acao"].fillna("").astype(str) + " " + actions["descricao"].fillna("").astype(str)).map(normalize_text)
            actions = actions[
                action_keys.isin(["1_analise", "1_analise_enviada", "1_analise_confirmada", "analise_de_credito", "analise_credito_confirmada"])
                | (
                    text.str.contains("ANALISE", na=False)
                    & (
                        text.str.contains("ENVIADO", na=False)
                        | text.str.contains("ENVIADA", na=False)
                        | text.str.contains("CREDITO", na=False)
                        | text.str.contains("1", na=False)
                        | text.str.contains("PRIMEIRA", na=False)
                    )
                )
            ].copy()

        lookup_cols = [col for col in ["lead_id", "person_id", "lead", "cliente", "pipeline", "etapa"] if col in deals_df.columns]
        lookup = deals_df[lookup_cols].drop_duplicates("lead_id") if lookup_cols and "lead_id" in lookup_cols else pd.DataFrame()
        if "lead" in actions.columns:
            actions["lead_atividade"] = clean_client_series(actions["lead"])
        else:
            actions["lead_atividade"] = pd.NA
        if not lookup.empty:
            actions = actions.merge(lookup, on="lead_id", how="left")
        if "cliente_y" in actions.columns:
            actions["cliente"] = clean_client_series(actions["cliente_y"])
        elif "cliente" in actions.columns:
            actions["cliente"] = clean_client_series(actions["cliente"])
        elif "lead_y" in actions.columns:
            actions["cliente"] = clean_client_series(actions["lead_y"])
        elif "lead" in actions.columns:
            actions["cliente"] = clean_client_series(actions["lead"])
        else:
            actions["cliente"] = pd.NA

        if "person_id" in actions.columns and "person_id" in deals_df.columns and "cliente" in deals_df.columns:
            person_lookup = (
                deals_df[["person_id", "cliente"]]
                .dropna()
                .drop_duplicates("person_id")
                .set_index("person_id")["cliente"]
                .to_dict()
            )
            mapped_person = clean_client_series(actions["person_id"].map(person_lookup))
            actions["cliente"] = actions["cliente"].fillna(mapped_person)

        nome_extraido = actions["descricao"].fillna("").astype(str).apply(extract_nome_cliente).replace("", pd.NA)
        actions["cliente"] = actions["cliente"].fillna(actions["lead_atividade"])
        actions["cliente"] = actions["cliente"].fillna(nome_extraido)
        actions["cliente"] = actions["cliente"].fillna("ID " + actions["lead_id"].astype(str))
        actions["data_conclusao"] = pd.to_datetime(actions["data_acao"], errors="coerce")
        actions = actions.sort_values("data_conclusao", ascending=False)
        actions["dedupe_key"] = actions["lead_id"].fillna("").astype(str)
        missing_dedupe = actions["dedupe_key"].isin(["", "nan", "None"])
        actions.loc[missing_dedupe, "dedupe_key"] = actions.loc[missing_dedupe, "cliente"].map(normalize_text)
        actions["id_lead"] = actions["lead_id"].astype(str)
        table = actions.rename(columns={"tipo_acao": "atividade"})[
            ["dedupe_key", "id_lead", "cliente", "responsavel", "equipe", "atividade", "data_conclusao"]
        ].drop_duplicates("dedupe_key")
        table["data_conclusao"] = table["data_conclusao"].dt.strftime("%d/%m/%Y %H:%M").fillna("")
        table = table.drop(columns=["dedupe_key"])
        return table.sort_values(["responsavel", "cliente"]).reset_index(drop=True)

    if deals.empty:
        return pd.DataFrame(columns=["cliente", "responsavel", "equipe", "funil", "etapa"])

    table = deals.rename(columns={"lead": "cliente", "pipeline": "funil"})[
        ["cliente", "responsavel", "equipe", "funil", "etapa"]
    ].drop_duplicates()
    table["cliente"] = table["cliente"].fillna("").replace("", "Cliente sem nome")
    return table.sort_values(["responsavel", "cliente"]).reset_index(drop=True)


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


def collect_person_ids(*frames: pd.DataFrame, limit: int = 120) -> list[str]:
    ids = []
    id_cols = ["person_id", "person.id", "contact_id", "contact.id", "customer_id", "client_id"]
    for frame in frames:
        if frame is None or frame.empty:
            continue
        for col in id_cols:
            if col in frame.columns:
                ids.extend(frame[col].dropna().apply(normalize_id).tolist())
    unique_ids = [person_id for person_id in dict.fromkeys(ids) if person_id]
    return unique_ids[:limit]


def collect_deal_ids(*frames: pd.DataFrame, limit: int = 120) -> list[str]:
    ids = []
    id_cols = ["deal_id", "deal.id", "card_id", "lead_id", "opportunity_id", "opportunity.id"]
    for frame in frames:
        if frame is None or frame.empty:
            continue
        for col in id_cols:
            if col in frame.columns:
                ids.extend(frame[col].dropna().apply(normalize_id).tolist())
    unique_ids = [deal_id for deal_id in dict.fromkeys(ids) if deal_id]
    return unique_ids[:limit]


def fetch_deal_details(client: PiperunClient, deal_ids: list[str]) -> pd.DataFrame:
    frames = []
    for deal_id in deal_ids:
        endpoints = [
            f"deals/{deal_id}",
            f"opportunities/{deal_id}",
            f"cards/{deal_id}",
            f"leads/{deal_id}",
        ]
        result = client.fetch_first_available(endpoints, params={}, max_pages=1, per_page=1)
        if result.ok and not result.data.empty:
            frames.append(result.data)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def merge_detail_rows(base: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    if base is None or base.empty:
        return details if details is not None else pd.DataFrame()
    if details is None or details.empty:
        return base

    combined = pd.concat([base, details], ignore_index=True, sort=False)
    id_col = next((col for col in ["id", "deal_id", "opportunity_id", "card_id"] if col in combined.columns), "")
    if not id_col:
        return combined

    combined["_merge_id"] = combined[id_col].apply(normalize_id)
    combined["_filled_cols"] = combined.notna().sum(axis=1)
    combined = combined.sort_values("_filled_cols").drop_duplicates("_merge_id", keep="last")
    return combined.drop(columns=["_merge_id", "_filled_cols"]).reset_index(drop=True)


def fetch_person_details(client: PiperunClient, person_ids: list[str]) -> pd.DataFrame:
    frames = []
    for person_id in person_ids:
        endpoints = [
            f"persons/{person_id}",
            f"people/{person_id}",
            f"contacts/{person_id}",
            f"customers/{person_id}",
            f"clients/{person_id}",
        ]
        result = client.fetch_first_available(endpoints, params={}, max_pages=1, per_page=1)
        if result.ok and not result.data.empty:
            frames.append(result.data)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


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

    actions_df = pd.concat(action_frames, ignore_index=True) if action_frames else pd.DataFrame()
    deal_detail_ids = collect_deal_ids(actions_df)
    deal_details = fetch_deal_details(client, deal_detail_ids)
    if not deal_details.empty:
        deals_result.data = merge_detail_rows(deals_result.data, deal_details)

    persons_result = client.fetch_first_available(PERSON_ENDPOINTS, params={}, max_pages=max_pages, per_page=per_page)
    person_detail_ids = collect_person_ids(actions_df, deals_result.data)
    person_details = fetch_person_details(client, person_detail_ids)
    person_frames = []
    if persons_result.ok and not persons_result.data.empty:
        person_frames.append(persons_result.data)
    if not person_details.empty:
        person_frames.append(person_details)
    persons_df = pd.concat(person_frames, ignore_index=True) if person_frames else pd.DataFrame()

    return {
        "deals_result": deals_result,
        "actions_df": actions_df,
        "action_status": pd.DataFrame(action_status),
        "users_result": client.fetch_first_available(USER_ENDPOINTS, params={}, max_pages=5, per_page=per_page),
        "stages_result": client.fetch_first_available(STAGE_ENDPOINTS, params={}, max_pages=10, per_page=per_page),
        "pipelines_result": client.fetch_first_available(PIPELINE_ENDPOINTS, params={}, max_pages=5, per_page=per_page),
        "activity_types_result": client.fetch_first_available(ACTIVITY_TYPE_ENDPOINTS, params={}, max_pages=5, per_page=per_page),
        "persons_df": persons_df,
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
persons_df = carga["persons_df"]
corretor_equipe_map, corretor_nome_map = carregar_referencias_corretores()

if not deals_result.ok:
    st.error("Nao consegui carregar leads/cards/oportunidades do PipeRun.")
    st.write(deals_result.error)
    st.stop()

reference_kwargs = {
    "users_raw": users_result.data if users_result.ok else pd.DataFrame(),
    "stages_raw": stages_result.data if stages_result.ok else pd.DataFrame(),
    "pipelines_raw": pipelines_result.data if pipelines_result.ok else pd.DataFrame(),
    "activity_types_raw": activity_types_result.data if activity_types_result.ok else pd.DataFrame(),
    "persons_raw": persons_df,
    "corretor_equipe_map": corretor_equipe_map,
    "corretor_nome_map": corretor_nome_map,
}
try:
    reference_maps = build_reference_maps(**reference_kwargs)
except TypeError:
    reference_kwargs.pop("persons_raw", None)
    reference_maps = build_reference_maps(**reference_kwargs)

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
deals_norm = metricas.get("deals_normalizados", pd.DataFrame())
acoes_norm = metricas.get("acoes_normalizadas", pd.DataFrame())

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
        corretor_tabela = "Todos os corretores" if corretor_sel == "Toda imobiliaria" else corretor_sel
        clientes_atividade = build_client_table(
            atividade_sel,
            corretor_tabela,
            deals_norm,
            acoes_norm,
            data_ini,
            data_fim,
            activity_cols,
        )
        atividade_qtde = len(clientes_atividade)
        resumo_atividade = {**resumo, atividade_sel: atividade_qtde}
        if atividade_sel in {"1_analise", "1_analise_enviada", "1_analise_confirmada", "analise_de_credito", "analise_credito_confirmada"}:
            resumo_atividade["analise_enviada_atividade"] = atividade_qtde
        show_metric_grid(
            resumo_atividade,
            [
                (pretty_label(atividade_sel), atividade_sel),
                ("Leads com atividade", "leads_com_atividade"),
                ("Registros de atividade", "acoes_total"),
                ("Analise por atividade", "analise_enviada_atividade"),
            ],
        )

        st.subheader(f"Corretores em {pretty_label(atividade_sel)}")
        show_entity_cards(df_view, "responsavel", atividade_sel, limit=16)

        st.subheader(f"Leads em {pretty_label(atividade_sel)}")
        if clientes_atividade.empty:
            st.info("Nenhum lead encontrado para essa atividade.")
        else:
            st.dataframe(clientes_atividade, use_container_width=True, hide_index=True)
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

    st.subheader(f"Clientes em {pretty_label(ranking_metric)}")
    clientes = build_client_table(
        ranking_metric,
        corretor_ranking,
        deals_norm,
        acoes_norm,
        data_ini,
        data_fim,
        activity_cols,
    )
    if clientes.empty:
        st.info("Nenhum cliente encontrado para esse filtro.")
    else:
        st.dataframe(clientes, use_container_width=True, hide_index=True)
