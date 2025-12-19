import streamlit as st
import uuid

from utils.notificacoes import verificar_notificacoes
from login import tela_login
from app_dashboard import carregar_dados_planilha


def iniciar_app():
    """
    Bootstrap global do app:
    - controla login
    - carrega base única do sistema
    - executa notificações
    - renderiza alertas fixos
    - evita colisão de keys entre páginas
    """

    # -------------------------------------------------
    # CONTROLE DE LOGIN (GLOBAL)
    # -------------------------------------------------
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        tela_login()
        st.stop()

    # -------------------------------------------------
    # ID ÚNICO POR PÁGINA (ANTI-COLISÃO DE KEYS)
    # -------------------------------------------------
    if "page_scope_id" not in st.session_state:
        st.session_state["page_scope_id"] = str(uuid.uuid4())

    page_scope_id = st.session_state["page_scope_id"]

    # -------------------------------------------------
    # CARREGA BASE ÚNICA (FONTE DA VERDADE)
    # -------------------------------------------------
    df = carregar_dados_planilha()

    # -------------------------------------------------
    # EXECUÇÃO DAS NOTIFICAÇÕES (BACKEND)
    # -------------------------------------------------
    verificar_notificacoes(df)

    # -------------------------------------------------
    # GARANTIA DE ESTRUTURA NO SESSION STATE
    # -------------------------------------------------
    if "alertas_fixos" not in st.session_state:
        st.session_state["alertas_fixos"] = []

    if "alertas_fixos_ids" not in st.session_state:
        st.session_state["alertas_fixos_ids"] = set()

    # -------------------------------------------------
    # RENDERIZAÇÃO DOS ALERTAS FIXOS (FRONTEND)
    # -------------------------------------------------
    if st.session_state["alertas_fixos"]:

        st.markdown("### 🔔 Atualizações Recentes")

        alertas = list(st.session_state["alertas_fixos"])

        for alerta in alertas:

            col1, col2 = st.columns([9, 1])

            with col1:
                st.warning(
                    f"Cliente **{alerta['cliente']}**  \n"
                    f"{alerta['de']} → **{alerta['para']}**"
                )

            with col2:
                if st.button(
                    "❌",
                    key=f"fechar_alerta_{page_scope_id}_{alerta['id']}"
                ):

                    # remove alerta visual
                    st.session_state["alertas_fixos"] = [
                        a for a in st.session_state["alertas_fixos"]
                        if a["id"] != alerta["id"]
                    ]

                    # remove id para não reaparecer
                    if alerta["id"] in st.session_state["alertas_fixos_ids"]:
                        st.session_state["alertas_fixos_ids"].remove(alerta["id"])

                    st.rerun()
