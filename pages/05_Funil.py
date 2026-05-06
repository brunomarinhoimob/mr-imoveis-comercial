import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import date
import math

from utils.bootstrap import iniciar_app
from app_dashboard import carregar_dados_planilha
from streamlit_autorefresh import st_autorefresh


# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
st.set_page_config(
    page_title="Meta & Planejamento – MR Imóveis",
    page_icon="🎯",
    layout="wide",
)

st_autorefresh(interval=600 * 1000, key="auto_refresh_meta")


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
iniciar_app()
perfil = st.session_state.get("perfil")
nome_usuario = st.session_state.get("nome_usuario", "").upper().strip()


# ---------------------------------------------------------
# FUNÇÕES
# ---------------------------------------------------------
def format_int(v):
    try:
        return f"{int(v)}"
    except Exception:
        return "0"


def obter_vendas_unicas(df, status_final_map):
    if df.empty:
        return df.iloc[0:0].copy()

    df_v = df[df["STATUS_BASE"] == "VENDA GERADA"].copy()
    if df_v.empty:
        return df_v

    df_v["STATUS_FINAL"] = df_v["CHAVE_CLIENTE"].map(status_final_map)
    df_v = df_v[df_v["STATUS_FINAL"] != "DESISTIU"]

    df_v = df_v.sort_values("DIA").groupby("CHAVE_CLIENTE").tail(1)
    return df_v


# HISTÓRICO / VOLUME (para conversões e meta histórica)
def contar_analises_volume(df):
    return int(df["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"]).sum())


# REALIZADO (para o mês comercial): APENAS "EM ANÁLISE"
def contar_analises_realizado(df):
    return int((df["STATUS_BASE"] == "EM ANÁLISE").sum())


def contar_aprovacoes(df):
    return int((df["STATUS_BASE"] == "APROVADO").sum())


def total_por_tipo(df, tipo, status_final_map, modo="volume"):
    """
    modo:
      - "volume": análises = EM ANÁLISE + REANÁLISE
      - "realizado": análises = APENAS EM ANÁLISE
    """
    if df.empty:
        return 0

    if tipo == "Número de Análises":
        return contar_analises_realizado(df) if modo == "realizado" else contar_analises_volume(df)

    if tipo == "Número de Aprovações":
        return contar_aprovacoes(df)

    return int(len(obter_vendas_unicas(df, status_final_map)))


def serie_diaria_real(df, tipo, status_final_map, modo="realizado"):
    """
    Série diária do REAL (para gráfico).
    Para Análises no modo 'realizado' conta APENAS 'EM ANÁLISE'.
    """
    if df.empty:
        return pd.Series(dtype=int)

    if tipo == "Número de Análises":
        if modo == "realizado":
            s = df[df["STATUS_BASE"] == "EM ANÁLISE"].groupby("DIA").size()
        else:
            s = df[df["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])].groupby("DIA").size()

    elif tipo == "Número de Aprovações":
        s = df[df["STATUS_BASE"] == "APROVADO"].groupby("DIA").size()

    else:
        df_v = obter_vendas_unicas(df, status_final_map)
        s = df_v.groupby("DIA").size()

    return s.sort_index()


def bases_anteriores(df_scope, base_ref, n=3):
    """
    Retorna as N DATA_BASE_LABEL imediatamente anteriores à base_ref (DATA_BASE datetime).
    """
    if df_scope.empty or "DATA_BASE" not in df_scope.columns:
        return []

    uniq = (
        df_scope[["DATA_BASE", "DATA_BASE_LABEL"]]
        .dropna()
        .drop_duplicates()
        .sort_values("DATA_BASE")
        .reset_index(drop=True)
    )

    prev = uniq[uniq["DATA_BASE"] < base_ref]
    labels = prev["DATA_BASE_LABEL"].tolist()

    return labels[-n:] if labels else []


# ---------------------------------------------------------
# BASE
# ---------------------------------------------------------
df = carregar_dados_planilha(_refresh_key=st.session_state.get("refresh_planilha"))
df.columns = [c.upper().strip() for c in df.columns]
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
df["DATA_BASE"] = pd.to_datetime(df["DATA_BASE"], errors="coerce")

for c in ["EQUIPE", "CORRETOR"]:
    df[c] = df[c].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()

if "CHAVE_CLIENTE" not in df.columns:
    nome = df.get("NOME_CLIENTE_BASE", "NÃO INFORMADO").astype(str)
    cpf = df.get("CPF_CLIENTE_BASE", "").astype(str)
    df["CHAVE_CLIENTE"] = nome + " | " + cpf

df_final = df.sort_values("DIA").groupby("CHAVE_CLIENTE").tail(1)
status_final_por_cliente = df_final.set_index("CHAVE_CLIENTE")["STATUS_BASE"].to_dict()


# ---------------------------------------------------------
# FILTROS (TRAVA)
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

df_scope = df.copy()

if perfil == "corretor":
    df_scope = df_scope[df_scope["CORRETOR"] == nome_usuario]
else:
    visao = st.sidebar.radio("Visão", ["MR IMÓVEIS", "Equipe", "Corretor"])
    if visao == "Equipe":
        eq = st.sidebar.selectbox("Equipe", sorted(df_scope["EQUIPE"].unique()))
        df_scope = df_scope[df_scope["EQUIPE"] == eq]
    elif visao == "Corretor":
        cr = st.sidebar.selectbox("Corretor", sorted(df_scope["CORRETOR"].unique()))
        df_scope = df_scope[df_scope["CORRETOR"] == cr]


# ---------------------------------------------------------
# TOPO
# ---------------------------------------------------------
st.title("🎯 Meta & Planejamento")

tipo_meta = st.selectbox(
    "Tipo de Meta",
    ["Número de Análises", "Número de Aprovações", "Número de Vendas"]
)


# ---------------------------------------------------------
# SELETOR DA DATA_BASE (REFERÊNCIA PARA PEGAR AS 3 ANTERIORES)
# ---------------------------------------------------------
uniq_bases = (
    df_scope[["DATA_BASE", "DATA_BASE_LABEL"]]
    .dropna()
    .drop_duplicates()
    .sort_values("DATA_BASE")
)

lista_labels = uniq_bases["DATA_BASE_LABEL"].tolist()
base_label_sel = st.selectbox("Mês de Referência (DATA_BASE)", lista_labels)

base_ref = uniq_bases[uniq_bases["DATA_BASE_LABEL"] == base_label_sel]["DATA_BASE"].iloc[0]
labels_prev3 = bases_anteriores(df_scope, base_ref, n=3)

df_prev3 = df_scope[df_scope["DATA_BASE_LABEL"].isin(labels_prev3)].copy()


# ---------------------------------------------------------
# CONVERSÕES
# BASEADAS NAS 3 BASES ANTERIORES
# CASO NÃO EXISTA HISTÓRICO, USA CONVERSÃO PADRÃO
# REGRA PADRÃO: 7 ANÁLISES, 3 APROVAÇÕES PARA 1 VENDA
# ---------------------------------------------------------
vendas_prev3 = len(obter_vendas_unicas(df_prev3, status_final_por_cliente))
anal_prev3 = contar_analises_volume(df_prev3)   # volume: análise + reanálise
aprov_prev3 = contar_aprovacoes(df_prev3)

CONVERSAO_PADRAO_ANALISES_POR_VENDA = 7
CONVERSAO_PADRAO_APROVACOES_POR_VENDA = 3

if vendas_prev3 > 0:
    anal_por_venda = anal_prev3 / vendas_prev3
    aprov_por_venda = aprov_prev3 / vendas_prev3
    origem_conversao = "Conversão baseada nas 3 DATA_BASE anteriores"
else:
    anal_por_venda = CONVERSAO_PADRAO_ANALISES_POR_VENDA
    aprov_por_venda = CONVERSAO_PADRAO_APROVACOES_POR_VENDA
    origem_conversao = "Conversão padrão: 7 análises, 3 aprovações para 1 venda"


# ---------------------------------------------------------
# SIMULADOR
# ---------------------------------------------------------
st.markdown("### 🧮 Simulador de Produção")
vendas_desejadas = st.number_input("Vendas desejadas", min_value=0, step=1, value=0)

if vendas_desejadas > 0:
    st.metric("Análises necessárias", format_int(math.ceil(vendas_desejadas * anal_por_venda)))
    st.metric("Aprovações necessárias", format_int(math.ceil(vendas_desejadas * aprov_por_venda)))

st.caption("Bases referência (anteriores): " + (" | ".join(labels_prev3) if labels_prev3 else "—"))
st.caption(origem_conversao)


# ---------------------------------------------------------
# META HISTÓRICA (MÉDIA DAS 3 BASES ANTERIORES)
# ---------------------------------------------------------
valores_meta = []
for lab in labels_prev3:
    df_b = df_scope[df_scope["DATA_BASE_LABEL"] == lab]
    # meta histórica usa "volume" (análise + reanálise)
    valores_meta.append(total_por_tipo(df_b, tipo_meta, status_final_por_cliente, modo="volume"))

meta_historica = int(math.ceil(np.mean(valores_meta))) if valores_meta else 0


# ---------------------------------------------------------
# META FINAL
# ---------------------------------------------------------
if vendas_desejadas > 0:
    if tipo_meta == "Número de Vendas":
        meta_valor = vendas_desejadas
        origem_meta = "Meta definida pelo Simulador (vendas desejadas)"
    elif tipo_meta == "Número de Análises":
        meta_valor = int(math.ceil(vendas_desejadas * anal_por_venda))
        origem_meta = "Meta definida pelo Simulador (convertida em análises)"
    else:
        meta_valor = int(math.ceil(vendas_desejadas * aprov_por_venda))
        origem_meta = "Meta definida pelo Simulador (convertida em aprovações)"
else:
    meta_valor = meta_historica
    origem_meta = "Meta histórica (média das 3 DATA_BASE anteriores)"

st.markdown("### 🎯 Meta Atual")
st.metric("Meta", format_int(meta_valor))
st.caption(origem_meta)


# ---------------------------------------------------------
# MÊS COMERCIAL (MANUAL)
# ---------------------------------------------------------
st.subheader("📅 Mês Comercial (manual)")

c1, c2 = st.columns(2)
dt_inicio = c1.date_input("Início do mês comercial", value=base_ref.date())
dt_fim = c2.date_input("Fim do mês comercial", value=base_ref.date())

if dt_fim < dt_inicio:
    st.error("Fim do mês comercial não pode ser menor que o início.")
    st.stop()

df_periodo = df_scope[
    (df_scope["DIA"].dt.date >= dt_inicio) &
    (df_scope["DIA"].dt.date <= dt_fim)
].copy()

if df_periodo.empty:
    st.info("Sem registros no período selecionado.")
    st.stop()

# REAL só até o último dia existente na planilha dentro do período
ultimo_dia_planilha = df_periodo["DIA"].max().date()
df_real = df_periodo[df_periodo["DIA"].dt.date <= ultimo_dia_planilha].copy()


# ---------------------------------------------------------
# REAL x META (REALIZADO: análises = APENAS EM ANÁLISE)
# ---------------------------------------------------------
real_total = total_por_tipo(df_real, tipo_meta, status_final_por_cliente, modo="realizado")
faltam = max(meta_valor - real_total, 0)
pct = (real_total / meta_valor) if meta_valor > 0 else 0

c1, c2, c3 = st.columns(3)
c1.metric("Meta", format_int(meta_valor))
c2.metric("Realizado", format_int(real_total))
c3.metric("% Atingido", f"{pct:.1%}")


# ---------------------------------------------------------
# 📆 RITMO DIÁRIO NECESSÁRIO
# ---------------------------------------------------------
from datetime import timedelta

# Dias totais do mês comercial
dias_totais = (dt_fim - dt_inicio).days + 1

# Último dia real considerado
ultimo_dia_real = df_real["DIA"].max().date()

# Dias já ocorridos dentro do mês comercial
dias_decorridos = (ultimo_dia_real - dt_inicio).days + 1
dias_decorridos = max(dias_decorridos, 0)

# Dias restantes
dias_restantes = dias_totais - dias_decorridos

faltam = max(meta_valor - real_total, 0)

if dias_restantes > 0 and faltam > 0:
    ritmo_diario = faltam / dias_restantes
else:
    ritmo_diario = 0

st.markdown("### 📌 Produção necessária por dia")

if dias_restantes <= 0:
    st.info("O período do mês comercial já foi concluído.")
elif faltam <= 0:
    st.success("Meta já atingida 🎉")
else:
    unidade = (
        "análises" if tipo_meta == "Número de Análises"
        else "aprovações" if tipo_meta == "Número de Aprovações"
        else "vendas"
    )

    st.metric(
        f"{unidade.capitalize()} por dia",
        f"{ritmo_diario:.1f}",
        help=(
            f"Faltam {faltam} {unidade} em {dias_restantes} dias restantes "
            f"do mês comercial."
        )
    )


# ---------------------------------------------------------
# 📊 ACUMULADO – ÚLTIMAS 3 DATA_BASE
# ---------------------------------------------------------
st.markdown("### 📊 Resultado acumulado — últimas 3 DATA_BASE")

if not labels_prev3:
    st.info("Não há 3 DATA_BASE anteriores suficientes para exibir o acumulado.")
else:
    df_3bases = df_scope[df_scope["DATA_BASE_LABEL"].isin(labels_prev3)].copy()

    anal_3b = contar_analises_realizado(df_3bases)
    aprov_3b = contar_aprovacoes(df_3bases)
    vendas_3b = len(obter_vendas_unicas(df_3bases, status_final_por_cliente))

    c1, c2, c3 = st.columns(3)

    c1.metric("Análises", format_int(anal_3b))
    c2.metric("Aprovações", format_int(aprov_3b))
    c3.metric("Vendas", format_int(vendas_3b))

    st.caption("Bases consideradas: " + " | ".join(labels_prev3))


# ---------------------------------------------------------
# 🍩 DONUT
# ---------------------------------------------------------
st.subheader("🍩 Progresso da Meta")

df_donut = pd.DataFrame({
    "Status": ["Atingido", "Falta"],
    "Valor": [real_total, faltam]
})

donut = (
    alt.Chart(df_donut)
    .mark_arc(innerRadius=60)
    .encode(theta="Valor:Q", color="Status:N")
    .properties(height=300)
)

st.altair_chart(donut, use_container_width=True)


# ---------------------------------------------------------
# 📈 GRÁFICO – META x REAL (ACUMULADO)
# ---------------------------------------------------------
st.subheader("📈 Acompanhamento — Meta x Real (acumulado)")

cont_real = serie_diaria_real(df_real, tipo_meta, status_final_por_cliente, modo="realizado")
real_acum = cont_real.cumsum().reset_index()
real_acum.columns = ["DIA", "Valor"]
real_acum["Série"] = "Real"

dias_meta = pd.date_range(dt_inicio, dt_fim, freq="D")
meta_linear = np.linspace(0, meta_valor, num=len(dias_meta), endpoint=True)

df_meta = pd.DataFrame({
    "DIA": dias_meta,
    "Valor": meta_linear,
    "Série": "Meta"
})

df_plot = pd.concat([real_acum, df_meta], ignore_index=True)

chart = (
    alt.Chart(df_plot)
    .mark_line(point=True)
    .encode(
        x=alt.X("DIA:T", title="Dia"),
        y=alt.Y("Valor:Q", title="Total acumulado"),
        color=alt.Color("Série:N", title=""),
    )
    .properties(height=380)
)

st.altair_chart(chart, use_container_width=True)

st.caption(
    "Real (Análises) conta apenas 'EM ANÁLISE'. "
    "Meta e conversões usam volume (análise + reanálise) nas 3 DATA_BASE anteriores. "
    "Quando não há histórico de vendas, o simulador usa a conversão padrão de 7 análises, 3 aprovações para 1 venda. "
    "Real contabiliza somente até o último dia registrado na planilha dentro do período."
)