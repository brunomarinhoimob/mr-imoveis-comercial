from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import pandas as pd


@dataclass
class PiperunColumnMap:
    id: str = ""
    title: str = ""
    created_at: str = ""
    owner: str = ""
    owner_id: str = ""
    team: str = ""
    stage: str = ""
    last_action_at: str = ""
    action_type: str = ""
    action_owner: str = ""
    action_date: str = ""
    previous_owner: str = ""


def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().upper()
    text = unicodedata.normalize("NFKD", text).encode("ascii", errors="ignore").decode("ascii")
    return " ".join(text.split())


def first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str:
    available = {str(c).lower(): c for c in columns}
    normalized = {normalize_text(c).replace(" ", "_").lower(): c for c in columns}

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


def infer_deal_columns(df: pd.DataFrame) -> PiperunColumnMap:
    cols = df.columns
    return PiperunColumnMap(
        id=first_existing(cols, ["id", "deal_id", "opportunity_id", "card_id"]),
        title=first_existing(cols, ["title", "name", "nome", "deal_title", "person.name", "customer.name"]),
        created_at=first_existing(cols, ["created_at", "created", "data_criacao", "data_captura", "createdAt"]),
        owner=first_existing(cols, ["owner.name", "user.name", "responsible.name", "responsavel", "owner", "nome_corretor", "user_name"]),
        owner_id=first_existing(cols, ["owner.id", "user.id", "responsible.id", "owner_id", "user_id", "id_usuario"]),
        team=first_existing(cols, ["team.name", "team", "equipe", "company_team.name", "pipeline.name"]),
        stage=first_existing(cols, ["stage.name", "stage", "step.name", "status.name", "column.name", "etapa", "coluna", "pipeline_stage.name"]),
        last_action_at=first_existing(cols, ["last_activity_at", "last_action_at", "updated_at", "data_ultima_interacao", "last_note_at"]),
        previous_owner=first_existing(cols, ["previous_owner.name", "old_owner.name", "from_user.name", "usuario_anterior", "responsavel_anterior"]),
    )


def infer_action_columns(df: pd.DataFrame) -> PiperunColumnMap:
    cols = df.columns
    return PiperunColumnMap(
        id=first_existing(cols, ["id", "activity_id", "note_id"]),
        title=first_existing(cols, ["title", "description", "note", "text", "content", "name", "nome"]),
        created_at=first_existing(cols, ["created_at", "created", "data_criacao"]),
        owner=first_existing(cols, ["owner.name", "user.name", "responsible.name", "responsavel", "owner", "nome_usuario", "user_name"]),
        owner_id=first_existing(cols, ["owner.id", "user.id", "responsible.id", "owner_id", "user_id", "id_usuario"]),
        team=first_existing(cols, ["team.name", "team", "equipe"]),
        action_type=first_existing(cols, ["type", "activity_type", "tipo", "kind", "category", "nome_tipo", "activity_type.name"]),
        action_date=first_existing(cols, ["done_at", "date", "data", "created_at", "scheduled_at", "data_realizacao"]),
    )


def make_lookup(df: pd.DataFrame, id_candidates: Iterable[str], name_candidates: Iterable[str]) -> Dict[str, str]:
    if df is None or df.empty:
        return {}

    id_col = first_existing(df.columns, id_candidates)
    name_col = first_existing(df.columns, name_candidates)

    if not id_col or not name_col:
        return {}

    lookup = {}
    for _, row in df[[id_col, name_col]].dropna(subset=[id_col]).iterrows():
        key = str(row[id_col]).strip()
        value = normalize_text(row[name_col])
        if key and value:
            lookup[key] = value

    return lookup


def build_reference_maps(
    users_raw: pd.DataFrame | None = None,
    stages_raw: pd.DataFrame | None = None,
    activity_types_raw: pd.DataFrame | None = None,
) -> Dict[str, Dict[str, str]]:
    users = users_raw if users_raw is not None else pd.DataFrame()
    stages = stages_raw if stages_raw is not None else pd.DataFrame()
    activity_types = activity_types_raw if activity_types_raw is not None else pd.DataFrame()

    user_name = make_lookup(
        users,
        ["id", "user_id", "owner_id"],
        ["name", "nome", "user.name", "owner.name", "email"],
    )
    user_team = make_lookup(
        users,
        ["id", "user_id", "owner_id"],
        ["team.name", "team", "equipe", "group.name", "department.name"],
    )
    stage_name = make_lookup(
        stages,
        ["id", "stage_id", "pipeline_stage_id"],
        ["name", "nome", "title", "stage.name", "description"],
    )
    activity_type_name = make_lookup(
        activity_types,
        ["id", "activity_type_id", "type_id"],
        ["name", "nome", "title", "type", "description"],
    )

    return {
        "user_name": user_name,
        "user_team": user_team,
        "stage_name": stage_name,
        "activity_type_name": activity_type_name,
    }


def prepare_deals(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    cmap = infer_deal_columns(df)
    out = pd.DataFrame(index=df.index)
    out["lead_id"] = df[cmap.id].astype(str) if cmap.id else df.index.astype(str)
    out["lead"] = df[cmap.title].astype(str) if cmap.title else ""
    out["created_at"] = pd.to_datetime(df[cmap.created_at], errors="coerce") if cmap.created_at else pd.NaT
    out["responsavel"] = df[cmap.owner].apply(normalize_text) if cmap.owner else "SEM RESPONSAVEL"
    out["responsavel_id"] = df[cmap.owner_id].astype(str) if cmap.owner_id else ""
    out["equipe"] = df[cmap.team].apply(normalize_text) if cmap.team else "SEM EQUIPE"
    out["etapa"] = df[cmap.stage].apply(normalize_text) if cmap.stage else ""
    out["last_action_at"] = pd.to_datetime(df[cmap.last_action_at], errors="coerce") if cmap.last_action_at else pd.NaT
    out["responsavel_anterior"] = df[cmap.previous_owner].apply(normalize_text) if cmap.previous_owner else ""

    return out


def prepare_actions(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    cmap = infer_action_columns(df)
    out = pd.DataFrame(index=df.index)
    out["acao_id"] = df[cmap.id].astype(str) if cmap.id else df.index.astype(str)
    out["descricao"] = df[cmap.title].astype(str) if cmap.title else ""
    out["responsavel"] = df[cmap.owner].apply(normalize_text) if cmap.owner else "SEM RESPONSAVEL"
    out["responsavel_id"] = df[cmap.owner_id].astype(str) if cmap.owner_id else ""
    out["equipe"] = df[cmap.team].apply(normalize_text) if cmap.team else "SEM EQUIPE"
    out["tipo_acao"] = df[cmap.action_type].apply(normalize_text) if cmap.action_type else "ACAO"
    out["data_acao"] = pd.to_datetime(df[cmap.action_date], errors="coerce") if cmap.action_date else pd.NaT

    out.loc[out["tipo_acao"].eq(""), "tipo_acao"] = "ACAO"
    return out


def enrich_with_references(
    deals: pd.DataFrame,
    actions: pd.DataFrame,
    deals_raw: pd.DataFrame,
    actions_raw: pd.DataFrame,
    reference_maps: Dict[str, Dict[str, str]] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    refs = reference_maps or {}
    user_name = refs.get("user_name", {})
    user_team = refs.get("user_team", {})
    stage_name = refs.get("stage_name", {})
    activity_type_name = refs.get("activity_type_name", {})

    if not deals.empty:
        if "owner_id" in deals_raw.columns and user_name:
            mapped = deals_raw["owner_id"].astype(str).str.strip().map(user_name)
            deals["responsavel"] = mapped.fillna(deals["responsavel"]).replace("", "SEM RESPONSAVEL")

        if "owner_id" in deals_raw.columns and user_team:
            mapped = deals_raw["owner_id"].astype(str).str.strip().map(user_team)
            deals["equipe"] = mapped.fillna(deals["equipe"]).replace("", "SEM EQUIPE")

        if "stage_id" in deals_raw.columns and stage_name:
            mapped = deals_raw["stage_id"].astype(str).str.strip().map(stage_name)
            deals["etapa"] = mapped.fillna(deals["etapa"])

    if not actions.empty:
        owner_source = "owner_id" if "owner_id" in actions_raw.columns else "user_id" if "user_id" in actions_raw.columns else ""
        if owner_source and user_name:
            mapped = actions_raw[owner_source].astype(str).str.strip().map(user_name)
            actions["responsavel"] = mapped.fillna(actions["responsavel"]).replace("", "SEM RESPONSAVEL")

        if owner_source and user_team:
            mapped = actions_raw[owner_source].astype(str).str.strip().map(user_team)
            actions["equipe"] = mapped.fillna(actions["equipe"]).replace("", "SEM EQUIPE")

        if "activity_type_id" in actions_raw.columns and activity_type_name:
            mapped = actions_raw["activity_type_id"].astype(str).str.strip().map(activity_type_name)
            actions["tipo_acao"] = mapped.fillna(actions["tipo_acao"]).replace("", "ACAO")

        if "user_name" in actions_raw.columns:
            actions["responsavel"] = actions_raw["user_name"].apply(normalize_text).replace("", actions["responsavel"])

    return deals, actions


def contains_stage(series: pd.Series, words: Iterable[str]) -> pd.Series:
    text = series.fillna("").astype(str).map(normalize_text)
    mask = pd.Series(False, index=series.index)
    for word in words:
        mask = mask | text.str.contains(normalize_text(word), na=False)
    return mask


def build_performance(
    deals_raw: pd.DataFrame,
    actions_raw: pd.DataFrame,
    data_ini,
    data_fim,
    remanejo_dias: int = 2,
    reference_maps: Dict[str, Dict[str, str]] | None = None,
) -> Dict[str, pd.DataFrame]:
    deals = prepare_deals(deals_raw)
    actions = prepare_actions(actions_raw)
    deals, actions = enrich_with_references(deals, actions, deals_raw, actions_raw, reference_maps)

    if not deals.empty:
        deals_periodo = deals[
            deals["created_at"].isna()
            | ((deals["created_at"].dt.date >= data_ini) & (deals["created_at"].dt.date <= data_fim))
        ].copy()
    else:
        deals_periodo = deals

    if not actions.empty:
        actions_periodo = actions[
            actions["data_acao"].isna()
            | ((actions["data_acao"].dt.date >= data_ini) & (actions["data_acao"].dt.date <= data_fim))
        ].copy()
    else:
        actions_periodo = actions

    dims = ["equipe", "responsavel"]
    if deals_periodo.empty:
        base = pd.DataFrame(columns=dims)
    else:
        base = deals_periodo[dims].drop_duplicates()

    if not actions_periodo.empty:
        base = pd.concat([base, actions_periodo[dims].drop_duplicates()], ignore_index=True).drop_duplicates()

    if base.empty:
        base = pd.DataFrame([{"equipe": "SEM EQUIPE", "responsavel": "SEM RESPONSAVEL"}])

    leads = (
        deals_periodo.groupby(dims)["lead_id"].nunique().reset_index(name="leads_recebidos")
        if not deals_periodo.empty
        else pd.DataFrame(columns=dims + ["leads_recebidos"])
    )

    acoes = (
        actions_periodo.groupby(dims)["acao_id"].nunique().reset_index(name="acoes_total")
        if not actions_periodo.empty
        else pd.DataFrame(columns=dims + ["acoes_total"])
    )

    tipos = pd.DataFrame(columns=dims)
    if not actions_periodo.empty:
        tipos = (
            actions_periodo.assign(tipo_acao=actions_periodo["tipo_acao"].replace("", "ACAO"))
            .pivot_table(index=dims, columns="tipo_acao", values="acao_id", aggfunc="nunique", fill_value=0)
            .reset_index()
        )
        tipos.columns = [str(c).lower().replace(" ", "_") if c not in dims else c for c in tipos.columns]

    funil = pd.DataFrame(columns=dims)
    if not deals_periodo.empty:
        tmp = deals_periodo.copy()
        tmp["analises_enviadas"] = contains_stage(tmp["etapa"], ["ANALISE DE CREDITO", "ANALISE"])
        tmp["aprovacoes"] = contains_stage(tmp["etapa"], ["APROVACAO", "APROVADO"])
        tmp["reprovados"] = contains_stage(tmp["etapa"], ["REPROVADO", "REPROVACAO"])
        funil = tmp.groupby(dims).agg(
            analises_enviadas=("analises_enviadas", "sum"),
            aprovacoes=("aprovacoes", "sum"),
            reprovados=("reprovados", "sum"),
        ).reset_index()

    remanejados = pd.DataFrame(columns=dims + ["leads_remanejados"])
    if not deals_periodo.empty:
        tmp = deals_periodo.copy()
        tmp["remanejado"] = tmp["responsavel_anterior"].fillna("").astype(str).str.len() > 0
        if tmp["remanejado"].any():
            remanejados = tmp[tmp["remanejado"]].groupby(dims)["lead_id"].nunique().reset_index(name="leads_remanejados")
        elif "last_action_at" in tmp.columns:
            sem_acao = tmp["last_action_at"].isna()
            remanejados = tmp[sem_acao].groupby(dims)["lead_id"].nunique().reset_index(name="leads_remanejados")

    result = base.merge(leads, on=dims, how="left")
    result = result.merge(remanejados, on=dims, how="left")
    result = result.merge(acoes, on=dims, how="left")
    result = result.merge(funil, on=dims, how="left")
    if not tipos.empty:
        result = result.merge(tipos, on=dims, how="left")

    metric_cols = [c for c in result.columns if c not in dims]
    result[metric_cols] = result[metric_cols].fillna(0)

    for col in metric_cols:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).astype(int)

    equipe = result.groupby("equipe", as_index=False)[metric_cols].sum()
    geral = pd.DataFrame([{col: int(result[col].sum()) for col in metric_cols}])
    geral.insert(0, "visao", "GERAL")

    result = result.sort_values(["equipe", "responsavel"]).reset_index(drop=True)
    equipe = equipe.sort_values("equipe").reset_index(drop=True)

    return {
        "geral": geral,
        "equipe": equipe,
        "corretor": result,
        "deals_normalizados": deals_periodo,
        "acoes_normalizadas": actions_periodo,
    }
