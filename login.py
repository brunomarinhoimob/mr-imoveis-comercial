import streamlit as st
import os
import json
from pathlib import Path

# Bootstrap inicial (só pra popular o users.json na primeira vez / quando faltar gente)
from auth_users import USUARIOS

CAMINHO_USERS = Path("users.json")


# =========================================================
# USERS.JSON (única fonte de verdade do login)
# =========================================================
def carregar_users_json() -> dict:
    if CAMINHO_USERS.exists():
        try:
            with open(CAMINHO_USERS, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            # garante chaves em lowercase
            return {str(k).strip().lower(): v for k, v in data.items()}
        except Exception:
            return {}
    return {}


def salvar_users_json(data: dict):
    with open(CAMINHO_USERS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def bootstrap_users_json():
    """
    Garante que users.json existe e tem pelo menos os usuários do auth_users.py.
    IMPORTANTE: não sobrescreve senha já alterada no JSON.
    """
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
            # garante campos mínimos sem mexer na senha atual do JSON
            users[k]["nome"] = users[k].get("nome") or info.get("nome", k.upper())
            users[k]["perfil"] = users[k].get("perfil") or info.get("perfil", "corretor")
            if "senha" not in users[k]:
                users[k]["senha"] = str(info.get("senha", ""))

    salvar_users_json(users)


def validar_login(usuario: str, senha: str):
    """
    Retorna (ok, user_dict)
    user_dict precisa ter: nome, perfil
    """
    usuario = (usuario or "").strip().lower()
    senha = (senha or "").strip()

    users_json = carregar_users_json()
    user = users_json.get(usuario)

    # valida SOMENTE no users.json (fonte única)
    if user and senha == str(user.get("senha", "")).strip():
        return True, user

    return False, None


# =========================================================
# TELA LOGIN
# =========================================================
def tela_login():

    # garante que o users.json existe e está populado
    bootstrap_users_json()

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
            overflow: hidden;
        }

        .login-wrap {
            max-width: 460px;
            margin: 0 auto;
            padding: 22px;
        }

        .login-card {
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(14px);
            padding: 28px;
            border-radius: 18px;
            border: 1px solid rgba(148, 163, 184, 0.22);
            box-shadow: 0 18px 60px rgba(0,0,0,0.55);
        }

        .login-title {
            font-size: 1.4rem;
            font-weight: 800;
            color: #e5e7eb;
            margin-bottom: 4px;
            text-align: center;
        }

        .login-sub {
            font-size: 0.9rem;
            color: #cbd5e1;
            margin-bottom: 18px;
            text-align: center;
        }

        .frase {
            font-size: 1.0rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            color: #e5e7eb;
            margin: 16px 0 18px 0;
            text-transform: uppercase;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div class='login-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)

    # Logo (se existir)
    if os.path.exists("assets/logo_mr.png"):
        st.image("assets/logo_mr.png", use_container_width=True)
    elif os.path.exists("logo_mr.png"):
        st.image("logo_mr.png", use_container_width=True)

    st.markdown("<div class='login-title'>Dashboard MR</div>", unsafe_allow_html=True)
    st.markdown("<div class='login-sub'>Acesse com seu usuário e senha</div>", unsafe_allow_html=True)
    st.markdown("<div class='frase'>MR IMÓVEIS</div>", unsafe_allow_html=True)

    usuario = st.text_input("Usuário", placeholder="ex: marcello.barbosa")
    senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")

    if st.button("Entrar", use_container_width=True):
        ok, user = validar_login(usuario, senha)

        if ok:
            st.session_state.logado = True
            st.session_state.usuario = (usuario or "").strip().lower()
            st.session_state.nome_usuario = user.get("nome", (usuario or "").strip().upper())
            st.session_state.perfil = user.get("perfil", "corretor")
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
