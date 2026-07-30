from __future__ import annotations

import unicodedata
import re
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

from utils.piperun_client import PiperunClient, date_params


DEAL_ENDPOINTS = ["deals", "opportunities", "cards", "leads"]
ACTION_ENDPOINTS = ["activities"]
USER_ENDPOINTS = ["users", "account/users", "user"]
STAGE_ENDPOINTS = ["stages", "pipeline-stages", "pipeline_stages", "pipelines/stages"]
PIPELINE_ENDPOINTS = ["pipelines", "pipeline", "funnels"]
EXPORT_ATIVIDADES_PATHS = [
    Path("data") / "atividades_piperun.xlsx",
    Path("data") / "atividades_piperun.csv",
]
EXPORT_ATIVIDADES_DESTINO = Path("data") / "atividades_piperun.xlsx"


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


def client_count_key(nome, lead_id) -> str:
    nome_norm = normalize_text(nome)
    lead_norm = normalize_id(lead_id)
    if nome_norm and nome_norm not in {"NAO INFORMADO", "CLIENTE SEM NOME", "NONE", "NAN"}:
        return nome_norm
    return lead_norm


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


def is_won_status(stage: str, pipeline: str, status: str) -> bool:
    stage_text = normalize_text(stage)
    pipeline_text = normalize_text(pipeline)
    status_text = normalize_text(status)
    combined = f"{pipeline_text} {stage_text} {status_text}"
    return any(word in combined for word in ["GANHO", "WON", "VENDA GANHA"])


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
    if is_won_status(stage, pipeline, status):
        return "VENDA GERADA"
    if "APROV" in combined:
        return "APROVADO"
    if "REANALISE" in combined:
        return "REANALISE"
    if "ANALISE" in combined or "CREDITO" in combined or "NOVA ANALISE" in combined:
        return "EM ANALISE"
    return ""


def is_primeira_analise_text(value) -> bool:
    text = normalize_text(value)
    if "ANALISE" not in text:
        return False
    if "PRIMEIRA ANALISE" in text or "PRIMEIRO ANALISE" in text:
        return True
    return bool(re.search(r"\b1\s*(A|O)?\s*ANALISE\b", text))


def credit_stage_from_text(value) -> str:
    text = normalize_text(value)
    if not text:
        return ""

    if is_primeira_analise_text(text) or "NOVA ANALISE" in text:
        return "NOVA ANALISE"
    if text == "DOC PENDENTE" or ("DOC" in text and ("PENDENTE" in text or "PENDENCIA" in text)):
        return "DOC PENDENTE"
    if "CONFERENCIA" in text and "PASTEIRO" in text:
        return "CONFERENCIA DO PASTEIRO"
    if "RECUSA" in text and "PASTEIRO" in text:
        return "RECUSA PASTEIRO"
    if "ANALISE DE CREDITO" in text:
        return "ANALISE DE CREDITO"
    if "CONDICIONADO" in text:
        return "CONDICIONADO"
    if "RESTRICAO" in text:
        return "RESTRICAO"
    if "REPROV" in text:
        return "REPROVADO"
    if "APROVADO" in text and ("PENDENCIA" in text or "C PENDENCIA" in text):
        return "APROVADO C/ PENDENCIA"
    if "APROV" in text:
        return "APROVADO"
    return ""


def credit_stage_from_activity_type(value) -> str:
    text = normalize_text(value)
    if not text:
        return ""

    if is_primeira_analise_text(text):
        return "NOVA ANALISE"
    if text == "DOC PENDENTE" or ("DOC" in text and ("PENDENTE" in text or "PENDENCIA" in text)):
        return "DOC PENDENTE"
    if "CONFERENCIA" in text and "PASTEIRO" in text:
        return "CONFERENCIA DO PASTEIRO"
    if "RECUSA" in text and "PASTEIRO" in text:
        return "RECUSA PASTEIRO"
    if "ANALISE DE CREDITO" in text:
        return "ANALISE DE CREDITO"
    if "CONDICIONADO" in text:
        return "CONDICIONADO"
    if "RESTRICAO" in text:
        return "RESTRICAO"
    if "REPROV" in text:
        return "REPROVADO"
    if "APROVADO" in text and ("PENDENCIA" in text or "C PENDENCIA" in text):
        return "APROVADO C/ PENDENCIA"
    if text in {"APROVADO", "APROVACAO"}:
        return "APROVADO"
    return ""


def action_date_column(actions_raw: pd.DataFrame) -> str:
    return first_existing(
        actions_raw.columns,
        [
            "done_at",
            "completed_at",
            "finished_at",
            "completed_on",
            "concluded_at",
            "end_at",
            "data_conclusao",
            "data_realizacao",
            "date",
            "data",
            "created_at",
            "scheduled_at",
        ],
    )


def actions_primeira_analise(actions_raw: pd.DataFrame) -> dict[str, date]:
    if actions_raw is None or actions_raw.empty:
        return {}

    cols = actions_raw.columns
    deal_id_col = first_existing(cols, ["deal_id", "deal.id", "card_id", "lead_id", "opportunity_id"])
    if not deal_id_col:
        return {}

    text_cols = [
        col
        for col in cols
        if any(key in str(col).lower() for key in ["title", "description", "comment", "text", "note", "content", "message", "type.name", "activity_type.name"])
    ]
    if not text_cols:
        return {}

    text = actions_raw[text_cols].fillna("").astype(str).agg(" ".join, axis=1)
    mask = text.apply(is_primeira_analise_text)
    analises = actions_raw.loc[mask].copy()
    if analises.empty:
        return {}

    data_col = action_date_column(analises)
    analises["_lead_id"] = analises[deal_id_col].apply(normalize_id)
    analises["_data_analise"] = pd.to_datetime(analises[data_col], errors="coerce") if data_col else pd.NaT
    analises = analises[analises["_lead_id"] != ""]
    if analises.empty:
        return {}

    datas = analises.sort_values("_data_analise").groupby("_lead_id")["_data_analise"].first()
    return {lead_id: data.date() if pd.notnull(data) else pd.NaT for lead_id, data in datas.items()}


def actions_credito_por_lead(actions_raw: pd.DataFrame, refs: dict[str, dict[str, str]] | None = None) -> pd.DataFrame:
    if actions_raw is None or actions_raw.empty:
        return pd.DataFrame(columns=["ID_LEAD", "DATA_EVENTO", "ETAPA_EVENTO"])
    refs = refs or {}

    cols = actions_raw.columns
    deal_id_col = first_existing(cols, ["deal_id", "deal.id", "card_id", "lead_id", "opportunity_id"])
    if not deal_id_col:
        return pd.DataFrame(columns=["ID_LEAD", "DATA_EVENTO", "ETAPA_EVENTO"])

    text_cols = [
        col
        for col in cols
        if any(key in str(col).lower() for key in ["title", "description", "comment", "text", "note", "content", "message", "type.name", "activity_type.name", "assunto", "tipo"])
    ]
    if not text_cols:
        return pd.DataFrame(columns=["ID_LEAD", "DATA_EVENTO", "ETAPA_EVENTO"])

    data_col = action_date_column(actions_raw)
    type_col = first_existing(
        cols,
        [
            "activity_type.name",
            "activityType.name",
            "type.name",
            "tipo",
            "type",
            "activity_type",
            "activityType",
        ],
    )
    stage_col = first_existing(
        cols,
        [
            "stage.name",
            "deal.stage.name",
            "opportunity.stage.name",
            "pipeline_stage.name",
            "stage",
            "etapa",
            "deal_stage",
            "column.name",
        ],
    )
    owner_col = first_existing(cols, ["responsible.name", "responsavel", "owner.name", "user.name", "requester.name", "user_name", "owner"])
    owner_id_col = first_existing(cols, ["owner_id", "user_id", "requester_id", "responsible.id", "owner.id", "user.id"])
    team_col = first_existing(cols, ["team.name", "team", "equipe", "group.name", "department.name"])
    client_col = first_existing(
        cols,
        [
            "opportunity",
            "opportunity.title",
            "deal.title",
            "deal.name",
            "person.name",
            "contact.name",
            "customer.name",
            "pessoa",
            "person",
            "title",
        ],
    )
    pipeline_col = first_existing(cols, ["pipeline.name", "deal.pipeline.name", "funil", "pipeline"])

    base = pd.DataFrame(index=actions_raw.index)
    base["ID_LEAD"] = actions_raw[deal_id_col].apply(normalize_id)
    base["TEXTO_EVENTO"] = actions_raw[text_cols].fillna("").astype(str).agg(" ".join, axis=1)
    base["TIPO_EVENTO"] = actions_raw[type_col].apply(normalize_text) if type_col else ""
    base["DATA_EVENTO"] = pd.to_datetime(actions_raw[data_col], errors="coerce").dt.date if data_col else pd.NaT
    base["ETAPA_ORIGINAL"] = actions_raw[stage_col].apply(normalize_text) if stage_col else ""
    base["ETAPA_RESULTADO"] = base["ETAPA_ORIGINAL"].apply(credit_stage_from_text)
    base["ETAPA_TIPO"] = base["TIPO_EVENTO"].apply(credit_stage_from_activity_type)
    base["CORRETOR"] = actions_raw[owner_col].apply(normalize_text) if owner_col else ""
    if owner_id_col:
        mapped_owner = actions_raw[owner_id_col].apply(normalize_id).map(refs.get("user_name", {}))
        base["CORRETOR"] = mapped_owner.fillna(base["CORRETOR"])
    base["CORRETOR"] = base["CORRETOR"].replace("", "SEM RESPONSAVEL")
    base["EQUIPE"] = actions_raw[team_col].apply(normalize_text) if team_col else ""
    if owner_id_col:
        mapped_team = actions_raw[owner_id_col].apply(normalize_id).map(refs.get("user_team", {}))
        base["EQUIPE"] = mapped_team.fillna(base["EQUIPE"])
    base["EQUIPE"] = base["EQUIPE"].replace("", "SEM EQUIPE")
    base["NOME_CLIENTE_BASE"] = actions_raw[client_col].fillna("").astype(str).str.upper().str.strip() if client_col else ""
    base["NOME_CLIENTE_BASE"] = base["NOME_CLIENTE_BASE"].replace("", "NAO INFORMADO")
    base["FUNIL"] = actions_raw[pipeline_col].apply(normalize_text) if pipeline_col else "CREDITO"

    eventos_base = base[base["ID_LEAD"] != ""].copy()
    eventos_base["ETAPA_EVENTO"] = eventos_base["ETAPA_TIPO"]
    eventos_base = eventos_base[eventos_base["ETAPA_EVENTO"] != ""]

    if eventos_base.empty:
        return pd.DataFrame(columns=["ID_LEAD", "DATA_EVENTO", "ETAPA_EVENTO"])

    evento_cols = ["ID_LEAD", "DATA_EVENTO", "CORRETOR", "EQUIPE", "NOME_CLIENTE_BASE", "FUNIL", "TIPO_EVENTO"]
    eventos = eventos_base[evento_cols + ["ETAPA_EVENTO"]].copy()
    return eventos[evento_cols + ["ETAPA_EVENTO"]].drop_duplicates()


def activity_date_params(data_ini: date | None, data_fim: date | None) -> dict:
    if not data_ini or not data_fim:
        return {}
    start = f"{data_ini.isoformat()} 00:00:00"
    end = f"{data_fim.isoformat()} 23:59:59"
    return {
        "status": 2,
        "with": "deal,owner,requester,activityType,persons,companies,pipeline,stage",
        "start_at_start": start,
        "start_at_end": end,
    }


def carregar_atividades_piperun(client: PiperunClient, max_pages: int, per_page: int, params: dict | None = None) -> pd.DataFrame:
    frames = []
    for endpoint in ACTION_ENDPOINTS:
        result = client.fetch_first_available([endpoint], params=params or {}, max_pages=max_pages, per_page=per_page)
        if result.ok and not result.data.empty:
            frames.append(result.data)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def month_label(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%m/%Y").fillna("")


def carregar_export_atividades(path: str | Path | None = None) -> pd.DataFrame:
    if path:
        paths = [Path(path)]
    else:
        paths = list(EXPORT_ATIVIDADES_PATHS)
        paths.extend(sorted(Path("data").glob("atividades*.xlsx"), key=lambda item: item.stat().st_mtime, reverse=True))
        paths.extend(sorted(Path("data").glob("atividades*.csv"), key=lambda item: item.stat().st_mtime, reverse=True))

    arquivo = next((candidate for candidate in paths if candidate.exists()), None)
    if arquivo is None:
        return pd.DataFrame()

    if arquivo.suffix.lower() == ".csv":
        raw = pd.read_csv(arquivo)
    else:
        raw = pd.read_excel(arquivo)
    if raw.empty:
        return pd.DataFrame()

    required = ["Tipo", "Responsável", "Início", "Concluído em", "Funil (Oportunidade)", "Etapa (Oportunidade)"]
    missing = [col for col in required if col not in raw.columns]
    if missing:
        raise RuntimeError(f"Exportacao PipeRun sem colunas esperadas: {', '.join(missing)}")

    def col_text(name: str, default: str = "") -> pd.Series:
        if name in raw.columns:
            return raw[name].fillna("").astype(str)
        return pd.Series(default, index=raw.index)

    base = pd.DataFrame(index=raw.index)
    base["ID_LEAD"] = col_text("ID (Oportunidade)").apply(normalize_id)
    base.loc[base["ID_LEAD"] == "", "ID_LEAD"] = col_text("ID").apply(normalize_id)
    base["CORRETOR"] = col_text("Responsável").apply(normalize_text).replace("", "SEM RESPONSAVEL")
    base["EQUIPE"] = "SEM EQUIPE"
    base["FUNIL"] = col_text("Funil (Oportunidade)").apply(normalize_text).replace("", "CREDITO")
    base["ETAPA_ORIGINAL"] = col_text("Etapa (Oportunidade)").apply(normalize_text)
    base["NOME_CLIENTE_BASE"] = col_text("Nome completo (Pessoa)").str.upper().str.strip()
    oportunidade = col_text("Titulo (Oportunidade)").str.upper().str.strip()
    base["NOME_CLIENTE_BASE"] = base["NOME_CLIENTE_BASE"].where(base["NOME_CLIENTE_BASE"] != "", oportunidade)
    base["NOME_CLIENTE_BASE"] = base["NOME_CLIENTE_BASE"].replace("", "NAO INFORMADO")
    base["CPF_CLIENTE_BASE"] = col_text("CPF (Pessoa)").str.replace(r"\D", "", regex=True)
    base["INICIO"] = pd.to_datetime(raw["Início"], errors="coerce").dt.date
    base["CONCLUIDO_EM"] = pd.to_datetime(raw["Concluído em"], errors="coerce").dt.date
    base["TIPO_ATIVIDADE"] = col_text("Tipo").apply(normalize_text)
    base["STATUS_ATIVIDADE"] = col_text("Status").apply(normalize_text)
    base["STATUS_OPORTUNIDADE"] = col_text("Status (Oportunidade)").apply(normalize_text)
    base["GANHO"] = base["STATUS_OPORTUNIDADE"].isin(["GANHA", "GANHO", "WON"])
    base["VGV"] = 0.0
    base["CHAVE_CLIENTE"] = base["ID_LEAD"]

    analises = base[base["TIPO_ATIVIDADE"].apply(is_primeira_analise_text)].copy()
    if analises.empty:
        return pd.DataFrame()

    common_cols = ["ID_LEAD", "CORRETOR", "EQUIPE", "FUNIL", "NOME_CLIENTE_BASE", "CPF_CLIENTE_BASE", "CHAVE_CLIENTE", "GANHO", "VGV"]
    eventos_analise = analises[common_cols].copy()
    eventos_analise["DIA"] = analises["INICIO"]
    eventos_analise["DATA_EVENTO"] = analises["INICIO"]
    eventos_analise["ETAPA_EVENTO"] = "NOVA ANALISE"
    eventos_analise["ETAPA"] = "NOVA ANALISE"
    eventos_analise["STATUS_BASE"] = "EM ANALISE"

    eventos_resultado = analises[common_cols].copy()
    eventos_resultado["DIA"] = analises["CONCLUIDO_EM"].where(analises["CONCLUIDO_EM"].notna(), analises["INICIO"])
    eventos_resultado["DATA_EVENTO"] = eventos_resultado["DIA"]
    eventos_resultado["ETAPA_EVENTO"] = analises["ETAPA_ORIGINAL"].apply(credit_stage_from_text)
    eventos_resultado = eventos_resultado[eventos_resultado["ETAPA_EVENTO"] != ""]
    eventos_resultado = eventos_resultado[eventos_resultado["ETAPA_EVENTO"] != "NOVA ANALISE"]
    eventos_resultado["ETAPA"] = eventos_resultado["ETAPA_EVENTO"]
    eventos_resultado["STATUS_BASE"] = eventos_resultado["ETAPA_EVENTO"]

    eventos = pd.concat([eventos_analise, eventos_resultado], ignore_index=True)
    eventos["DATA_BASE"] = pd.to_datetime(eventos["DIA"], errors="coerce").dt.to_period("M").dt.to_timestamp().dt.date
    eventos["DATA_BASE_LABEL"] = month_label(eventos["DIA"])
    eventos["TEM_1_ANALISE"] = eventos["ETAPA_EVENTO"].eq("NOVA ANALISE")
    eventos["DATA_1_ANALISE"] = eventos["DATA_EVENTO"].where(eventos["TEM_1_ANALISE"])
    eventos["ORIGEM_REGISTRO"] = "EXPORT_ATIVIDADES"
    return eventos.drop_duplicates()


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


def piperun_deals_to_commercial_df(
    deals_raw: pd.DataFrame,
    refs: dict[str, dict[str, str]],
    primeira_analise_datas: dict[str, date] | None = None,
    eventos_credito: pd.DataFrame | None = None,
) -> pd.DataFrame:
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
    out["GANHO"] = [is_won_status(etapa, funil, stat) for etapa, funil, stat in zip(stage, pipeline, status)]
    out["STATUS_BASE"] = [status_from_piperun(etapa, funil, stat) for etapa, funil, stat in zip(stage, pipeline, status)]
    primeira_analise_datas = primeira_analise_datas or {}
    out["DATA_1_ANALISE"] = out["ID_LEAD"].map(primeira_analise_datas)
    out["TEM_1_ANALISE"] = out["DATA_1_ANALISE"].notna()
    out.loc[out["TEM_1_ANALISE"] & (out["STATUS_BASE"] == ""), "STATUS_BASE"] = "EM ANALISE"

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


def carregar_piperun(max_pages: int = 5, per_page: int = 100, data_ini: date | None = None, data_fim: date | None = None) -> pd.DataFrame:
    client = PiperunClient()
    refs = fetch_piperun_reference_maps(client, per_page=per_page)
    activity_params = activity_date_params(data_ini, data_fim)
    actions = carregar_atividades_piperun(client, max_pages=max_pages, per_page=per_page, params=activity_params)
    primeira_analise_datas = actions_primeira_analise(actions)
    eventos_credito = actions_credito_por_lead(actions, refs=refs)

    params = {"with": "persons,companies,users,pipeline,stage"}
    if data_ini and data_fim:
        params.update(
            {
                "stage_movement_at_start": f"{data_ini.isoformat()} 00:00:00",
                "stage_movement_at_end": f"{data_fim.isoformat()} 23:59:59",
            }
        )
    result = client.fetch_first_available(DEAL_ENDPOINTS, params=params, max_pages=max_pages, per_page=per_page)
    base = piperun_deals_to_commercial_df(result.data if result.ok else pd.DataFrame(), refs, primeira_analise_datas=primeira_analise_datas)
    if eventos_credito.empty:
        if not result.ok and base.empty:
            raise RuntimeError(result.error or "Nao foi possivel carregar dados do PipeRun.")
        return base

    if not base.empty:
        base_keys = base[["ID_LEAD", "CORRETOR", "EQUIPE", "NOME_CLIENTE_BASE", "STATUS_BASE", "GANHO", "VGV"]].drop_duplicates("ID_LEAD")
        eventos_credito = eventos_credito.merge(base_keys, on="ID_LEAD", how="left", suffixes=("", "_LEAD"))
        for col in ["CORRETOR", "EQUIPE", "NOME_CLIENTE_BASE"]:
            lead_col = f"{col}_LEAD"
            if lead_col in eventos_credito.columns:
                eventos_credito[col] = eventos_credito[col].where(eventos_credito[col].notna() & (eventos_credito[col] != ""), eventos_credito[lead_col])
        for col, default in [("STATUS_BASE", ""), ("GANHO", False), ("VGV", 0.0)]:
            if col not in eventos_credito.columns:
                eventos_credito[col] = default
    else:
        eventos_credito["STATUS_BASE"] = ""
        eventos_credito["GANHO"] = False
        eventos_credito["VGV"] = 0.0

    for col, default in [
        ("CORRETOR", "SEM RESPONSAVEL"),
        ("EQUIPE", "SEM EQUIPE"),
        ("NOME_CLIENTE_BASE", "NAO INFORMADO"),
        ("STATUS_BASE", ""),
        ("GANHO", False),
        ("VGV", 0.0),
    ]:
        if col not in eventos_credito.columns:
            eventos_credito[col] = default
        eventos_credito[col] = eventos_credito[col].fillna(default)

    eventos_credito["DIA"] = eventos_credito["DATA_EVENTO"]
    eventos_credito["DATA_BASE"] = pd.to_datetime(eventos_credito["DIA"], errors="coerce").dt.to_period("M").dt.to_timestamp().dt.date
    eventos_credito["DATA_BASE_LABEL"] = month_label(eventos_credito["DIA"])
    eventos_credito["ETAPA"] = eventos_credito["ETAPA_EVENTO"]
    eventos_credito["TEM_1_ANALISE"] = eventos_credito["ETAPA_EVENTO"].eq("NOVA ANALISE")
    eventos_credito["DATA_1_ANALISE"] = eventos_credito["DATA_EVENTO"].where(eventos_credito["TEM_1_ANALISE"])
    eventos_credito["CPF_CLIENTE_BASE"] = ""
    eventos_credito["CHAVE_CLIENTE"] = [
        client_count_key(nome, lead_id)
        for nome, lead_id in zip(eventos_credito["NOME_CLIENTE_BASE"], eventos_credito["ID_LEAD"])
    ]
    eventos_credito["ORIGEM_REGISTRO"] = "ATIVIDADE"

    if base.empty:
        return eventos_credito[
            [
                "ID_LEAD",
                "DIA",
                "DATA_BASE",
                "DATA_BASE_LABEL",
                "CORRETOR",
                "EQUIPE",
                "FUNIL",
                "ETAPA",
                "GANHO",
                "STATUS_BASE",
                "DATA_1_ANALISE",
                "TEM_1_ANALISE",
                "NOME_CLIENTE_BASE",
                "CPF_CLIENTE_BASE",
                "VGV",
                "CHAVE_CLIENTE",
                "DATA_EVENTO",
                "ETAPA_EVENTO",
                "TIPO_EVENTO",
                "ORIGEM_REGISTRO",
            ]
        ].copy()

    base["ORIGEM_REGISTRO"] = "LEAD"
    for col in eventos_credito.columns:
        if col not in base.columns:
            base[col] = pd.NA
    for col in base.columns:
        if col not in eventos_credito.columns:
            eventos_credito[col] = pd.NA
    return pd.concat([base, eventos_credito[base.columns]], ignore_index=True)


def carregar_base_comercial(
    fonte: str = "piperun",
    max_pages: int = 5,
    per_page: int = 100,
    data_ini: date | None = None,
    data_fim: date | None = None,
) -> pd.DataFrame:
    if fonte == "piperun":
        return carregar_piperun(max_pages=max_pages, per_page=per_page, data_ini=data_ini, data_fim=data_fim)
    raise ValueError(f"Fonte de dados nao suportada: {fonte}")


def aplicar_perfil_corretor(df: pd.DataFrame, perfil: str, nome_usuario: str) -> pd.DataFrame:
    if perfil == "corretor" and "CORRETOR" in df.columns:
        return df[df["CORRETOR"] == str(nome_usuario or "").upper().strip()].copy()
    return df.copy()
