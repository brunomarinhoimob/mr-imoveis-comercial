import streamlit as st
import os

def tela_login():
    # caminho absoluto da pasta do projeto
    base_dir = os.path.dirname(os.path.abspath(__file__))
    logo_path = os.path.join(base_dir, "assets", "logo_mr.png")

    st.markdown(
        """
        <style>
        .login-container {
            max-width: 420px;
            margin: auto;
            margin-top: 100px;
            text-align: center;
        }
        .login-box {
            background-color: #ffffff;
            padding: 32px;
            border-radius: 14px;
            box-shadow: 0px 6px 25px rgba(0,0,0,0.10);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="login-container">', unsafe_allow_html=True)

    # LOGO MR
    st.image(logo_path, width=300)

    st.markdown('<div class="login-box">', unsafe_allow_html=True)

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar", use_container_width=True):
        if usuario == "Adm" and senha == "123456":
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.markdown('</div></div>', unsafe_allow_html=True)
