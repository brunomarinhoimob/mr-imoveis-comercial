import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------
# CAMINHOS
# ----------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = PROJECT_ROOT / "logo_mr.png"

# ----------------------------------------------------
# ESTILO GLOBAL (fundo escuro, centralizado)
# ----------------------------------------------------
st.markdown(
    """
    <style>
        .stApp {
            background-color: #050608;
        }
        .block-container {
            padding-top: 4rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# FUNÇÃO PARA BUSCAR MÊS COMERCIAL
# ----------------------------------------------------
def obter_mes_comercial():
    try:
        # 🔧 AJUSTE AQUI SE A PLANILHA ESTIVER EM OUTRO LUGAR
        df = pd.read_excel(PROJECT_ROOT / "base_vendas.xlsx")
        df["data_base"] = pd.to_datetime(df["data_base"], errors="coerce")
        ultima_data = df["data_base"].max()
        if pd.isna(ultima_data):
            return "Indefinido"
        return ultima_data.strftime("%B/%Y").capitalize()
    except Exception:
        return "Indefinido"


mes_comercial = obter_mes_comercial()
ultima_atualizacao = datetime.now().strftime("%d/%m/%Y • %H:%M")

# ----------------------------------------------------
# LAYOUT: CARD CENTRALIZADO
# ----------------------------------------------------
# 3 colunas para centralizar o card
col_esq, col_meio, col_dir = st.columns([1, 2, 1])

with col_meio:
    st.markdown(
        """
        <div style="
            background-color: #111111;
            border-radius: 28px;
            padding: 40px 30px;
            text-align: center;
            box-shadow: 0px 0px 25px rgba(0,0,0,0.45);
        ">
        """,
        unsafe_allow_html=True,
    )

    # LOGO MR
    try:
        st.image(str(LOGO_PATH), width=260)
    except Exception:
        st.markdown(
            "<p style='color:#ff4b4b; font-size:14px;'><b>Logo MR não encontrada.</b></p>",
            unsafe_allow_html=True,
        )

    # FRASE
    st.markdown(
        """
        <p style="
            font-size: 20px;
            color: #e8e8e8;
            font-weight: 500;
            margin-top: 20px;
            margin-bottom: 10px;
            line-height: 1.35;
        ">
            Nenhum de nós é tão bom quanto todos nós juntos.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # INFOS
    st.markdown(
        f"""
        <p style="margin-top: 30px; font-size: 16px; color: #cfcfcf; line-height: 1.6;">
            <b>Mês comercial:</b> {mes_comercial}<br>
            <b>Última atualização:</b> {ultima_atualizacao}
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
