import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------
# CAMINHO DA LOGO — AGORA CORRETO
# ----------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = PROJECT_ROOT / "logo_mr.png"

# ----------------------------------------------------
# ESTILOS VISUAIS
# ----------------------------------------------------
st.markdown(
    """
    <style>
        .centered {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }

        .card {
            background-color: #111111;
            padding: 55px 40px;
            border-radius: 28px;
            width: 82%;
            max-width: 650px;
            box-shadow: 0px 0px 25px rgba(0,0,0,0.45);
        }

        .logo {
            width: 260px;
            margin-bottom: 25px;
        }

        .phrase {
            font-size: 20px;
            color: #e8e8e8;
            font-weight: 500;
            margin-top: 10px;
            line-height: 1.35;
        }

        .info {
            margin-top: 35px;
            font-size: 16px;
            color: #cfcfcf;
            line-height: 1.6;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# FUNÇÃO MÊS COMERCIAL
# ----------------------------------------------------
def obter_mes_comercial():
    try:
        df = pd.read_excel(PROJECT_ROOT / "base_vendas.xlsx")  # ajuste se necessário
        df["data_base"] = pd.to_datetime(df["data_base"], errors="coerce")
        ultima_data = df["data_base"].max()
        return ultima_data.strftime("%B/%Y").capitalize()
    except:
        return "Indefinido"


mes_comercial = obter_mes_comercial()
ultima_atualizacao = datetime.now().strftime("%d/%m/%Y • %H:%M")

# ----------------------------------------------------
# LAYOUT
# ----------------------------------------------------
st.markdown('<div class="centered">', unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)

# LOGO MR
try:
    st.image(str(LOGO_PATH), width=260)
except:
    st.error("Logo MR não encontrada no caminho raiz.")

# FRASE
st.markdown(
    """
    <div class="phrase">
        Nenhum de nós é tão bom quanto todos nós juntos.
    </div>
    """,
    unsafe_allow_html=True
)

# INFOS
st.markdown(
    f"""
    <div class="info">
        <b>Mês comercial:</b> {mes_comercial}<br>
        <b>Última atualização:</b> {ultima_atualizacao}
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
