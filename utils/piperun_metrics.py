            deals["equipe"] = mapped.fillna(deals["equipe"]).replace("", "SEM EQUIPE")

        if "stage_id" in deals_raw.columns and stage_name:
            mapped = deals_raw["stage_id"].astype(str).str.strip().map(stage_name)
            deals["etapa"] = mapped.fillna(deals["etapa"])

        if corretor_equipe:
            mapped = deals["responsavel"].map(corretor_equipe)
            has_team = mapped.fillna("").astype(str).str.len() > 0
            deals.loc[has_team, "equipe"] = mapped[has_team]

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
            mapped = actions_raw["user_name"].apply(normalize_text)
            has_user_name = mapped.astype(str).str.len() > 0
            actions.loc[has_user_name, "responsavel"] = mapped[has_user_name]

        if corretor_equipe:
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
