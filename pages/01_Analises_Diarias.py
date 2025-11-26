import streamlit as st
import pandas as pd
from datetime import date, datetime
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Análises Diárias – MR Imóveis",
    page_icon="📅",
    layout="wide",
)

# AUTO-REFRESH DISCRETO (30 SEGUNDOS)
st_autorefresh(interval=30 * 1000, key="analises_refresh")

# ---------------------------------------------------------
# SIMULAÇÃO DE DADOS (substituir pela fonte real quando quiser)
# ---------------------------------------------------------
data_hoje = date.today()

dados = {
    "CORRETOR": ["Ricardo", "Marcia", "Ivan", "Ricardo", "Ivan", "Ricardo"],
    "DATA": [data_hoje] * 6
}

df = pd.DataFrame(dados)

# ---------------------------------------------------------
# TÍTULO
# ---------------------------------------------------------
st.title("📊 Análises de Crédito do Dia")

# ---------------------------------------------------------
# FILTROS
# ---------------------------------------------------------
corretores = ["Todos"] + sorted(df["CORRETOR"].unique().tolist())
corretor_selecionado = st.selectbox("Filtrar por corretor:", corretores)

if corretor_selecionado != "Todos":
    df = df[df["CORRETOR"] == corretor_selecionado]

# ---------------------------------------------------------
# TABELA DE ANÁLISES
# ---------------------------------------------------------
df_em_analise = df.copy()

def criar_coluna_rank(tamanho):
    return [f"{i+1}º" for i in range(tamanho)]

df_corretor = df_em_analise.groupby("CORRETOR").size().reset_index(name="ANÁLISES")
df_corretor = df_corretor.sort_values("ANÁLISES", ascending=False).reset_index(drop=True)
df_corretor.insert(0, "POSIÇÃO", criar_coluna_rank(len(df_corretor)))
df_corretor = df_corretor.rename(columns={"CORRETOR": "Corretor", "ANÁLISES": "Análises no dia"})

st.table(df_corretor)

# ---------------------------------------------------------
# RODAPÉ
# ---------------------------------------------------------
st.markdown("---")
st.caption("Nenhum de nós é tão bom quanto todos nós juntos! • Dashboard MR Imóveis • Gestão à Vista • Atualização suave a cada 30s")
