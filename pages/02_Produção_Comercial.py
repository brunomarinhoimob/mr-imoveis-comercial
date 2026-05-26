import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Produção Comercial",
    page_icon="📞",
    layout="wide"
)

st_autorefresh(interval=30 * 1000, key="auto_refresh_producao")

# =========================================================
# CSS
# =========================================================
st.markdown("""
<style>
.stApp {
    background: #020617;
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #0f172a 0%, #020617 100%);
    border: 1px solid rgba(148,163,184,0.20);
    padding: 18px;
    border-radius: 18px;
}

div[data-testid="stMetricLabel"] {
    color: #94a3b8;
}

div[data-testid="stMetricValue"] {
    color: white;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# GOOGLE SHEETS (LINKS OTIMIZADOS PARA TEMPO REAL)
# =========================================================
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"

GID_PRODUCAO = "1161609337"
GID_PROCESSOS = "1574157905"

CSV_PRODUCAO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PRODUCAO}"
CSV_PROCESSOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_PROCESSOS}"

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def mes_ano_ptbr_para_date(valor):
    if pd.isna(valor):
        return pd.NaT

    s = str(valor).strip().lower()
    if not s:
        return pd.NaT

    meses = {
        "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3,
        "abril": 4, "maio": 5, "junho": 6, "julho": 7,
        "agosto": 8, "setembro": 9, "outubro": 10,
        "novembro": 11, "dezembro": 12,
    }

    try:
        partes = s.split()
        mes_txt = partes[0]
        ano = int(partes[-1])
        mes_num = meses.get(mes_txt)
        if mes_num is None:
            return pd.NaT
        return datetime(ano, mes_num, 1).date()
    except:
        return pd.NaT


def tratar_data_base(df):
    possiveis_cols_base = [
        "DATA BASE", "DATA_BASE", "DT BASE",
        "DATA REF", "DATA REFERÊNCIA", "DATA REFERENCIA",
    ]

    col_data_base = next((c for c in possiveis_cols_base if c in df.columns), None)

    if col_data_base:
        base_raw = df[col_data_base].fillna("").astype(str).str.strip()
        df["DATA_BASE_LABEL"] = base_raw.str.lower().str.title()
        df["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)
    else:
        df["DATA_BASE_LABEL"] = ""
        df["DATA_BASE"] = pd.NaT

    return df

# =========================================================
# CARREGAR PRODUÇÃO COMERCIAL
# =========================================================
@st.cache_data(ttl=10)
def carregar_base():
    df = pd.read_csv(CSV_PRODUCAO)
    df.columns = [c.strip().upper() for c in df.columns]

    if "DATA" not in df.columns:
        df["DATA"] = pd.NaT
    else:
        df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")

    df = tratar_data_base(df)

    colunas_numericas = [
        "ATENDEU", "PROSPECT", "WHATSAPP ENVIADO",
        "CONTATO INVÁLIDO", "LEADS QUENTES", "LEADS FRIOS", "TOTAL"
    ]

    for col in colunas_numericas:
        if col not in df.columns:
            df[col] = 0
        else:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df

# =========================================================
# CARREGAR PROCESSOS (ANÁLISES)
# =========================================================
@st.cache_data(ttl=10)
def carregar_processos():
    dfp = pd.read_csv(CSV_PROCESSOS)
    dfp.columns = [c.strip().upper() for c in dfp.columns]

    if "DATA" in dfp.columns:
        dfp["DATA"] = pd.to_datetime(dfp["DATA"], dayfirst=True, errors="coerce")
    elif "DIA" in dfp.columns:
        dfp["DATA"] = pd.to_datetime(dfp["DIA"], dayfirst=True, errors="coerce")
    else:
        dfp["DATA"] = pd.NaT

    dfp = tratar_data_base(dfp)

    possiveis_status = [
        "SITUAÇÃO", "SITUACAO", "STATUS", "SITUAÇÃO ATUAL", "SITUACAO ATUAL",
        "SITUAÇÃO DA ANÁLISE", "SITUACAO DA ANALISE", "STATUS DA ANALISE", "STATUS DA ANÁLISE"
    ]

    col_status = next((c for c in possiveis_status if c in dfp.columns), None)

    if col_status:
        dfp["STATUS_ORIGINAL"] = dfp[col_status].fillna("").astype(str).str.upper().str.strip()
    else:
        dfp["STATUS_ORIGINAL"] = ""

    dfp["STATUS_BASE"] = "OUTROS"
    s = dfp["STATUS_ORIGINAL"]

    # Mapeamento inteligente de status
    dfp.loc[s == "EM ANÁLISE", "STATUS_BASE"] = "EM ANÁLISE"
    dfp.loc[s == "REANÁLISE", "STATUS_BASE"] = "REANÁLISE"
    dfp.loc[s == "APROVAÇÃO", "STATUS_BASE"] = "APROVADO"
    dfp.loc[s == "APROVADO BACEN", "STATUS_BASE"] = "APROVADO BACEN"
    dfp.loc[s == "APROVADO COM RESTRIÇÃO", "STATUS_BASE"] = "APROVADO COM RESTRIÇÃO"
    dfp.loc[s == "VENDA GERADA", "STATUS_BASE"] = "VENDA GERADA"
    dfp.loc[s == "VENDA INFORMADA", "STATUS_BASE"] = "VENDA INFORMADA"
    
    dfp.loc[s.str.contains("PENDEN", na=False), "STATUS_BASE"] = "PENDÊNCIA"
    dfp.loc[s.str.contains("REPROV", na=False), "STATUS_BASE"] = "REPROVADO"

    # Mapeamento flexível de Origem
    possiveis_origens = ["ORIGEM", "ORIGEM LEAD", "CANAL", "MEIO", "COMO CONHECEU", "ORIGEM DO CLIENTE", "ORIGEM DO LEAD"]
    col_origem = next((c for c in possiveis_origens if c in dfp.columns), None)
    
    if col_origem:
        dfp["ORIGEM"] = dfp[col_origem].fillna("").astype(str).str.upper().str.strip()
    else:
        dfp["ORIGEM"] = ""

    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in dfp.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in dfp.columns), None)

    if col_nome:
        dfp["NOME_CLIENTE_BASE"] = dfp[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
    else:
        dfp["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"

    if col_cpf:
        dfp["CPF_CLIENTE_BASE"] = dfp[col_cpf].fillna("").astype(str).str.replace(r"\D", "", regex=True)
    else:
        dfp["CPF_CLIENTE_BASE"] = ""

    dfp["CHAVE_CLIENTE"] = dfp["NOME_CLIENTE_BASE"] + " | " + dfp["CPF_CLIENTE_BASE"]

    return dfp

# =========================================================
# CARREGAMENTO INICIAL
# =========================================================
df = carregar_base()
df_processos = carregar_processos()

st.title("📞  Produção Comercial")
st.caption("Controle operacional diário de prospecção comercial")

if df.empty:
    st.warning("Sem dados.")
    st.stop()

df = df[df["DATA"].notna()].copy()

if df.empty:
    st.warning("Sem datas válidas.")
    st.stop()

# =========================================================
# SIDEBAR / FILTROS
# =========================================================
st.sidebar.title("Filtros 🔎")

modo_periodo = st.sidebar.radio(
    "Modo de filtro",
    ["Por DATA BASE", "Por DATA"],
    index=0
)

if modo_periodo == "Por DATA BASE":
    bases_df = df[["DATA_BASE", "DATA_BASE_LABEL"]].dropna(subset=["DATA_BASE"]).drop_duplicates().sort_values("DATA_BASE")
    opcoes_base = bases_df["DATA_BASE_LABEL"].tolist()
    ultima_base = opcoes_base[-1]

    data_base_sel = st.sidebar.selectbox("DATA BASE", opcoes_base, index=opcoes_base.index(ultima_base))
    df = df[df["DATA_BASE_LABEL"] == data_base_sel].copy()

    data_ini = df["DATA"].min().date()
    data_fim = df["DATA"].max().date()
else:
    data_min = df["DATA"].min().date()
    data_max = df["DATA"].max().date()

    periodo = st.sidebar.date_input("Período", value=(data_min, data_max), min_value=data_min, max_value=data_max)

    if isinstance(periodo, tuple):
        data_ini, data_fim = periodo
    else:
        data_ini = data_fim = periodo

    df = df[(df["DATA"].dt.date >= data_ini) & (df["DATA"].dt.date <= data_fim)].copy()

# =========================================================
# FILTRAGEM E RECONSTRUÇÃO DE DADOS EM BRANCO (HISTÓRICO)
# =========================================================
df_processos = df_processos[df_processos["DATA"].notna()].copy()
df_processos_periodo = df_processos[(df_processos["DATA"].dt.date >= data_ini)].copy()

if not df_processos_periodo.empty:
    df_processos_periodo = df_processos_periodo.sort_values(by="DATA", ascending=True)
    # Copia inteligentemente dados vazios (como origem) de linhas passadas do mesmo cliente
    for col_propagate in ["ORIGEM", "CORRETOR", "GERENTE", "NOME_CLIENTE_BASE"]:
        if col_propagate in df_processos_periodo.columns:
            df_processos_periodo[col_propagate] = df_processos_periodo[col_propagate].astype(str).str.strip().replace("", None).replace("NAN", None).replace("NONE", None)
            df_processos_periodo[col_propagate] = df_processos_periodo.groupby("CHAVE_CLIENTE")[col_propagate].ffill()
            df_processos_periodo[col_propagate] = df_processos_periodo.groupby("CHAVE_CLIENTE")[col_propagate].bfill()
            df_processos_periodo[col_propagate] = df_processos_periodo[col_propagate].fillna("")

# =========================================================
# CÁLCULOS OPERACIONAIS
# =========================================================
df["TOTAL_CALCULADO"] = df["ATENDEU"] + df["WHATSAPP ENVIADO"] + df["CONTATO INVÁLIDO"]
df["TOTAL"] = df["TOTAL"].fillna(0)
df.loc[df["TOTAL"] == 0, "TOTAL"] = df.loc[df["TOTAL"] == 0, "TOTAL_CALCULADO"]

total_atendeu = int(df["ATENDEU"].sum())
total_prospect = int(df["PROSPECT"].sum())
total_whatsapp = int(df["WHATSAPP ENVIADO"].sum())
total_invalido = int(df["CONTATO INVÁLIDO"].sum())
total_leads_quentes = int(df["LEADS QUENTES"].sum())
total_leads_frios = int(df["LEADS FRIOS"].sum())
total_operacional = int(df["TOTAL"].sum())

taxa_prospect = (total_prospect / total_operacional) * 100 if total_operacional > 0 else 0

# =========================================================
# LÓGICA DE CONTAGEM PELA ÚLTIMA LINHA REAL DE CADA CLIENTE
# =========================================================
if not df_processos_periodo.empty:
    df_ultimos_status = df_processos_periodo.groupby("CHAVE_CLIENTE")["STATUS_BASE"].last().reset_index()
    df_ultimas_origens = df_processos_periodo.groupby("CHAVE_CLIENTE")["ORIGEM"].last().reset_index()
    df_clientes_unicos = pd.merge(df_ultimos_status, df_ultimas_origens, on="CHAVE_CLIENTE", how="left")
else:
    df_clientes_unicos = pd.DataFrame(columns=["CHAVE_CLIENTE", "STATUS_BASE", "ORIGEM"])

total_clientes = int(df_clientes_unicos["CHAVE_CLIENTE"].nunique())
em_analise = int(df_clientes_unicos["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"]).sum())
aprovacoes = int((df_clientes_unicos["STATUS_BASE"] == "APROVADO").sum())
aprovado_bacen = int((df_clientes_unicos["STATUS_BASE"] == "APROVADO BACEN").sum())
aprovado_restricao = int((df_clientes_unicos["STATUS_BASE"] == "APROVADO COM RESTRIÇÃO").sum())
vendas = int(df_clientes_unicos["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"]).sum())
pendencias = int((df_clientes_unicos["STATUS_BASE"] == "PENDÊNCIA").sum())
reprovacoes = int((df_clientes_unicos["STATUS_BASE"] == "REPROVADO").sum())

# =========================================================
# QUADRO DE ORIGENS (INCLUI EM ANÁLISE, REANÁLISE E PENDÊNCIA)
# =========================================================
df_analises_ativas = df_clientes_unicos[df_clientes_unicos["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE", "PENDÊNCIA"])].copy()
total_em_analise_estrito = len(df_analises_ativas)

origens_alvo = ["INDICAÇÃO", "ORGÂNICO", "LISTA", "C2S", "INSTAGRAM", "TRÁFEGO"]
recap_origens = {}

for orig in origens_alvo:
    qtd = int((df_analises_ativas["ORIGEM"] == orig).sum())
    pct = (qtd / total_em_analise_estrito * 100) if total_em_analise_estrito > 0 else 0
    recap_origens[orig] = {"qtd": qtd, "pct": pct}

# =========================================================
# BLOCOS VISUAIS: CARDS OPERACIONAIS
# =========================================================
c1, c2, c3, c4 = st.columns(4)
c1.metric("📞 Total Operacional", total_operacional)
c2.metric("🔥 Leads Quentes", total_leads_quentes)
c3.metric("❄️ Leads Frios", total_leads_frios)
c4.metric("📊 Taxa Prospect", f"{taxa_prospect:.1f}%")

st.markdown("---")
p1, p2, p3, p4 = st.columns(4)
p1.metric("✅ Atendeu", total_atendeu)
p2.metric("🔥 Prospect", total_prospect)
p3.metric("💬 WhatsApp", total_whatsapp)
p4.metric("🚫 Inválido", total_invalido)

# =========================================================
# CARDS DE RESULTADO DOS PROCESSOS
# =========================================================
st.markdown("---")
st.subheader("🎯 Resultado dos Processos")

st.markdown("##### ⏳ Fila Operacional")
r_col1, r_col2, r_col3, r_col4 = st.columns(4)
r_col1.metric("👥 Total de Clientes únicos", total_clientes)
r_col2.metric("📄 Em Análise / Reanálise", em_analise)
r_col3.metric("⏳ Pendências", pendencias)
r_col4.metric("❌ Reprovações", reprovacoes)

st.markdown("##### 🚀 Conversões")
r_col5, r_col6, r_col7, r_col8 = st.columns(4)
r_col5.metric("✅ Aprovações Puras", aprovacoes)
r_col6.metric("🟡 Aprov. com Restrição", aprovado_restricao)
r_col7.metric("🏦 Aprovado BACEN", aprovado_bacen)
r_col8.metric("💰 Vendas Concluídas", vendas)

# =========================================================
# QUADRO: ORIGENS DAS ANÁLISES ATIVAS & PENDENTES
# =========================================================
st.markdown("---")
st.subheader(f"🧠 Origem das Análises Ativas & Pendentes (Total: {total_em_analise_estrito})")

o1, o2, o3 = st.columns(3)
o1.metric("📢 Indicação", recap_origens["INDICAÇÃO"]["qtd"], delta=f"{recap_origens['INDICAÇÃO']['pct']:.1f}% na fila", delta_color="off")
o2.metric("🌱 Orgânico", recap_origens["ORGÂNICO"]["qtd"], delta=f"{recap_origens['ORGÂNICO']['pct']:.1f}% na fila", delta_color="off")
o3.metric("📋 Lista", recap_origens["LISTA"]["qtd"], delta=f"{recap_origens['LISTA']['pct']:.1f}% na fila", delta_color="off")

o4, o5, o6 = st.columns(3)
o4.metric("💻 C2S", recap_origens["C2S"]["qtd"], delta=f"{recap_origens['C2S']['pct']:.1f}% na fila", delta_color="off")
o5.metric("📸 Instagram", recap_origens["INSTAGRAM"]["qtd"], delta=f"{recap_origens['INSTAGRAM']['pct']:.1f}% na fila", delta_color="off")
o6.metric("🎯 Tráfego", recap_origens["TRÁFEGO"]["qtd"], delta=f"{recap_origens['TRÁFEGO']['pct']:.1f}% na fila", delta_color="off")

# =========================================================
# GRÁFICO: EVOLUÇÃO DIÁRIA
# =========================================================
st.markdown("---")
st.subheader("📈 Evolução diária")

chart = (
    alt.Chart(df)
    .transform_fold(
        ["ATENDEU", "PROSPECT", "WHATSAPP ENVIADO", "CONTATO INVÁLIDO", "LEADS QUENTES"],
        as_=["Tipo", "Quantidade"]
    )
    .mark_line(point=True)
    .encode(
        x=alt.X("DATA:T", title="Data"),
        y=alt.Y("Quantidade:Q", title="Quantidade"),
        color="Tipo:N"
    )
    .properties(height=450)
)
st.altair_chart(chart, use_container_width=True)

# =========================================================
# TABELA 1: PRODUÇÃO OPERACIONAL DETALHADA
# =========================================================
st.markdown("---")
st.subheader("📋 Production Detalhada")

df_exibir = df.copy()
df_exibir["DATA"] = df_exibir["DATA"].dt.strftime("%d/%m/%Y")
colunas_exibir = ["DATA", "DATA_BASE_LABEL", "ATENDEU", "PROSPECT", "WHATSAPP ENVIADO", "CONTATO INVÁLIDO", "LEADS QUENTES", "LEADS FRIOS", "TOTAL"]
colunas_exibir = [c for c in colunas_exibir if c in df_exibir.columns]

df_exibir = df_exibir[colunas_exibir].copy()
df_exibir = df_exibir.rename(columns={"DATA_BASE_LABEL": "DATA BASE"})

for col in df_exibir.columns:
    df_exibir[col] = df_exibir[col].astype(str)

st.dataframe(df_exibir, use_container_width=True, hide_index=True)

# =========================================================
# MÉDIAS DIÁRIAS
# =========================================================
st.markdown("---")
st.subheader("📌 Média diária")

dias = df["DATA"].dt.date.nunique()
media_total = total_operacional / dias if dias > 0 else 0
media_atendeu = total_atendeu / dias if dias > 0 else 0
media_prospect = total_prospect / dias if dias > 0 else 0
media_quente = total_leads_quentes / dias if dias > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Média Operacional", f"{media_total:.1f}")
m2.metric("Média Atendeu", f"{media_atendeu:.1f}")
m3.metric("Média Prospect", f"{media_prospect:.1f}")
m4.metric("Média Leads Quentes", f"{media_quente:.1f}")

# =========================================================
# TABELA 2: LISTAGEM DE ANÁLISES ATUALIZADAS (Último Status)
# =========================================================
st.markdown("---")
st.subheader("📋 Situação Real das Análises (Último Status)")

if not df_processos_periodo.empty:
    df_lista_analises = df_processos_periodo.sort_values(by="DATA", ascending=True)
    df_lista_analises = df_lista_analises.drop_duplicates(subset=["CHAVE_CLIENTE"], keep="last").copy()
    
    if "DATA" in df_lista_analises.columns:
        df_lista_analises["DATA_FORMATADA"] = df_lista_analises["DATA"].dt.strftime("%d/%m/%Y")
    else:
        df_lista_analises["DATA_FORMATADA"] = ""
        
    colunas_finais = []
    nomes_amigaveis = {}
    
    if "DATA_FORMATADA" in df_lista_analises.columns:
        colunas_finais.append("DATA_FORMATADA")
        nomes_amigaveis["DATA_FORMATADA"] = "DATA REGISTRO"
        
    if "NOME_CLIENTE_BASE" in df_lista_analises.columns:
        colunas_finais.append("NOME_CLIENTE_BASE")
        nomes_amigaveis["NOME_CLIENTE_BASE"] = "CLIENTE"
        
    if "STATUS_BASE" in df_lista_analises.columns:
        colunas_finais.append("STATUS_BASE")
        nomes_amigaveis["STATUS_BASE"] = "SITUAÇÃO ATUAL"
        
    if "ORIGEM" in df_lista_analises.columns:
        colunas_finais.append("ORIGEM")
        nomes_amigaveis["ORIGEM"] = "ORIGEM"
        
    for col_extra in ["CORRETOR", "GERENTE"]:
        if col_extra in df_lista_analises.columns:
            colunas_finais.append(col_extra)
            nomes_amigaveis[col_extra] = col_extra

    df_tabela_analises = df_lista_analises[colunas_finais].copy()
    df_tabela_analises = df_tabela_analises.rename(columns=nomes_amigaveis)
    
    st.dataframe(df_tabela_analises, use_container_width=True, hide_index=True)
else:
    st.info("Nenhuma análise encontrada no banco de dados a partir da data inicial informada.")