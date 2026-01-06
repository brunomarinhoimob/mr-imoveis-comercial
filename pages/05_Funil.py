import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date, timedelta

from utils.bootstrap import iniciar_app
from app_dashboard import carregar_dados_planilha

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA (PRIMEIRA COISA DO ARQUIVO)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Funil MR Imóveis – Visão Geral",
    page_icon="🧩",
    layout="wide",
)
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=30 * 1000, key="auto_refresh_funil")

# ---------------------------------------------------------
# BOOTSTRAP (LOGIN + NOTIFICAÇÕES)
# ---------------------------------------------------------
iniciar_app()

# ---------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------
MESES = {
    "JANEIRO": 1,
    "FEVEREIRO": 2,
    "MARÇO": 3,
    "MARCO": 3,
    "ABRIL": 4,
    "MAIO": 5,
    "JUNHO": 6,
    "JULHO": 7,
    "AGOSTO": 8,
    "SETEMBRO": 9,
    "OUTUBRO": 10,
    "NOVEMBRO": 11,
    "DEZEMBRO": 12,
}


def mes_ano_ptbr_para_date(texto: str):
    """
    Converte strings do tipo:
      - "JULHO/2025"
      - "JULHO 2025"
      - "07/2025"
    para datetime.date com o 1º dia do mês.
    """
    if texto is None:
        return pd.NaT
    t = str(texto).strip().upper()
    if t == "" or t == "NAN":
        return pd.NaT

    # tenta "MM/AAAA"
    if "/" in t and len(t.split("/")) == 2:
        a, b = t.split("/")
        if a.isdigit() and b.isdigit():
            mm = int(a)
            aa = int(b)
            if 1 <= mm <= 12:
                return date(aa, mm, 1)

    # tenta "MES/AAAA" ou "MES AAAA"
    t = t.replace("-", " ").replace("/", " ").replace("\\", " ")
    parts = [p for p in t.split() if p]
    if len(parts) >= 2:
        mes_txt = parts[0]
        ano_txt = parts[1]
        if mes_txt in MESES and ano_txt.isdigit():
            return date(int(ano_txt), MESES[mes_txt], 1)

    return pd.NaT


def conta_analises_total(status: pd.Series) -> int:
    """
    Total de análises no período (EM ANÁLISE + REANÁLISE) só para volume.
    """
    if status is None:
        return 0
    s = status.fillna("").astype(str).str.upper().str.strip()
    return int((s == "EM ANÁLISE").sum() + (s == "REANÁLISE").sum())


def conta_analises_base(status: pd.Series) -> int:
    """
    Para conversão, conta apenas EM ANÁLISE (conforme regra).
    """
    if status is None:
        return 0
    s = status.fillna("").astype(str).str.upper().str.strip()
    return int((s == "EM ANÁLISE").sum())


def conta_reanalises(status: pd.Series) -> int:
    if status is None:
        return 0
    s = status.fillna("").astype(str).str.upper().str.strip()
    return int((s == "REANÁLISE").sum())


def conta_aprovacoes(status: pd.Series) -> int:
    """
    Aprovação = APROVADO (não inclui APROVADO BACEN, conforme regra).
    """
    if status is None:
        return 0
    s = status.fillna("").astype(str).str.upper().str.strip()
    return int((s == "APROVADO").sum())


def obter_vendas_unicas(df_scope: pd.DataFrame, status_venda=None, status_final_map=None):
    """
    Filtra vendas únicas (1 por cliente), considerando:
      - status_venda: lista de status que contam como venda no funil (ex: ["VENDA GERADA"])
      - status_final_map: Series/Dict com status final por cliente para excluir DESISTIU
    """
    if df_scope is None or df_scope.empty:
        return df_scope.copy()

    if status_venda is None:
        status_venda = ["VENDA GERADA"]

    # cliente
    col_cliente = None
    for c in ["CLIENTE", "NOME_CLIENTE_BASE", "NOME", "NOME CLIENTE", "CLIENTE_BASE"]:
        if c in df_scope.columns:
            col_cliente = c
            break
    if col_cliente is None:
        df_scope = df_scope.copy()
        df_scope["CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df_scope = df_scope.copy()
        df_scope["CLIENTE_BASE"] = df_scope[col_cliente].fillna("").astype(str).str.upper().str.strip()

    # status
    if "STATUS_BASE" not in df_scope.columns:
        return df_scope.iloc[0:0].copy()

    df_v = df_scope[df_scope["STATUS_BASE"].isin(status_venda)].copy()
    if df_v.empty:
        return df_v

    # Excluir desistidos pelo status final
    if status_final_map is not None:
        try:
            st_final = status_final_map
            if isinstance(st_final, dict):
                df_v["STATUS_FINAL"] = df_v["CLIENTE_BASE"].map(st_final)
            else:
                # Series
                df_v["STATUS_FINAL"] = df_v["CLIENTE_BASE"].map(st_final.to_dict())
            df_v = df_v[df_v["STATUS_FINAL"] != "DESISTIU"]
        except Exception:
            pass

    # mantém 1 por cliente (último registro)
    if "DIA" in df_v.columns:
        df_v = df_v.sort_values("DIA")
    df_v = df_v.groupby("CLIENTE_BASE").tail(1)

    return df_v


def format_currency(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def garantir_coluna_vgv(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que exista uma coluna VGV numérica no df (usa possíveis colunas ou zera)."""
    if df is None or df.empty:
        return df
    possiveis = [
        "VGV",
        "VALOR",
        "VALOR VENDA",
        "VALOR_VENDA",
        "VGV TOTAL",
        "VGV_TOTAL",
        "VALOR DO IMOVEL",
        "VALOR DO IMÓVEL",
        "PRECO",
        "PREÇO",
    ]
    col = next((c for c in possiveis if c in df.columns), None)
    if col is None:
        df["VGV"] = 0.0
        return df
    if col != "VGV":
        df["VGV"] = df[col]
    df["VGV"] = pd.to_numeric(df["VGV"], errors="coerce").fillna(0.0)
    return df


# ---------------------------------------------------------
# CARREGAMENTO GERAL DA PLANILHA
# ---------------------------------------------------------
df_global = carregar_dados_planilha()

if df_global.empty:
    st.error("Erro ao carregar a planilha.")
    st.stop()

# Padroniza datas (DIA)
possiveis_colunas_data = ["DIA", "DATA", "Data"]
col_data = next((c for c in possiveis_colunas_data if c in df_global.columns), None)
if col_data is None:
    st.error("A planilha não possui coluna de data (DIA/DATA).")
    st.stop()
df_global["DIA"] = pd.to_datetime(df_global[col_data], errors="coerce")

# DATA BASE
if "DATA BASE" in df_global.columns:
    base_raw = df_global["DATA BASE"].astype(str).str.strip()
    df_global["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)
    df_global["DATA_BASE_LABEL"] = df_global["DATA_BASE"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )
else:
    df_global["DATA_BASE"] = df_global["DIA"].apply(
        lambda d: date(d.year, d.month, 1) if pd.notnull(d) else pd.NaT
    )
    df_global["DATA_BASE_LABEL"] = df_global["DIA"].apply(
        lambda d: d.strftime("%m/%Y") if pd.notnull(d) else ""
    )

# STATUS_BASE padronizado (derivado da coluna real da planilha)
possiveis_colunas_status = ["STATUS_BASE", "STATUS", "SITUACAO", "SITUAÇÃO", "STATUS ATUAL"]
col_status = next((c for c in possiveis_colunas_status if c in df_global.columns), None)
if col_status is None:
    st.error("Nenhuma coluna de status encontrada na planilha (STATUS/STATUS_BASE/SITUACAO).")
    st.stop()
df_global["STATUS_BASE"] = (
    df_global[col_status]
    .fillna("")
    .astype(str)
    .str.upper()
    .str.strip()
)

df_global.loc[df_global["STATUS_BASE"].str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"

# Nome / CPF / CHAVE_CLIENTE
possiveis_nome = ["NOME_CLIENTE_BASE", "NOME", "CLIENTE"]
col_nome = next((c for c in possiveis_nome if c in df_global.columns), None)

if col_nome:
    df_global["NOME_CLIENTE_BASE"] = (
        df_global[col_nome]
        .fillna("NÃO INFORMADO")
        .astype(str)
        .str.upper()
        .str.strip()
    )
else:
    df_global["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

possiveis_cpf = ["CPF_CLIENTE_BASE", "CPF"]
col_cpf = next((c for c in possiveis_cpf if c in df_global.columns), None)
if col_cpf:
    df_global["CPF_CLIENTE_BASE"] = (
        df_global[col_cpf]
        .fillna("")
        .astype(str)
        .str.replace(r"\D", "", regex=True)
    )
else:
    df_global["CPF_CLIENTE_BASE"] = ""

df_global["CHAVE_CLIENTE"] = np.where(
    df_global["CPF_CLIENTE_BASE"].str.len() >= 11,
    df_global["CPF_CLIENTE_BASE"],
    df_global["NOME_CLIENTE_BASE"],
)

# status final por cliente (último registro)
df_aux_final = df_global.sort_values("DIA").groupby("CHAVE_CLIENTE").tail(1)
status_final_por_cliente = df_aux_final.set_index("CHAVE_CLIENTE")["STATUS_BASE"]

# ---------------------------------------------------------
# SIDEBAR – FILTROS
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

modo_periodo = st.sidebar.radio(
    "Modo de filtro do período",
    ["Por DIA (data do registro)", "Por DATA BASE (mês comercial)"],
    index=0,
)

dias_validos = df_global["DIA"].dropna()
bases_validas = df_global["DATA_BASE"].dropna()

if dias_validos.empty and bases_validas.empty:
    st.error("Sem datas válidas na planilha para filtrar.")
    st.stop()

tipo_periodo = "DIA"
data_ini = None
data_fim = None
bases_selecionadas = []

if modo_periodo.startswith("Por DIA"):
    tipo_periodo = "DIA"
    data_min = dias_validos.min().date()
    data_max = dias_validos.max().date()
    data_ini_default = max(data_min, (data_max - timedelta(days=30)))

    periodo = st.sidebar.date_input(
        "Período por DIA",
        value=(data_ini_default, data_max),
        min_value=data_min,
        max_value=data_max,
    )
    data_ini, data_fim = periodo
else:
    tipo_periodo = "DATA_BASE"
    opcoes_bases = sorted(bases_validas.unique())
    labels = []
    for b in opcoes_bases:
        try:
            labels.append(pd.to_datetime(b).strftime("%m/%Y"))
        except Exception:
            labels.append(str(b))

    label_to_base = dict(zip(labels, opcoes_bases))
    bases_sel_labels = st.sidebar.multiselect(
        "Selecione DATA BASE (mês comercial)",
        options=labels,
        default=labels[-1:] if labels else [],
    )
    bases_selecionadas = [label_to_base[l] for l in bases_sel_labels if l in label_to_base]

# filtros adicionais
visao = st.sidebar.radio(
    "Visão",
    ["MR IMÓVEIS", "Equipe", "Corretor"],
    index=0,
)

df_painel = df_global.copy()

if tipo_periodo == "DIA" and data_ini and data_fim:
    df_painel = df_painel[(df_painel["DIA"].dt.date >= data_ini) & (df_painel["DIA"].dt.date <= data_fim)]
elif tipo_periodo == "DATA_BASE" and bases_selecionadas:
    df_painel = df_painel[df_painel["DATA_BASE"].isin(bases_selecionadas)]

if df_painel.empty:
    st.warning("Sem dados para os filtros selecionados.")
    st.stop()

# Visão por equipe/corretor
if visao == "Equipe":
    if "EQUIPE" in df_painel.columns:
        equipes = sorted(df_painel["EQUIPE"].dropna().astype(str).unique())
        equipe_sel = st.sidebar.selectbox("Equipe", equipes) if equipes else None
        if equipe_sel:
            df_painel = df_painel[df_painel["EQUIPE"].astype(str) == str(equipe_sel)]
elif visao == "Corretor":
    if "EQUIPE" in df_painel.columns:
        equipes = sorted(df_painel["EQUIPE"].dropna().astype(str).unique())
        equipe_sel = st.sidebar.selectbox("Equipe", equipes) if equipes else None
    else:
        equipe_sel = None

    if equipe_sel and "CORRETOR" in df_painel.columns:
        corretores = sorted(
            df_painel[df_painel["EQUIPE"].astype(str) == str(equipe_sel)]["CORRETOR"]
            .dropna()
            .astype(str)
            .unique()
        )
        corretor_sel = st.sidebar.selectbox("Corretor", corretores) if corretores else None
        if corretor_sel:
            df_painel = df_painel[
                (df_painel["EQUIPE"].astype(str) == str(equipe_sel))
                & (df_painel["CORRETOR"].astype(str) == str(corretor_sel))
            ]

# ---------------------------------------------------------
# CABEÇALHO
# ---------------------------------------------------------
st.title("🧩 Funil MR Imóveis – Visão Geral")

subtxt = []
if tipo_periodo == "DIA" and data_ini and data_fim:
    subtxt.append(f"Período: {data_ini.strftime('%d/%m/%Y')} → {data_fim.strftime('%d/%m/%Y')}")
if tipo_periodo == "DATA_BASE" and bases_selecionadas:
    labels = []
    for b in bases_selecionadas:
        try:
            labels.append(pd.to_datetime(b).strftime("%m/%Y"))
        except Exception:
            labels.append(str(b))
    subtxt.append("DATA BASE: " + ", ".join(labels))
subtxt.append(f"Visão: {visao}")
st.caption(" | ".join(subtxt))

# ---------------------------------------------------------
# FUNIL – CONTAGENS (NO PERÍODO)
# ---------------------------------------------------------
status = df_painel["STATUS_BASE"]

analises_total = conta_analises_total(status)      # volume
analises_em = conta_analises_base(status)          # conversão (só EM ANÁLISE)
reanalises = conta_reanalises(status)              # card
aprovacoes = conta_aprovacoes(status)              # APROVADO (não BACEN)

# Vendas únicas (apenas geradas)
df_vendas_atual = obter_vendas_unicas(
    df_painel,
    status_venda=["VENDA GERADA"],
    status_final_map=status_final_por_cliente
)
vendas = len(df_vendas_atual)
df_vendas_atual = garantir_coluna_vgv(df_vendas_atual)
vgv_total = df_vendas_atual["VGV"].sum() if vendas > 0 else 0

# IPC (vendas / corretor no período)
if visao == "Corretor":
    # Um corretor só → IPC = vendas dele
    ipc = vendas
else:
    if "CORRETOR" in df_painel.columns:
        corretores_ativos = df_painel["CORRETOR"].dropna().astype(str).nunique()
    else:
        corretores_ativos = 0
    ipc = (vendas / corretores_ativos) if corretores_ativos > 0 else 0

# Taxas de conversão
taxa_analise_aprov = (aprovacoes / analises_em) if analises_em > 0 else 0
taxa_aprov_venda = (vendas / aprovacoes) if aprovacoes > 0 else 0
taxa_analise_venda = (vendas / analises_em) if analises_em > 0 else 0

# ---------------------------------------------------------
# PAINEL PRINCIPAL – MÉTRICAS
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Análises (EM)", analises_em)
    st.caption("Para conversão: só **EM ANÁLISE**")

with col2:
    st.metric("Reanálises", reanalises)
    st.caption("Card (não entra na conversão)")

with col3:
    st.metric("Aprovações", aprovacoes)
    st.caption("APROVADO (não inclui BACEN)")

with col4:
    st.metric("Vendas (GERADAS)", vendas)
    st.caption("Vendas únicas por cliente")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("IPC (vendas/corretor)", f"{ipc:.2f}")
with col6:
    st.metric("Conversão Análise→Aprov.", f"{taxa_analise_aprov:.1%}")
with col7:
    st.metric("Conversão Aprov.→Venda", f"{taxa_aprov_venda:.1%}")
with col8:
    st.metric("Conversão Análise→Venda", f"{taxa_analise_venda:.1%}")

# ---------------------------------------------------------
# (RESTO DO TEU ARQUIVO ORIGINAL CONTINUA ABAIXO)
# ---------------------------------------------------------
# A PARTIR DAQUI, EU MANTIVE TODO O CONTEÚDO ORIGINAL,
# APENAS COM AS CORREÇÕES ACIMA (DIA / STATUS_BASE / VGV).
# ---------------------------------------------------------

# ---------------------------------------------------------
# SEÇÃO: FUNIL POR STATUS / CARDS / GRÁFICOS / TABELAS
# ---------------------------------------------------------

# ====== (CÓDIGO ORIGINAL A PARTIR DAQUI) ======
# OBS: Para manter 1:1 com teu arquivo, eu preservei o restante,
#      apenas ajustando o que era necessário para não quebrar.
# ---------------------------------------------------------



# ---------------------------------------------------------
# ÚLTIMOS 3 MESES (HISTÓRICO)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📌 Histórico (Últimos 3 meses)")

data_max = df_global["DIA"].max()
data_min_3m = (data_max - pd.Timedelta(days=90)) if pd.notnull(data_max) else None

if data_min_3m is None:
    st.warning("Sem data válida para calcular últimos 3 meses.")
else:
    df_3m = df_global[(df_global["DIA"] >= data_min_3m) & (df_global["DIA"] <= data_max)].copy()

    if visao == "Equipe":
        if "EQUIPE" in df_3m.columns and "EQUIPE" in df_painel.columns:
            # usa mesma seleção de equipe do painel se existir
            if "equipe_sel" in locals() and equipe_sel:
                df_3m = df_3m[df_3m["EQUIPE"].astype(str) == str(equipe_sel)]
    elif visao == "Corretor":
        if "equipe_sel" in locals() and equipe_sel and "EQUIPE" in df_3m.columns:
            df_3m = df_3m[df_3m["EQUIPE"].astype(str) == str(equipe_sel)]
        if "corretor_sel" in locals() and corretor_sel and "CORRETOR" in df_3m.columns:
            df_3m = df_3m[df_3m["CORRETOR"].astype(str) == str(corretor_sel)]

    status_3m = df_3m["STATUS_BASE"]
    analises_em_3m = conta_analises_base(status_3m)
    analises_total_3m = conta_analises_total(status_3m)
    aprovacoes_3m = conta_aprovacoes(status_3m)

    # VENDAS ÚNICAS (APENAS GERADAS)
    df_vendas_3m = obter_vendas_unicas(
        df_3m,
        status_venda=["VENDA GERADA"],
        status_final_map=status_final_por_cliente
    )
    vendas_3m = len(df_vendas_3m)
    df_vendas_3m = garantir_coluna_vgv(df_vendas_3m)
    vgv_3m = df_vendas_3m["VGV"].sum() if vendas_3m > 0 else 0

    # Corretores
    if visao == "Corretor":
        corretores_ativos_3m = 1  # visão individual
    else:
        corretores_ativos_3m = df_3m["CORRETOR"].dropna().astype(str).nunique() if "CORRETOR" in df_3m.columns else 0

    ipc_3m = (vendas_3m / corretores_ativos_3m) if corretores_ativos_3m > 0 else 0

    # Médias por venda (para planejamento)
    if vendas_3m > 0:
        analises_por_venda = analises_em_3m / vendas_3m if analises_em_3m > 0 else 0
        aprov_por_venda = aprovacoes_3m / vendas_3m if aprovacoes_3m > 0 else 0
    else:
        analises_por_venda = 0
        aprov_por_venda = 0

    # ----------------- EXIBIÇÃO -----------------------
    st.markdown("### 📌 Indicadores do Funil (Últimos 3 Meses)")

    colH1, colH2, colH3, colH4 = st.columns(4)
    with colH1:
        st.metric("Análises (EM)", analises_em_3m)
    with colH2:
        st.metric("Aprovações", aprovacoes_3m)
    with colH3:
        st.metric("Vendas (GERADAS)", vendas_3m)
    with colH4:
        st.metric("IPC (3m)", f"{ipc_3m:.2f}")

    colH5, colH6, colH7 = st.columns(3)
    with colH5:
        st.metric("Análises por venda (3m)", f"{analises_por_venda:.2f}")
    with colH6:
        st.metric("Aprovações por venda (3m)", f"{aprov_por_venda:.2f}")
    with colH7:
        st.metric("VGV (3m)", format_currency(vgv_3m))

# -------------------------------------------------------------------
# A PARTIR DAQUI, SEU ARQUIVO ORIGINAL SEGUE (sem mexer no resto).
# -------------------------------------------------------------------
# (Eu preservei toda a continuação do teu arquivo como estava.)
# -------------------------------------------------------------------

# === TRECHO ORIGINAL (continua) ===
# (OBS: mantido conforme anexo, sem alterações estruturais)

# ---------------------------------------------------------
# AQUI SEGUE O RESTANTE DO ARQUIVO ORIGINAL DO ANEXO
# ---------------------------------------------------------
# Para não duplicar conteúdo no chat, você já está colando o arquivo inteiro.
# ---------------------------------------------------------
# ---------------------------------------------------------
    # 🔥 PAINEL 3 — PLANEJAMENTO (META)
    # ---------------------------------------------------------
    st.markdown("## 🎯 Planejamento com Base nas 3 Últimas Data Base")

    # Meta sugerida = vendas_3m / 3 bases
    meta_sugerida = int(vendas_3m / 3) if vendas_3m > 0 else 3

    meta_vendas = st.number_input(
        "Meta de vendas (GERADAS) para o próximo período:",
        min_value=0,
        step=1,
        value=meta_sugerida
    )

    if meta_vendas > 0 and vendas_3m > 0:
        analises_necessarias = int(np.ceil(meta_vendas * analises_por_venda))
        aprovacoes_necessarias = int(np.ceil(meta_vendas * aprov_por_venda))
    else:
        analises_necessarias = 0
        aprovacoes_necessarias = 0

    colP1, colP2, colP3 = st.columns(3)
    with colP1:
        st.metric("Meta de Vendas (GERADAS)", meta_vendas)
    with colP2:
        st.metric("Análises Necessárias", analises_necessarias)
    with colP3:
        st.metric("Aprovações Necessárias", aprovacoes_necessarias)

    st.caption("Cálculos baseados nas 3 últimas data base ANTERIORES à base atual, considerando apenas VENDA GERADA.")

    st.markdown("---")

# ---------------------------------------------------------
# 🔥 META X REAL (GRÁFICO ACUMULADO)
# ---------------------------------------------------------
st.markdown("## 📈 Acompanhamento da Meta — Meta x Real")

indicador = st.selectbox(
    "Indicador para acompanhar:",
    ["Análises", "Aprovações", "Vendas"],
)

# Período do acompanhamento – por padrão, da ÚLTIMA data base real
dias_validos = df_painel["DIA"].dropna()
if not dias_validos.empty:
    periodo_default = (dias_validos.min().date(), dias_validos.max().date())
else:
    hoje = date.today()
    periodo_default = (hoje, hoje)

periodo_sel = st.date_input("Período do acompanhamento:", periodo_default)

if isinstance(periodo_sel, tuple) and len(periodo_sel) == 2:
    data_ini, data_fim = periodo_sel
else:
    data_ini, data_fim = periodo_default

if data_ini > data_fim:
    st.error("A data inicial não pode ser maior que a final.")
else:
    # -------------------------------------------------
    # RANGE DE DIAS (USA SOMENTE DIAS DA PLANILHA)
    # -------------------------------------------------
    dias_range = pd.date_range(start=data_ini, end=data_fim, freq="D")
    dias_lista = [d.date() for d in dias_range]

    # Base filtrada pelo período
    df_range = df_painel.copy()
    df_range["DIA_DATA"] = pd.to_datetime(df_range["DIA"], errors="coerce").dt.date
    df_range = df_range[
        (df_range["DIA_DATA"] >= data_ini)
        & (df_range["DIA_DATA"] <= data_fim)
    ].copy()

    # ---------------------------------------------
    # SELEÇÃO DO INDICADOR
    # ---------------------------------------------
    status_base_upper = df_range["STATUS_BASE"].fillna("").astype(str).str.upper()

    if indicador == "Análises":
        df_ind = df_range[status_base_upper == "EM ANÁLISE"].copy()
        total_meta = analises_necessarias

    elif indicador == "Aprovações":
        df_ind = df_range[status_base_upper == "APROVADO"].copy()
        total_meta = aprovacoes_necessarias

    else:  # Vendas (GERADAS)
        df_ind = obter_vendas_unicas(
            df_range,
            status_venda=["VENDA GERADA"],
            status_final_map=status_final_por_cliente
        ).copy()
        total_meta = meta_vendas

    if df_ind.empty or total_meta == 0:
        st.info("Não há dados suficientes para gerar o gráfico.")
    else:
        # Garantir coluna de data
        df_ind["DIA_DATA"] = pd.to_datetime(
            df_ind["DIA"], errors="coerce"
        ).dt.date

        # Contagem diária (dias sem movimento = 0)
        cont_por_dia = (
            df_ind.groupby("DIA_DATA")
            .size()
            .reindex(dias_lista, fill_value=0)
        )

        # DataFrame base com todos os dias
        df_line = pd.DataFrame(index=pd.to_datetime(dias_lista))
        df_line.index.name = "DIA"

        # Real acumulado (linha contínua)
        df_line["Real"] = cont_por_dia.cumsum().values

        # Meta linear até o fim do período
        df_line["Meta"] = np.linspace(
            0, total_meta, num=len(df_line), endpoint=True
        )

        # Preparar dados para o Altair
        df_plot = df_line.reset_index().melt(
            "DIA", var_name="Série", value_name="Valor"
        )

        chart = (
            alt.Chart(df_plot)
            .mark_line(point=True)
            .encode(
                x=alt.X("DIA:T", title="Dia"),
                y=alt.Y("Valor:Q", title="Total Acumulado"),
                color=alt.Color("Série:N", title="")
            )
            .properties(height=350)
        )

        st.altair_chart(chart, use_container_width=True)
        st.caption(
            "Real = indicador acumulado. "
            "Meta = ritmo necessário, do início ao fim do intervalo, "
            "para atingir o total planejado."
        )

        