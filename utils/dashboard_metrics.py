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
    if "ORIGEM_REGISTRO" in df_filtrado.columns:
        eventos = df_filtrado[df_filtrado["ORIGEM_REGISTRO"] == "ATIVIDADE"].copy()
    else:
        eventos = pd.DataFrame()

    ref_credito = eventos if not eventos.empty else df_filtrado.copy()
    etapa_evento = (
        ref_credito["ETAPA_EVENTO"].fillna("")
        if "ETAPA_EVENTO" in ref_credito.columns
        else ref_credito["ETAPA"].fillna("")
        if "ETAPA" in ref_credito.columns
        else pd.Series(dtype="object")
    )

    def contar_etapa(nome: str) -> int:
        linhas = ref_credito[etapa_evento == nome]
        if linhas.empty:
            return 0
        if "ID_LEAD" in linhas.columns:
            return int(linhas["ID_LEAD"].nunique())
        if "CHAVE_CLIENTE" in linhas.columns:
            return int(linhas["CHAVE_CLIENTE"].nunique())
        return int(len(linhas))

    nova_analise = contar_etapa("NOVA ANALISE")
    conferencia_pasteiro = contar_etapa("CONFERENCIA DO PASTEIRO")
    recusa_pasteiro = contar_etapa("RECUSA PASTEIRO")
    analise_credito = contar_etapa("ANALISE DE CREDITO")
    doc_pendente = contar_etapa("DOC PENDENTE")
    condicionado = contar_etapa("CONDICIONADO")
    restricao = contar_etapa("RESTRICAO")
    reprovado = contar_etapa("REPROVADO")
    aprovado_pendencia = contar_etapa("APROVADO C/ PENDENCIA")
    aprovado = contar_etapa("APROVADO")

    analises_total = nova_analise
    aprovacoes = aprovado + aprovado_pendencia
    vendas = calcular_vendas(df_filtrado, df_completo, filtro_vendas)
    vendas_total = vendas["vendas_total"]

    taxa_aprov_analise = (aprovacoes / analises_total * 100) if analises_total else 0.0
    taxa_venda_analise = (vendas_total / analises_total * 100) if analises_total else 0.0
    taxa_venda_aprov = (vendas_total / aprovacoes * 100) if aprovacoes else 0.0

    return {
        "nova_analise": nova_analise,
        "conferencia_pasteiro": conferencia_pasteiro,
        "recusa_pasteiro": recusa_pasteiro,
        "analise_credito": analise_credito,
        "doc_pendente": doc_pendente,
        "condicionado": condicionado,
        "restricao": restricao,
        "reprovado": reprovado,
        "aprovado_pendencia": aprovado_pendencia,
        "aprovado": aprovado,
        "em_analise": nova_analise,
        "reanalise": 0,
        "analises_total": analises_total,
        "aprovacoes": aprovacoes,
        "aprovado_bacen": 0,
        "aprovado_restricao": restricao + condicionado,
        "reprovacoes": reprovado,
        "taxa_aprov_analise": taxa_aprov_analise,
        "taxa_venda_analise": taxa_venda_analise,
        "taxa_venda_aprov": taxa_venda_aprov,
        **vendas,
    }


def percentual(valor: float) -> str:
    return f"{float(valor or 0):.1f}%"
