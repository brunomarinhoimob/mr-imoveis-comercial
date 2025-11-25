import streamlit as st
import pandas as pd
from datetime import timedelta, date

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Alertas – MR Imóveis",
    page_icon="🔴",
    layout="wide",
)

# Cabeçalho
col_titulo, col_logo = st.columns([3, 1])
with col_titulo:
    st.title("🔴 Alertas da Operação Comercial")
with col_logo:
    try:
        st.image("logo_mr.png", use_column_width=True)
    except Exception:
        pass

st.markdown(
    "Monitoramento de corretores, clientes em pendência e vendas informadas paradas, "
    "para o gestor cobrar e destravar o funil."
)

# ---------------------------------------------------------
# PLANILHA
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"

def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date

@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)
    df.columns = [c.strip().upper() for c in df.columns]

    # DIA / DATA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    df["DT_BASE"] = pd.to_datetime(df["DIA"], errors="coerce")

    # CORRETOR / EQUIPE
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # SITUAÇÃO
    possiveis_cols_situacao = [
        "SITUAÇÃO", "SITUACAO", "SITUAÇÃO ATUAL", "SITUACAO ATUAL",
        "STATUS"
    ]
    col_sit = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_sit:
        status = df[col_sit].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        df.loc[status.str.contains("PEND", na=False), "STATUS_BASE"] = "PENDÊNCIA"

    # CLIENTE / CPF
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

    df["NOME_CLIENTE_BASE"] = (
        df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        if col_nome else "NÃO INFORMADO"
    )

    df["CPF_CLIENTE_BASE"] = (
        df[col_cpf].fillna("").astype(str).str.replace(r"\D", "", regex=True)
        if col_cpf else ""
    )

    return df

df = carregar_dados()
if df.empty:
    st.error("Erro ao carregar base da planilha.")
    st.stop()

# ---------------------------------------------------------
# FILTRO DE EQUIPE
# ---------------------------------------------------------
st.sidebar.title("Filtros 🔎")

lista_equipes = sorted(df["EQUIPE"].unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)

if equipe_sel != "Todas":
    df = df[df["EQUIPE"] == equipe_sel]

if df.empty:
    st.warning("Nenhum registro encontrado para esta equipe.")
    st.stop()

# Datas principais
hoje = date.today()
data_ref_geral_ts = df["DT_BASE"].max()

# ---------------------------------------------------------
# 1) ALERTA DE 3+ DIAS SEM ANÁLISE (JANELA 30 DIAS)
# ---------------------------------------------------------
st.markdown("## 🧑‍💻 Corretores sem análises nos últimos 3 dias (janela de 30 dias)")

df_analise_base = df[df["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"])].copy()

if df_analise_base.empty:
    st.info("Nenhuma análise encontrada para calcular este alerta.")
else:
    data_ref = df_analise_base["DT_BASE"].max()
    data_inicio_janela = data_ref - timedelta(days=30)

    # CORREÇÃO AQUI
    df_analise_30 = df_analise_base[
        (df_analise_base["DT_BASE"] >= data_inicio_janela) &
        (df_analise_base["DT_BASE"] <= data_ref)
    ].copy()

    if df_analise_30.empty:
        st.info("Nenhuma análise encontrada dentro dos últimos 30 dias.")
    else:
        ultima_analise = (
            df_analise_30.dropna(subset=["DT_BASE"])
            .groupby("CORRETOR", as_index=False)["DT_BASE"]
            .max()
        )

        registros = []
        for cor in sorted(df["CORRETOR"].unique()):
            linha = ultima_analise[ultima_analise["CORRETOR"] == cor]

            if linha.empty:
                continue  # não fez análise na janela → não entra

            ultima_data = linha["DT_BASE"].iloc[0]
            dias_sem = (data_ref - ultima_data).days

            if dias_sem >= 3:
                registros.append({
                    "CORRETOR": cor,
                    "ÚLTIMA ANÁLISE": ultima_data.date().strftime("%d/%m/%Y"),
                    "DIAS SEM ANÁLISE": dias_sem
                })

        if not registros:
            st.success("Nenhum corretor está há 3 dias ou mais sem análises.")
        else:
            df_alert = pd.DataFrame(registros).sort_values(
                "DIAS SEM ANÁLISE", ascending=False
            )
            st.dataframe(df_alert, use_container_width=True)

# ---------------------------------------------------------
# 2) CLIENTES EM PENDÊNCIA (ÚLTIMA AÇÃO +2 DIAS)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## ⏳ Clientes em pendência há mais de 2 dias")

df["CHAVE_CLIENTE"] = df["NOME_CLIENTE_BASE"] + " | " + df["CPF_CLIENTE_BASE"]

df_last = (
    df.dropna(subset=["DT_BASE"])
    .sort_values("DT_BASE")
    .groupby("CHAVE_CLIENTE", as_index=False)
    .tail(1)
)

if df_last.empty:
    st.info("Não foi possível identificar últimas ações.")
else:
    df_pend = df_last[df_last["STATUS_BASE"] == "PENDÊNCIA"].copy()

    if df_pend.empty:
        st.success("Nenhum cliente está em pendência.")
    else:
        df_pend["DIAS_DESDE_PENDENCIA"] = (
            hoje - df_pend["DT_BASE"].dt.date
        ).dt.days

        df_pend = df_pend[df_pend["DIAS_DESDE_PENDENCIA"] >= 2]

        if df_pend.empty:
            st.success("Não há clientes há 2+ dias em pendência.")
        else:
            df_view = df_pend[
                ["NOME_CLIENTE_BASE", "CPF_CLIENTE_BASE", "EQUIPE", "CORRETOR",
                 "DT_BASE", "DIAS_DESDE_PENDENCIA"]
            ].copy()

            df_view["DT_BASE"] = df_view["DT_BASE"].dt.strftime("%d/%m/%Y")

            st.dataframe(
                df_view.sort_values("DIAS_DESDE_PENDENCIA", ascending=False),
                use_container_width=True
            )

# ---------------------------------------------------------
# 3) VENDAS INFORMADAS HÁ +5 DIAS
# ---------------------------------------------------------
st.markdown("---")
st.markdown("## 📝 Vendas informadas há mais de 5 dias (sem virar venda gerada)")

df_vinfo = df_last[df_last["STATUS_BASE"] == "VENDA INFORMADA"].copy()

if df_vinfo.empty:
    st.success("Nenhuma venda informada pendente.")
else:
    df_vinfo["DIAS_DESDE_INFO"] = (
        data_ref_geral_ts - df_vinfo["DT_BASE"]
    ).dt.days

    df_vinfo = df_vinfo[df_vinfo["DIAS_DESDE_INFO"] >= 5]

    if df_vinfo.empty:
        st.success("Nenhuma venda informada presa há 5+ dias.")
    else:
        df_view = df_vinfo[
            ["NOME_CLIENTE_BASE", "CPF_CLIENTE_BASE", "EQUIPE", "CORRETOR",
             "DT_BASE", "DIAS_DESDE_INFO"]
        ].copy()
        df_view["DT_BASE"] = df_view["DT_BASE"].dt.strftime("%d/%m/%Y")

        st.dataframe(
            df_view.sort_values("DIAS_DESDE_INFO", ascending=False),
            use_container_width=True
        )
