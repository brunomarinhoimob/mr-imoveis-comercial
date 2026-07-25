import pandas as pd


def status_final_por_cliente(df: pd.DataFrame) -> pd.Series:
    if df.empty or "CHAVE_CLIENTE" not in df.columns:
        return pd.Series(dtype="object", name="STATUS_FINAL_CLIENTE")

    ordenado = df.sort_values("DIA") if "DIA" in df.columns else df.copy()
    status = ordenado.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().fillna("")
    status.name = "STATUS_FINAL_CLIENTE"
    return status


def calcular_vendas(df_filtrado: pd.DataFrame, df_completo: pd.DataFrame, filtro_vendas: str) -> dict:
    if "GANHO" not in df_filtrado.columns:
        vendas_ref = pd.DataFrame()
    else:
        vendas_ref = df_filtrado[df_filtrado["GANHO"] == True].copy()

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

    vendas_ref = vendas_ref.sort_values("DIA")
    vendas_ult = vendas_ref.groupby("CHAVE_CLIENTE").tail(1)

    if vendas_ult.empty:
        return vazio

    venda_gerada = int(vendas_ult["CHAVE_CLIENTE"].nunique())
    venda_informada = 0
    vendas_total = venda_gerada
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

    if "TEM_1_ANALISE" in df_filtrado.columns:
        analises_df = df_filtrado[df_filtrado["TEM_1_ANALISE"] == True].copy()
        analises_total = int(analises_df["CHAVE_CLIENTE"].nunique()) if "CHAVE_CLIENTE" in analises_df.columns else len(analises_df)
        em_analise = analises_total
    else:
        em_analise = int((status == "EM ANALISE").sum())
        analises_total = em_analise + int((status == "REANALISE").sum())
    reanalise = int((status == "REANALISE").sum())
    aprovacoes = int((status == "APROVADO").sum())
    aprovado_bacen = int((status == "APROVADO BACEN").sum())
    aprovado_restricao = int((status == "APROVADO COM RESTRICAO").sum())
    reprovacoes = int((status == "REPROVADO").sum())
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
