import pandas as pd


def status_final_por_cliente(df: pd.DataFrame) -> pd.Series:
    if df.empty or "CHAVE_CLIENTE" not in df.columns:
        return pd.Series(dtype="object", name="STATUS_FINAL_CLIENTE")

    ordenado = df.sort_values("DIA") if "DIA" in df.columns else df.copy()
    status = ordenado.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().fillna("")
    status.name = "STATUS_FINAL_CLIENTE"
    return status


def calcular_vendas(df_filtrado: pd.DataFrame, df_completo: pd.DataFrame, filtro_vendas: str) -> dict:
    status_final = status_final_por_cliente(df_completo)
    vendas_ref = df_filtrado[df_filtrado["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"])].copy()

    vazio = {
        "venda_gerada": 0,
        "venda_informada": 0,
        "vendas_total": 0,
        "vgv_total": 0.0,
        "maior_vgv": 0.0,
        "ticket_medio": 0.0,
    }
    if vendas_ref.empty:
        return vazio

    vendas_ref = vendas_ref.merge(status_final, on="CHAVE_CLIENTE", how="left")
    vendas_ref = vendas_ref[vendas_ref["STATUS_FINAL_CLIENTE"] != "DESISTIU"]
    if vendas_ref.empty:
        return vazio

    vendas_ref = vendas_ref.sort_values("DIA")
    vendas_ult = vendas_ref.groupby("CHAVE_CLIENTE").tail(1)

    if filtro_vendas == "Somente GERADAS":
        vendas_ult = vendas_ult[vendas_ult["STATUS_BASE"] == "VENDA GERADA"].copy()

    if vendas_ult.empty:
        return vazio

    venda_gerada = int((vendas_ult["STATUS_BASE"] == "VENDA GERADA").sum())
    venda_informada = int((vendas_ult["STATUS_BASE"] == "VENDA INFORMADA").sum())
    vendas_total = venda_gerada + venda_informada
    vgv_total = float(vendas_ult["VGV"].sum())
    maior_vgv = float(vendas_ult["VGV"].max()) if vendas_total else 0.0
    ticket_medio = float(vgv_total / vendas_total) if vendas_total else 0.0

    return {
        "venda_gerada": venda_gerada,
        "venda_informada": venda_informada,
        "vendas_total": vendas_total,
        "vgv_total": vgv_total,
        "maior_vgv": maior_vgv,
        "ticket_medio": ticket_medio,
    }


def calcular_resumo_comercial(df_filtrado: pd.DataFrame, df_completo: pd.DataFrame, filtro_vendas: str) -> dict:
    status = df_filtrado["STATUS_BASE"].fillna("") if "STATUS_BASE" in df_filtrado.columns else pd.Series(dtype="object")

    em_analise = int((status == "EM ANALISE").sum())
    reanalise = int((status == "REANALISE").sum())
    aprovacoes = int((status == "APROVADO").sum())
    aprovado_bacen = int((status == "APROVADO BACEN").sum())
    aprovado_restricao = int((status == "APROVADO COM RESTRICAO").sum())
    reprovacoes = int((status == "REPROVADO").sum())
    analises_total = em_analise + reanalise

    vendas = calcular_vendas(df_filtrado, df_completo, filtro_vendas)
    vendas_total = vendas["vendas_total"]

    taxa_aprov_analise = (aprovacoes / analises_total * 100) if analises_total else 0.0
    taxa_venda_analise = (vendas_total / analises_total * 100) if analises_total else 0.0
    taxa_venda_aprov = (vendas_total / aprovacoes * 100) if aprovacoes else 0.0

    return {
        "em_analise": em_analise,
        "reanalise": reanalise,
        "analises_total": analises_total,
        "aprovacoes": aprovacoes,
        "aprovado_bacen": aprovado_bacen,
        "aprovado_restricao": aprovado_restricao,
        "reprovacoes": reprovacoes,
        "taxa_aprov_analise": taxa_aprov_analise,
        "taxa_venda_analise": taxa_venda_analise,
        "taxa_venda_aprov": taxa_venda_aprov,
        **vendas,
    }


def percentual(valor: float) -> str:
    return f"{float(valor or 0):.1f}%"
