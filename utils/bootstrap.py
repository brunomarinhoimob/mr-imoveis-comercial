import streamlit as st
from utils.notificacoes import verificar_notificacoes
from login import tela_login
import pandas as pd

def iniciar_app(df: pd.DataFrame):
    # controle de login
    if "logado" not in st.session_state:
        st.session_state.logado = False

    if not st.session_state.logado:
        tela_login()
        st.stop()

    # notificações globais
    verificar_notificacoes(df)
