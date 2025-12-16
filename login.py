import streamlit as st
import os
from auth_users import USUARIOS

def tela_login():

    # -------------------------
    # CSS (login clean)
    # -------------------------
    st.markdown(
        """
        <style>
        section[data-testid="stSidebar"] { display: none; }
        header[data-testid="stHeader"] { display: none; }

        html, body {
            height: 100%;
            margin: 0;
            overflow: hidden !important;
        }

        .stApp {
            height: 100vh;
            overflow: hidden !important;
        }

        .frase {
            font-size: 1.2rem;
            font-weight: 600;
            letter-spacing: 0.18em;
            color: #e5e7eb;
            margin: 16px 0 24px 0;
            text-transform: uppercase;
            text-align: center;
        }

        .login-card {
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(14px);
            padding: 28px;
            border-radius: 18px;
            border: 1px solid rgba(148,163,184,0.25);
            box-shadow: 0 25px 50px rgba(0,0,0,0.55);
        }

        button[kind="primary"], button[data-baseweb="button"] {
            border-radius: 999px !important;
            height: 46px;
            font-weight: 600;
            background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 50%, #0ea5e9 100%);
            border: none;
            box-shadow: 0 12px 28px rgba(37,99,235,0.45);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # -------------------------
    # Caminho da logo
    # -------------------------
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "logo_mr_hd.png")

    # Espaço vertical
    st.markdown("<div style='margin-top: 8vh'></div>", unsafe_allow_html=True)

    # -------------------------
    # Centralização
    # -------------------------
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        # -------- LOGO (FUNDO BRANCO CLEAN) --------
        if os.path.exists(logo_path):
            st.markdown(
                """
                <div style="
                    background:#ffffff;
                    border-radius:18px;
                    padding:12px 18px;
                    display:flex;
                    justify-content:center;
                    align-items:center;
                    margin-bottom:14px;
                ">
                """,
                unsafe_allow_html=True
            )
            st.image(logo_path, width=220)
            st.markdown("</div>", unsafe_allow_html=True)

        # -------- FRASE --------
        st.markdown(
            "<div class='frase'>INTELIGÊNCIA COMERCIAL</div>",
            unsafe_allow_html=True
        )

        # -------- CARD LOGIN --------
        st.markdown("<div class='login-card'>", unsafe_allow_html=True)

        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar", use_container_width=True):
    user = USUARIOS.get(usuario.lower())

    if user and senha == user["senha"]:
        st.session_state.logado = True
        st.session_state.usuario = usuario.lower()
        st.session_state.nome_usuario = user["nome"].upper()
        st.session_state.perfil = user["perfil"]
        st.rerun()
    else:
        st.error("Usuário ou senha inválidos")

        st.markdown("</div>", unsafe_allow_html=True)
