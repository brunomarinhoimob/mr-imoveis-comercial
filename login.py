import streamlit as st
import os
import json
from pathlib import Path
import base64

# Bootstrap inicial
from utils.auth_users import USUARIOS

CAMINHO_USERS = Path("users.json")


# =========================================================
# USERS.JSON
# =========================================================
def carregar_users_json() -> dict:
    if CAMINHO_USERS.exists():
        try:
            with open(CAMINHO_USERS, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return {str(k).strip().lower(): v for k, v in data.items()}
        except Exception:
            return {}
    return {}


def salvar_users_json(data: dict):
    with open(CAMINHO_USERS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def bootstrap_users_json():
    users = carregar_users_json()

    for login, info in (USUARIOS or {}).items():
        k = str(login).strip().lower()

        if not k:
            continue

        if k not in users:
            users[k] = {
                "nome": info.get("nome", k.upper()),
                "senha": str(info.get("senha", "")),
                "perfil": info.get("perfil", "corretor"),
            }
        else:
            users[k]["nome"] = users[k].get("nome") or info.get("nome", k.upper())
            users[k]["perfil"] = users[k].get("perfil") or info.get("perfil", "corretor")

            if "senha" not in users[k]:
                users[k]["senha"] = str(info.get("senha", ""))

    salvar_users_json(users)


def validar_login(usuario: str, senha: str):
    usuario = (usuario or "").strip().lower()
    senha = (senha or "").strip()

    users_json = carregar_users_json()
    user = users_json.get(usuario)

    if user and senha == str(user.get("senha", "")).strip():
        return True, user

    return False, None


def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


# =========================================================
# TELA LOGIN
# =========================================================
def tela_login():

    bootstrap_users_json()

    st.markdown(
        """
        <style>

        section[data-testid="stSidebar"] {
            display: none;
        }

        header[data-testid="stHeader"] {
            display: none;
        }

        html, body, [class*="css"] {
            background: #000000;
        }

        .stApp {
            background: #000000;
        }

        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }

        .login-wrap {
            max-width: 520px;
            margin: 0 auto;
            padding-top: 2vh;
        }

        .login-card {
            background: rgba(10, 10, 10, 0.92);
            padding: 32px;
            border-radius: 24px;
            border: 1px solid rgba(255, 215, 0, 0.12);
            box-shadow: 0 20px 80px rgba(0,0,0,0.65);
        }

        .logo-wrap {
            display: flex;
            justify-content: center;
            margin-bottom: 25px;
        }

        .logo-wrap img {
            width: 100%;
            max-width: 430px;
            display: block;
        }

        .login-title {
            text-align: center;
            font-size: 1.7rem;
            font-weight: 800;
            color: #f8fafc;
            margin-bottom: 6px;
        }

        .login-sub {
            text-align: center;
            color: #cbd5e1;
            margin-bottom: 26px;
            font-size: 0.95rem;
        }

        div[data-testid="stTextInput"] input {
            background-color: #111827;
            border: 1px solid #374151;
            color: white;
            border-radius: 12px;
        }

        div[data-testid="stTextInput"] label {
            color: #e5e7eb !important;
            font-weight: 600;
        }

        div[data-testid="stButton"] button {
            background: linear-gradient(90deg, #d4af37, #f5d76e);
            color: black;
            border: none;
            border-radius: 12px;
            font-weight: 800;
            height: 48px;
            font-size: 1rem;
            transition: 0.2s ease;
        }

        div[data-testid="stButton"] button:hover {
            transform: scale(1.01);
            filter: brightness(1.05);
        }

        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='login-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)

    # LOGO NOVA
    if os.path.exists("logo_bruno_marinho.jpg"):

        logo_base64 = image_to_base64("logo_bruno_marinho.jpg")

        st.markdown(
            f"""
            <div class="logo-wrap">
                <img src="data:image/jpg;base64,{logo_base64}">
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        "<div class='login-title'>Painel Comercial</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='login-sub'>Acesse sua central de performance</div>",
        unsafe_allow_html=True
    )

    usuario = st.text_input(
        "Usuário",
        placeholder="Digite seu usuário"
    )

    senha = st.text_input(
        "Senha",
        type="password",
        placeholder="Digite sua senha"
    )

    if st.button("Entrar", use_container_width=True):

        ok, user = validar_login(usuario, senha)

        if ok:
            st.session_state.logado = True
            st.session_state.usuario = (usuario or "").strip().lower()
            st.session_state.nome_usuario = user.get(
                "nome",
                (usuario or "").strip().upper()
            )
            st.session_state.perfil = user.get("perfil", "corretor")

            st.rerun()

        else:
            st.error("Usuário ou senha inválidos")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)