from __future__ import annotations

import unicodedata
from datetime import date
from typing import Iterable

import pandas as pd

from utils.piperun_client import PiperunClient


DEAL_ENDPOINTS = ["deals", "opportunities", "cards", "leads"]
USER_ENDPOINTS = ["users", "account/users", "user"]
STAGE_ENDPOINTS = ["stages", "pipeline-stages", "pipeline_stages", "pipelines/stages"]
PIPELINE_ENDPOINTS = ["pipelines", "pipeline", "funnels"]


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text).encode("ascii", errors="ignore").decode("ascii")
    return " ".join(text.split())


def normalize_id(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null"}:
        return ""
    try:
        number = float(text)
        if number.is_integer():
            return str(int(number))
    except Exception:
        pass
    return text[:-2] if text.endswith(".0") and text[:-2].isdigit() else text


def first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str:
    available = {str(col).lower(): col for col in columns}
    normalized = {normalize_text(col).replace(" ", "_").lower(): col for col in columns}

    for candidate in candidates:
        key = candidate.lower()
        if key in available:
            return available[key]
        if key in normalized:
            return normalized[key]

    for candidate in candidates:
        key = candidate.lower()
        for col_lower, real_col in available.items():
            if key in col_lower:
                return real_col
    return ""


def make_lookup(df: pd.DataFrame, id_candidates: list[str], value_candidates: list[str]) -> dict[str, str]:
    if df is None or df.empty:
        return {}
    id_col = first_existing(df.columns, id_candidates)
    value_col = first_existing(df.columns, value_candidates)
    if not id_col or not value_col:
        return {}

    lookup = {}
    for _, row in df[[id_col, value_col]].dropna(subset=[id_col]).iterrows():
        key = normalize_id(row[id_col])
        value = normalize_text(row[value_col])
        if key and value:
            lookup[key] = value
    return lookup


def status_from_piperun(stage: str, pipeline: str, status: str) -> str:
    stage_text = normalize_text(stage)
    pipeline_text = normalize_text(pipeline)
    status_text = normalize_text(status)
    combined = f"{pipeline_text} {stage_text} {status_text}"

    if any(word in combined for word in ["DESIST", "PERDIDO", "LOST"]):
        return "DESISTIU"
    if "REPROV" in combined or "RECUSAD" in combined:
        return "REPROVADO"
    if "APROVADO BACEN" in combined:
        return "APROVADO BACEN"
    if "RESTRICAO" in combined or "CONDICIONADO" in combined:
        return "APROVADO COM RESTRICAO"
    if "APROV" in combined or "GANHO" in combined or "WON" in combined:
        return "APROVADO"
    if "VENDA" in combined or "FINANCEIRO" in combined or "PAGAMENTO" in combined:
        return "VENDA GERADA"
    if "REANALISE" in combined:
        return "REANALISE"
    if "ANALISE" in combined or "CREDITO" in combined or "NOVA ANALISE" in combined:
        return "EM ANALISE"
    return ""


def month_label(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%m/%Y").fillna("")


def fetch_piperun_reference_maps(client: PiperunClient, per_page: int) -> dict[str, dict[str, str]]:
    users = client.fetch_first_available(USER_ENDPOINTS, params={}, max_pages=5, per_page=per_page)
    stages = client.fetch_first_available(STAGE_ENDPOINTS, params={}, max_pages=10, per_page=per_page)
    pipelines = client.fetch_first_available(PIPELINE_ENDPOINTS, params={}, max_pages=5, per_page=per_page)

    users_df = users.data if users.ok else pd.DataFrame()
    stages_df = stages.data if stages.ok else pd.DataFrame()
    pipelines_df = pipelines.data if pipelines.ok else pd.DataFrame()

    return {
        "user_name": make_lookup(users_df, ["id", "user_id", "owner_id"], ["name", "nome", "user.name", "owner.name", "email"]),
        "user_team": make_lookup(users_df, ["id", "user_id", "owner_id"], ["team.name", "team", "equipe", "group.name", "department.name"]),
        "stage_name": make_lookup(stages_df, ["id", "stage_id", "pipeline_stage_id"], ["name", "nome", "title", "stage.name", "description"]),
        "pipeline_name": make_lookup(pipelines_df, ["id", "pipeline_id", "funil_id"], ["name", "nome", "title", "pipeline.name", "description"]),
    }


def piperun_deals_to_commercial_df(deals_raw: pd.DataFrame, refs: dict[str, dict[str, str]]) -> pd.DataFrame:
    if deals_raw is None or deals_raw.empty:
        return pd.DataFrame()

    df = deals_raw.copy()
    cols = df.columns

    id_col = first_existing(cols, ["id", "deal_id", "opportunity_id", "card_id"])
    title_col = first_existing(cols, ["title", "name", "nome", "deal_title", "person.name", "customer.name"])
    client_col = first_existing(cols, ["person.name", "contact.name", "customer.name", "client.name", "company.name", "title", "name"])
    cpf_col = first_existing(cols, ["person.cpf", "contact.cpf", "customer.cpf", "cpf", "document", "document_number"])
    created_col = first_existing(cols, ["created_at", "created", "data_criacao", "data_captura", "createdAt"])
    updated_col = first_existing(cols, ["updated_at", "last_stage_updated_at", "stage_changed_at", "last_contact_at"])
    owner_col = first_existing(cols, ["owner.name", "user.name", "responsible.name", "responsavel", "owner", "user_name"])
    owner_id_col = first_existing(cols, ["owner.id", "user.id", "responsible.id", "owner_id", "user_id"])
    team_col = first_existing(cols, ["team.name", "team", "equipe", "company_team.name"])
    stage_col = first_existing(cols, ["stage.name", "stage", "step.name", "status.name", "column.name", "etapa", "pipeline_stage.name"])
    stage_id_col = first_existing(cols, ["stage_id", "pipeline_stage_id", "stage.id"])
    pipeline_col = first_existing(cols, ["pipeline.name", "pipeline", "funil"])
    pipeline_id_col = first_existing(cols, ["pipeline_id", "pipeline.id", "funil_id"])
    status_col = first_existing(cols, ["status", "deal_status", "state"])
    value_col = first_existing(cols, ["value", "valor", "amount", "price", "value_mrr"])

    out = pd.DataFrame(index=df.index)
    out["ID_LEAD"] = df[id_col].apply(normalize_id) if id_col else df.index.astype(str)

    raw_date = df[created_col] if created_col else df[updated_col] if updated_col else pd.NaT
    out["DIA"] = pd.to_datetime(raw_date, errors="coerce").dt.date
    out["DATA_BASE"] = pd.to_datetime(out["DIA"], errors="coerce").dt.to_period("M").dt.to_timestamp().dt.date
    out["DATA_BASE_LABEL"] = month_label(out["DIA"])

    if owner_col:
        out["CORRETOR"] = df[owner_col].apply(normalize_text)
    elif owner_id_col:
        out["CORRETOR"] = df[owner_id_col].apply(normalize_id).map(refs.get("user_name", {})).fillna("")
    else:
        out["CORRETOR"] = ""
    if owner_id_col:
        mapped_owner = df[owner_id_col].apply(normalize_id).map(refs.get("user_name", {}))
        out["CORRETOR"] = mapped_owner.fillna(out["CORRETOR"])
    out["CORRETOR"] = out["CORRETOR"].replace("", "SEM RESPONSAVEL")

    if team_col:
        out["EQUIPE"] = df[team_col].apply(normalize_text)
    else:
        out["EQUIPE"] = ""
    if owner_id_col:
        mapped_team = df[owner_id_col].apply(normalize_id).map(refs.get("user_team", {}))
        out["EQUIPE"] = mapped_team.fillna(out["EQUIPE"])
    out["EQUIPE"] = out["EQUIPE"].replace("", "SEM EQUIPE")

    stage = df[stage_col].apply(normalize_text) if stage_col else pd.Series("", index=df.index)
    if stage_id_col:
        mapped_stage = df[stage_id_col].apply(normalize_id).map(refs.get("stage_name", {}))
        stage = mapped_stage.fillna(stage)

    pipeline = df[pipeline_col].apply(normalize_text) if pipeline_col else pd.Series("", index=df.index)
    if pipeline_id_col:
        mapped_pipeline = df[pipeline_id_col].apply(normalize_id).map(refs.get("pipeline_name", {}))
        pipeline = mapped_pipeline.fillna(pipeline)

    status = df[status_col].apply(normalize_text) if status_col else pd.Series("", index=df.index)
    out["FUNIL"] = pipeline
    out["ETAPA"] = stage
    out["STATUS_BASE"] = [status_from_piperun(etapa, funil, stat) for etapa, funil, stat in zip(stage, pipeline, status)]

    if client_col:
        out["NOME_CLIENTE_BASE"] = df[client_col].fillna("").astype(str).str.upper().str.strip()
    elif title_col:
        out["NOME_CLIENTE_BASE"] = df[title_col].fillna("").astype(str).str.upper().str.strip()
    else:
        out["NOME_CLIENTE_BASE"] = "NAO INFORMADO"
    out["NOME_CLIENTE_BASE"] = out["NOME_CLIENTE_BASE"].replace("", "NAO INFORMADO")

    out["CPF_CLIENTE_BASE"] = (
        df[cpf_col].fillna("").astype(str).str.replace(r"\D", "", regex=True)
        if cpf_col
        else ""
    )
    out["VGV"] = pd.to_numeric(df[value_col], errors="coerce").fillna(0) if value_col else 0
    out["CHAVE_CLIENTE"] = out["NOME_CLIENTE_BASE"].fillna("NAO INFORMADO") + " | " + out["CPF_CLIENTE_BASE"].fillna("") + " | " + out["ID_LEAD"].fillna("")

    return out


def carregar_piperun(max_pages: int = 5, per_page: int = 100) -> pd.DataFrame:
    client = PiperunClient()
    result = client.fetch_first_available(DEAL_ENDPOINTS, params={}, max_pages=max_pages, per_page=per_page)
    if not result.ok:
        raise RuntimeError(result.error or "Nao foi possivel carregar leads do PipeRun.")

    refs = fetch_piperun_reference_maps(client, per_page=per_page)
    return piperun_deals_to_commercial_df(result.data, refs)


def carregar_base_comercial(fonte: str = "piperun", max_pages: int = 5, per_page: int = 100) -> pd.DataFrame:
    if fonte == "piperun":
        return carregar_piperun(max_pages=max_pages, per_page=per_page)
    raise ValueError(f"Fonte de dados nao suportada: {fonte}")


def aplicar_perfil_corretor(df: pd.DataFrame, perfil: str, nome_usuario: str) -> pd.DataFrame:
    if perfil == "corretor" and "CORRETOR" in df.columns:
        return df[df["CORRETOR"] == str(nome_usuario or "").upper().strip()].copy()
    return df.copy()
