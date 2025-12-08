import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------
# CAMINHOS
# ----------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_PATH = PROJECT_ROOT / "logo_mr.png"  # sua logo está na raiz do projeto

# ----------------------------------------------------
# ESTILO GLOBAL (fundo claro + card escuro central)
# ----------------------------------------------------
st.markdown(
    """
    <style>
        /* Fundo da área principal (deixa cara de feed/Instagram) */
        .stApp {
            background-color: #f3f4f6;
        }

        .block-container {
            padding-top: 4rem;
            padding-bottom: 4rem;
        }

        /* Card da home */
        .home-card {
            background-color: #090909;
            border-radius: 32px;
            padding: 40px 34px;
            max-width: 460px;
            margin: 0 auto;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.45);
        }

        .home-logo {
            margin-bottom: 28px;
        }

        .home-quote {
            font-size: 20px;
            font-weight: 600;
            color: #f5f5f5;
            text-align: left;
            line-height: 1.3;
            margin-bottom: 32px;
        }

        .home-footer {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            font-size: 14px;
            color: #d0d0d0;
        }

        .home-footer b {
            color: #ffffff;
        }

        /* Responsivo: em telas menores, footer quebra em duas linhas */
        @media (max-width: 768px) {
            .home-footer {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------
# FUNÇÃO PARA BUSCAR MÊS COMERCIAL
# ----------------------------------------------------
def obter_mes_comercial():
    """
    Tenta pegar a última data_base da planilha e transformar em mês/ano.
    Se não encontrar ou der erro, retorna 'Indefinido'.
    """
    try:
        # 🔧 AJUSTE AQUI O NOME/CAMINHO DA PLANILHA QUANDO SOUBER QUAL É
        # Exemplo: PROJECT_ROOT / "base_vendas.xlsx"
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
# LAYOUT: CARD ESTILO OPÇÃO 2
# ----------------------------------------------------

# colunas só pra garantir que fique centralizado
col_esq, col_meio, col_dir = st.columns([1, 2, 1])

with col_meio:
    st.markdown('<div class="home-card">', unsafe_allow_html=True)

    # LOGO MR
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=220, output_format="PNG", use_container_width=False)
    else:
        st.markdown(
            "<p style='color:#ff4b4b; font-size:13px; margin-bottom:20px;'><b>Logo MR não encontrada em logo_mr.png</b></p>",
            unsafe_allow_html=True,
        )

    # FRASE (um pouco menor pra logo dominar)
    st.markdown(
        """
        <div class="home-quote">
            Nenhum de nós é tão bom quanto todos nós juntos.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # RODAPÉ (mês comercial + última atualização)
    st.markdown(
        f"""
        <div class="home-footer">
            <div>
                <b>Mês comercial:</b><br>{mes_comercial}
            </div>
            <div>
                <b>Última atualização:</b><br>{ultima_atualizacao}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
