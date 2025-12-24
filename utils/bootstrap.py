import streamlit as st
import uuid
import json
from pathlib import Path

from login import tela_login
from utils.data_loader import carregar_dados_planilha
from utils.notificacoes_json import processar_eventos


# -------------------------------------------------
# CAMINHO DO JSON DE NOTIFICAÇÕES
# -------------------------------------------------
CAMINHO_NOTIFICACOES = Path("data/notificacoes.json")


# -------------------------------------------------
# UTILIDADES
# -------------------------------------------------
def carregar_notificacoes_corretor(nome_corretor: str) -> list:
    if not CAMINHO_NOTIFICACOES.exists():
        return []

    try:
        with open(CAMINHO_NOTIFICACOES, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return []

    return [
        n for n in data.get(nome_corretor.upper(), [])
        if not n.get("lido", False)
    ]


def marcar_como_lido(nome_corretor: str, alerta_id: str):
    if not CAMINHO_NOTIFICACOES.exists():
        return

    try:
        with open(CAMINHO_NOTIFICACOES, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception:
        return

    lista = data.get(nome_corretor.upper(), [])

    for n in lista:
        if n.get("id") == alerta_id:
            n["lido"] = True
            break

    data[nome_corretor.upper()] = lista

    with open(CAMINHO_NOTIFICACOES, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -------------------------------------------------
# BOOTSTRAP GLOBAL
# -------------------------------------------------
def iniciar_app():
    """
    Bootstrap global do app:
    - controla login
    - processa eventos (JSON)
    - exibe notificações persistentes
    """

    # -------------------------------------------------
    # LOGIN
    # -------------------------------------------------
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        tela_login()
        st.stop()

    # -------------------------------------------------
    # ID ÚNICO DA PÁGINA (ANTI-COLISÃO)
    # -------------------------------------------------
    if "page_scope_id" not in st.session_state:
        st.session_state.page_scope_id = str(uuid.uuid4())

    page_scope_id = st.session_state.page_scope_id

    # -------------------------------------------------
    # CARREGA BASE E PROCESSA EVENTOS
    # -------------------------------------------------
    df = carregar_dados_planilha()
    processar_eventos(df)

    # -------------------------------------------------
    # CONTEXTO DO USUÁRIO
    # -------------------------------------------------
    nome_corretor = st.session_state.nome_usuario.upper().strip()
    perfil = st.session_state.get("perfil", "corretor")

    if perfil not in {"corretor", "gestor", "admin"}:
        return

    # -------------------------------------------------
    # CARREGA NOTIFICAÇÕES PENDENTES
    # -------------------------------------------------
    notificacoes = carregar_notificacoes_corretor(nome_corretor)

    # -------------------------------------------------
    # RENDERIZAÇÃO
    # -------------------------------------------------
    if notificacoes:
        st.markdown("### 🔔 Atualizações Recentes")

        for alerta in notificacoes:
            col1, col2 = st.columns([9, 1])

            with col1:
                if alerta["tipo"] == "NOVO_CLIENTE":
                    st.info(
                        f"🆕 **Novo cliente**  \n"
                        f"**{alerta['cliente']}** — {alerta['status']}"
                    )
                else:
                    st.warning(
                        f"🔄 **Atualização de status**  \n"
                        f"**{alerta['cliente']}**  \n"
                        f"{alerta['de']} → **{alerta['para']}**"
                    )

            with col2:
                if st.button(
                    "❌",
                    key=f"fechar_alerta_{page_scope_id}_{alerta['id']}"
                ):
                    marcar_como_lido(nome_corretor, alerta["id"])
                    st.rerun()
