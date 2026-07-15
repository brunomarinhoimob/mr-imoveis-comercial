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
    pipeline: str = ""
    stage: str = ""
    last_action_at: str = ""
    action_type: str = ""
    action_owner: str = ""
    action_date: str = ""
    action_deal_id: str = ""
    previous_owner: str = ""


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

    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]

    return text


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
        pipeline=first_existing(cols, ["pipeline.name", "pipeline", "funil", "pipeline_id"]),
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
        action_type=first_existing(cols, ["activity_type_id", "activity_type.name", "activity_type", "nome_tipo", "tipo", "kind", "category", "type"]),
        action_date=first_existing(cols, ["done_at", "date", "data", "created_at", "scheduled_at", "data_realizacao"]),
        action_deal_id=first_existing(cols, ["deal_id", "deal.id", "card_id", "lead_id", "opportunity_id"]),
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
        key = normalize_id(row[id_col])
        value = normalize_text(row[name_col])
        if key and value:
            lookup[key] = value

    return lookup


def build_reference_maps(
    users_raw: pd.DataFrame | None = None,
    stages_raw: pd.DataFrame | None = None,
    pipelines_raw: pd.DataFrame | None = None,
    activity_types_raw: pd.DataFrame | None = None,
    corretor_equipe_map: Dict[str, str] | None = None,
    corretor_nome_map: Dict[str, str] | None = None,
) -> Dict[str, Dict[str, str]]:
    users = users_raw if users_raw is not None else pd.DataFrame()
    stages = stages_raw if stages_raw is not None else pd.DataFrame()
    pipelines = pipelines_raw if pipelines_raw is not None else pd.DataFrame()
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
    pipeline_name = make_lookup(
        pipelines,
        ["id", "pipeline_id", "funil_id"],
        ["name", "nome", "title", "pipeline.name", "description"],
    )
    activity_type_name = make_lookup(
        activity_types,
        ["id", "activity_type_id", "type_id"],
        ["name", "nome", "title", "type", "description"],
    )

    return {
        "user_name": user_name,
        "user_team": user_team,
        "corretor_equipe": corretor_equipe_map or {},
        "corretor_nome": corretor_nome_map or {},
        "stage_name": stage_name,
        "pipeline_name": pipeline_name,
        "activity_type_name": activity_type_name,
    }


def canonical_responsavel(value, corretor_nome: Dict[str, str]) -> str:
    text = normalize_text(value)
    if not text:
        return "SEM RESPONSAVEL"

    if text in corretor_nome:
        return corretor_nome[text]

    email_prefix = text.split("@", 1)[0]
    compact = "".join(ch for ch in email_prefix if ch.isalpha())
    for alias, nome in corretor_nome.items():
        if len(alias) >= 4 and alias in compact:
            return nome

    return text


def classify_action_type(tipo, descricao) -> str:
    tipo_text = normalize_text(tipo)
    desc_text = normalize_text(descricao)
    combined = f"{tipo_text} {desc_text}".strip()

    if (
        ("OPORTUNIDADE" in combined and "COPIA" in combined)
        or "DUPLICAD" in combined
        or ("ORIGINAL" in combined and "RECUPERACAO DE LEAD" in combined)
    ):
        return "LEAD REMANEJADO"
    if "ANALISE" in combined and "CONFIRM" in combined and (
        "1" in combined or "PRIMEIRA" in combined or "1A" in combined
    ):
        return "1 ANALISE CONFIRMADA"
    if "ANALISE" in combined and ("ENVIADO" in combined or "ENVIADA" in combined):
        return "1 ANALISE ENVIADA"
    if "ANALISE" in combined and ("1" in combined or "PRIMEIRA" in combined or "1A" in combined):
        return "1 ANALISE"
    if "ANALISE" in combined and "CREDITO" in combined and "CONFIRM" in combined:
        return "ANALISE CREDITO CONFIRMADA"
    if "ANALISE" in combined and "CREDITO" in combined:
        return "ANALISE DE CREDITO"
    if "APROVAD" in combined:
        return "APROVADO"
    if "VISITA" in combined:
        return "VISITA"
    if "WHATS" in combined:
        return "MENSAGEM WHATSAPP"
    if "LIGACAO" in combined or "LIGA" in combined:
        return "LIGACAO"

    return tipo_text or "ACAO"


def prepare_deals(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    cmap = infer_deal_columns(df)
    out = pd.DataFrame(index=df.index)
    out["lead_id"] = df[cmap.id].astype(str) if cmap.id else df.index.astype(str)
    out["lead"] = df[cmap.title].astype(str) if cmap.title else ""
    out["created_at"] = pd.to_datetime(df[cmap.created_at], errors="coerce") if cmap.created_at else pd.NaT
    out["responsavel"] = df[cmap.owner].apply(normalize_text) if cmap.owner else "SEM RESPONSAVEL"
    out["responsavel_id"] = df[cmap.owner_id].apply(normalize_id) if cmap.owner_id else ""
    out["equipe"] = df[cmap.team].apply(normalize_text) if cmap.team else "SEM EQUIPE"
    out["pipeline"] = df[cmap.pipeline].apply(normalize_text) if cmap.pipeline else ""
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
    out["lead_id"] = df[cmap.action_deal_id].apply(normalize_id) if cmap.action_deal_id else out["acao_id"]
    text_cols = [
        col
        for col in df.columns
        if any(key in str(col).lower() for key in ["title", "description", "comment", "text", "note", "content", "message"])
    ]
    if text_cols:
        out["descricao"] = df[text_cols].fillna("").astype(str).agg(" ".join, axis=1).str.strip()
    else:
        out["descricao"] = df[cmap.title].astype(str) if cmap.title else ""
    out["responsavel"] = df[cmap.owner].apply(normalize_text) if cmap.owner else "SEM RESPONSAVEL"
    out["responsavel_id"] = df[cmap.owner_id].apply(normalize_id) if cmap.owner_id else ""
    out["equipe"] = df[cmap.team].apply(normalize_text) if cmap.team else "SEM EQUIPE"
    out["tipo_acao"] = df[cmap.action_type].apply(normalize_text) if cmap.action_type else "ACAO"
    out["data_acao"] = pd.to_datetime(df[cmap.action_date], errors="coerce") if cmap.action_date else pd.NaT

    out["tipo_acao"] = [
        classify_action_type(tipo, descricao)
        for tipo, descricao in zip(out["tipo_acao"], out["descricao"])
    ]
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
    corretor_equipe = refs.get("corretor_equipe", {})
    corretor_nome = refs.get("corretor_nome", {})
    stage_name = refs.get("stage_name", {})
    pipeline_name = refs.get("pipeline_name", {})
    activity_type_name = refs.get("activity_type_name", {})

    if not deals.empty:
        if "owner_id" in deals_raw.columns and user_name:
            mapped = deals_raw["owner_id"].apply(normalize_id).map(user_name)
            deals["responsavel"] = mapped.fillna(deals["responsavel"]).replace("", "SEM RESPONSAVEL")

        if "owner_id" in deals_raw.columns and user_team:
            mapped = deals_raw["owner_id"].apply(normalize_id).map(user_team)
            deals["equipe"] = mapped.fillna(deals["equipe"]).replace("", "SEM EQUIPE")

        if "stage_id" in deals_raw.columns and stage_name:
            mapped = deals_raw["stage_id"].apply(normalize_id).map(stage_name)
            deals["etapa"] = mapped.fillna(deals["etapa"])

        if "pipeline_id" in deals_raw.columns and pipeline_name:
            mapped = deals_raw["pipeline_id"].apply(normalize_id).map(pipeline_name)
            deals["pipeline"] = mapped.fillna(deals["pipeline"])

        if corretor_equipe:
            if corretor_nome:
                deals["responsavel"] = deals["responsavel"].apply(lambda value: canonical_responsavel(value, corretor_nome))
            mapped = deals["responsavel"].map(corretor_equipe)
            has_team = mapped.fillna("").astype(str).str.len() > 0
            deals.loc[has_team, "equipe"] = mapped[has_team]

    if not actions.empty:
        deal_owner = {}
        deal_team = {}
        if not deals.empty:
            deal_owner = deals.set_index("lead_id")["responsavel"].to_dict()
            deal_team = deals.set_index("lead_id")["equipe"].to_dict()

        if "deal_id" in actions_raw.columns and deal_owner:
            deal_ids = actions_raw["deal_id"].apply(normalize_id)
            actions["lead_id"] = deal_ids
            mapped_owner = deal_ids.map(deal_owner)
            has_owner_from_deal = mapped_owner.fillna("").astype(str).str.len() > 0
            actions.loc[has_owner_from_deal, "responsavel"] = mapped_owner[has_owner_from_deal]

            mapped_team = deal_ids.map(deal_team)
            has_team_from_deal = mapped_team.fillna("").astype(str).str.len() > 0
            actions.loc[has_team_from_deal, "equipe"] = mapped_team[has_team_from_deal]

        owner_source = "owner_id" if "owner_id" in actions_raw.columns else "user_id" if "user_id" in actions_raw.columns else ""
        if owner_source and user_name:
            mapped = actions_raw[owner_source].apply(normalize_id).map(user_name)
            has_owner = mapped.fillna("").astype(str).str.len() > 0
            missing_owner = actions["responsavel"].fillna("").astype(str).isin(["", "SEM RESPONSAVEL"])
            actions.loc[has_owner & missing_owner, "responsavel"] = mapped[has_owner & missing_owner]

        if owner_source and user_team:
            mapped = actions_raw[owner_source].apply(normalize_id).map(user_team)
            has_team = mapped.fillna("").astype(str).str.len() > 0
            missing_team = actions["equipe"].fillna("").astype(str).isin(["", "SEM EQUIPE"])
            actions.loc[has_team & missing_team, "equipe"] = mapped[has_team & missing_team]

        if "activity_type_id" in actions_raw.columns and activity_type_name:
            mapped = actions_raw["activity_type_id"].apply(normalize_id).map(activity_type_name)
            actions["tipo_acao"] = mapped.fillna(actions["tipo_acao"]).replace("", "ACAO")
            actions["tipo_acao"] = [
                classify_action_type(tipo, descricao)
                for tipo, descricao in zip(actions["tipo_acao"], actions["descricao"])
            ]

        if "user_name" in actions_raw.columns:
            mapped = actions_raw["user_name"].apply(normalize_text)
            has_user_name = mapped.astype(str).str.len() > 0
            actions.loc[has_user_name, "responsavel"] = mapped[has_user_name]

        if owner_source:
            missing_owner = actions["responsavel"].fillna("").astype(str).isin(["", "SEM RESPONSAVEL"])
            fallback_owner = actions_raw[owner_source].apply(normalize_id)
            actions.loc[missing_owner, "responsavel"] = "ID " + fallback_owner[missing_owner]

        if corretor_equipe:
            if corretor_nome:
                actions["responsavel"] = actions["responsavel"].apply(lambda value: canonical_responsavel(value, corretor_nome))
            mapped = actions["responsavel"].map(corretor_equipe)
            has_team = mapped.fillna("").astype(str).str.len() > 0
            actions.loc[has_team, "equipe"] = mapped[has_team]

    return deals, actions


def contains_stage(series: pd.Series, words: Iterable[str]) -> pd.Series:
    text = series.fillna("").astype(str).map(normalize_text)
    mask = pd.Series(False, index=series.index)
    for word in words:
        mask = mask | text.str.contains(normalize_text(word), na=False)
    return mask


def exclude_financeiro(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "pipeline" not in df.columns:
        return df

    mask = ~df["pipeline"].fillna("").astype(str).map(normalize_text).str.contains("FINANCEIRO", na=False)
    return df[mask].copy()


def build_stage_metrics(deals_df: pd.DataFrame, dims: List[str]) -> pd.DataFrame:
    if deals_df.empty:
        return pd.DataFrame(columns=dims)

    tmp = deals_df.copy()
    etapa = tmp["etapa"]
    pipeline = tmp["pipeline"]

    tmp["novo_lead"] = contains_stage(etapa, ["NOVO LEAD", "NOVA VENDA"])
    tmp["aguardando_atendimento"] = contains_stage(etapa, ["AGUARDANDO ATENDIMENTO"])
    tmp["em_atendimento"] = contains_stage(etapa, ["EM ATENDIMENTO", "ATENDIMENTO"])
    tmp["cadencia"] = contains_stage(pipeline, ["CADENCIA"]) | contains_stage(etapa, ["DIA 1", "DIA 2", "DIA 3", "DIA 4", "DIA 5"])
    tmp["recuperacao_lead"] = contains_stage(pipeline, ["RECUPERACAO DE LEAD"])
    tmp["acompanhamento"] = contains_stage(etapa, ["ACOMPANHAMENTO"])
    tmp["visita_agendada"] = contains_stage(etapa, ["VISITA AGENDADA"])
    tmp["visita_realizada"] = contains_stage(etapa, ["VISITA REALIZADA"])
    tmp["aguardando_documentos"] = contains_stage(etapa, ["AGUARDANDO DOCUMENTOS"])
    tmp["recusa_pasteiro"] = contains_stage(etapa, ["RECUSA PASTEIRO"])
    tmp["analises_enviadas"] = contains_stage(etapa, ["ANALISE DE CREDITO", "1 ANALISE", "1A ANALISE", "NOVA ANALISE"])
    tmp["conferencia_pasteiro"] = contains_stage(etapa, ["CONFERENCIA DO PASTEIRO"])
    tmp["pendencias"] = contains_stage(etapa, ["DOC PENDENTE", "PENDENCIA", "PENDENTE"])
    tmp["condicionados"] = contains_stage(etapa, ["CONDICIONADO"])
    tmp["restricoes"] = contains_stage(etapa, ["RESTRICAO"])
    tmp["aprovacoes"] = contains_stage(etapa, ["APROVADO", "APROVACAO"])
    tmp["reprovados"] = contains_stage(etapa, ["REPROVADO", "REPROVACAO", "RECUSADO", "RECUSADA"])

    stage_cols = [
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

    return tmp.groupby(dims).agg(**{col: (col, "sum") for col in stage_cols}).reset_index()


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
    deals_funil = exclude_financeiro(deals)

    if not deals.empty:
        deals_periodo = deals[
            deals["created_at"].isna()
            | ((deals["created_at"].dt.date >= data_ini) & (deals["created_at"].dt.date <= data_fim))
        ].copy()
    else:
        deals_periodo = deals

    deals_periodo = exclude_financeiro(deals_periodo)

    if not actions.empty:
        actions_periodo = actions[
            actions["data_acao"].isna()
            | ((actions["data_acao"].dt.date >= data_ini) & (actions["data_acao"].dt.date <= data_fim))
        ].copy()
    else:
        actions_periodo = actions

    dims = ["equipe", "responsavel"]
    if deals_funil.empty:
        base = pd.DataFrame(columns=dims)
    else:
        base = deals_funil[dims].drop_duplicates()

    if not actions_periodo.empty:
        base = pd.concat([base, actions_periodo[dims].drop_duplicates()], ignore_index=True).drop_duplicates()

    if base.empty:
        base = pd.DataFrame([{"equipe": "SEM EQUIPE", "responsavel": "SEM RESPONSAVEL"}])

    leads = (
        deals_periodo.groupby(dims)["lead_id"].nunique().reset_index(name="leads_recebidos")
        if not deals_periodo.empty
        else pd.DataFrame(columns=dims + ["leads_recebidos"])
    )

    cards_total = (
        deals_funil.groupby(dims)["lead_id"].nunique().reset_index(name="cards_total")
        if not deals_funil.empty
        else pd.DataFrame(columns=dims + ["cards_total"])
    )

    acoes = (
        actions_periodo.groupby(dims)["acao_id"].nunique().reset_index(name="acoes_total")
        if not actions_periodo.empty
        else pd.DataFrame(columns=dims + ["acoes_total"])
    )

    leads_com_atividade = (
        actions_periodo.groupby(dims)["lead_id"].nunique().reset_index(name="leads_com_atividade")
        if not actions_periodo.empty
        else pd.DataFrame(columns=dims + ["leads_com_atividade"])
    )

    analise_enviada_atividade = pd.DataFrame(columns=dims + ["analise_enviada_atividade"])
    if not actions_periodo.empty:
        tipo_normalizado = actions_periodo["tipo_acao"].fillna("").astype(str).map(normalize_text)
        texto_atividade = (
            actions_periodo["tipo_acao"].fillna("").astype(str)
            + " "
            + actions_periodo["descricao"].fillna("").astype(str)
        ).map(normalize_text)
        mask_analise_enviada = tipo_normalizado.isin(
            [
                "1 ANALISE",
                "1 ANALISE ENVIADA",
                "1 ANALISE CONFIRMADA",
                "ANALISE DE CREDITO",
                "ANALISE CREDITO CONFIRMADA",
            ]
        ) | (
            texto_atividade.str.contains("ANALISE", na=False)
            & (
                texto_atividade.str.contains("ENVIADO", na=False)
                | texto_atividade.str.contains("ENVIADA", na=False)
                | texto_atividade.str.contains("CREDITO", na=False)
                | texto_atividade.str.contains("1", na=False)
                | texto_atividade.str.contains("PRIMEIRA", na=False)
            )
        )
        analise_enviada_atividade = (
            actions_periodo[mask_analise_enviada]
            .groupby(dims)["lead_id"]
            .nunique()
            .reset_index(name="analise_enviada_atividade")
        )

    tipos = pd.DataFrame(columns=dims)
    if not actions_periodo.empty:
        tipos = (
            actions_periodo.assign(tipo_acao=actions_periodo["tipo_acao"].replace("", "ACAO"))
            .pivot_table(index=dims, columns="tipo_acao", values="lead_id", aggfunc="nunique", fill_value=0)
            .reset_index()
        )
        tipos.columns = [str(c).lower().replace(" ", "_") if c not in dims else c for c in tipos.columns]

    funil = pd.DataFrame(columns=dims)
    if not deals_periodo.empty and False:
        tmp = deals_periodo.copy()
        tmp["analises_enviadas"] = contains_stage(
            tmp["etapa"],
            ["ANALISE DE CREDITO", "ANALISE", "1 ANALISE", "1A ANALISE", "1ª ANALISE"],
        )
        tmp["aprovacoes"] = contains_stage(
            tmp["etapa"],
            ["APROVACAO", "APROVADO", "APROVADA"],
        )
        tmp["reprovados"] = contains_stage(
            tmp["etapa"],
            ["REPROVADO", "REPROVACAO", "RECUSA", "RECUSADO", "RECUSADA"],
        )
        tmp["pendencias"] = contains_stage(
            tmp["etapa"],
            ["PENDENCIA", "PENDENTE"],
        )
        tmp["em_cadencia"] = contains_stage(
            tmp["etapa"],
            ["CADENCIA", "CADÊNCIA"],
        )
        tmp["em_acompanhamento"] = contains_stage(
            tmp["etapa"],
            ["ACOMPANHAMENTO", "ACOMPANHAR"],
        )
        tmp["em_atendimento"] = contains_stage(
            tmp["etapa"],
            ["ATENDIMENTO", "ATENDENDO", "EM ATENDIMENTO"],
        )
        funil = tmp.groupby(dims).agg(
            analises_enviadas=("analises_enviadas", "sum"),
            aprovacoes=("aprovacoes", "sum"),
            reprovados=("reprovados", "sum"),
            pendencias=("pendencias", "sum"),
            em_cadencia=("em_cadencia", "sum"),
            em_acompanhamento=("em_acompanhamento", "sum"),
            em_atendimento=("em_atendimento", "sum"),
        ).reset_index()

    funil = build_stage_metrics(deals_funil, dims)

    cards_por_coluna = pd.DataFrame()
    if not deals_funil.empty:
        cards_por_coluna = (
            deals_funil.assign(etapa=deals_funil["etapa"].replace("", "SEM ETAPA"))
            .groupby(["pipeline", "etapa"], as_index=False)["lead_id"]
            .nunique()
            .rename(columns={"lead_id": "qtde_cards"})
            .sort_values(["pipeline", "qtde_cards"], ascending=[True, False])
        )

    remanejados_deal = pd.DataFrame(columns=dims + ["lead_id"])
    if not deals_funil.empty:
        tmp = deals_funil.copy()
        tmp["remanejado"] = tmp["responsavel_anterior"].fillna("").astype(str).str.len() > 0
        if tmp["remanejado"].any():
            remanejados_deal = tmp.loc[tmp["remanejado"], dims + ["lead_id"]].drop_duplicates()

    remanejados_atividade = pd.DataFrame(columns=dims + ["lead_id"])
    if not actions_periodo.empty:
        texto_atividade = (
            actions_periodo["tipo_acao"].fillna("").astype(str)
            + " "
            + actions_periodo["descricao"].fillna("").astype(str)
        ).map(normalize_text)
        mask_remanejo = (actions_periodo["tipo_acao"].fillna("").astype(str).map(normalize_text) == "LEAD REMANEJADO") | (
            (texto_atividade.str.contains("OPORTUNIDADE", na=False) & texto_atividade.str.contains("COPIA", na=False))
            | texto_atividade.str.contains("DUPLICAD", na=False)
            | (texto_atividade.str.contains("ORIGINAL", na=False) & texto_atividade.str.contains("RECUPERACAO DE LEAD", na=False))
        )
        remanejados_atividade = actions_periodo.loc[mask_remanejo, dims + ["lead_id"]].drop_duplicates()

    remanejados = pd.concat([remanejados_deal, remanejados_atividade], ignore_index=True)
    if not remanejados.empty:
        remanejados = remanejados.drop_duplicates(dims + ["lead_id"])
        remanejados = remanejados.groupby(dims)["lead_id"].nunique().reset_index(name="leads_remanejados")

    result = base.merge(leads, on=dims, how="left")
    result = result.merge(cards_total, on=dims, how="left")
    result = result.merge(remanejados, on=dims, how="left")
    result = result.merge(acoes, on=dims, how="left")
    result = result.merge(leads_com_atividade, on=dims, how="left")
    result = result.merge(analise_enviada_atividade, on=dims, how="left")
    result = result.merge(funil, on=dims, how="left")
    if not tipos.empty:
        result = result.merge(tipos, on=dims, how="left")

    metric_cols = [c for c in result.columns if c not in dims]
    result[metric_cols] = result[metric_cols].fillna(0)

    if "analise_enviada_atividade" in result.columns:
        if "analises_enviadas" not in result.columns:
            result["analises_enviadas"] = 0
        result["analises_enviadas"] = result[["analises_enviadas", "analise_enviada_atividade"]].max(axis=1)

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
        "deals_normalizados": deals_funil,
        "acoes_normalizadas": actions_periodo,
        "cards_por_coluna": cards_por_coluna,
    }
