# utils/notificacoes.py

import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# Arquivo local para guardar último status conhecido
ARQ_STATUS = Path("utils/status_clientes_cache.json")


def _carregar_cache():
    if ARQ_STATUS.exists():
        try:
            with open(ARQ_STATUS, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _salvar_cache(cache: dict):
    try:
        with open(ARQ_STATUS, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def verificar_notificacoes(df: pd.DataFrame):
    """
    Mostra notificações quando o STATUS_BASE do cliente muda.
    Respeita perfil:
    - corretor: apenas seus clientes
    - gestor/admin: todos
    """

    if df.empty:
        return

    perfil = st.session_state.get("perfil")
    nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

    # garante colunas mínimas
    cols_necessarias = {"CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR"}
    if not cols_necessarias.issubset(df.columns):
        return

    # aplica regra por perfil
    if perfil == "corretor":
        df_notif = df[df["CORRETOR"] == nome_corretor].copy()
    else:
        df_notif = df.copy()

    if df_notif.empty:
        return

    # status atual por cliente (último do histórico)
    df_ord = df_notif.sort_values("DIA")
    status_atual = (
        df_ord.groupby("CHAVE_CLIENTE")["STATUS_BASE"]
        .last()
        .to_dict()
    )

    cache = _carregar_cache()
    cache_usuario = cache.get(nome_corretor if perfil == "corretor" else "ADMIN", {})

    houve_alerta = False

    for chave, status_novo in status_atual.items():
        status_antigo = cache_usuario.get(chave)

        if status_antigo and status_antigo != status_novo:
            # dispara notificação
            cliente = chave.split("|")[0].strip()

            st.toast(
                f"🔔 Cliente {cliente}\n"
                f"{status_antigo} → {status_novo}",
                icon="🔔",
            )

            houve_alerta = True

        # atualiza cache
        cache_usuario[chave] = status_novo

    if houve_alerta:
        cache_usuario["_ultima_execucao"] = datetime.now().isoformat()

    cache[nome_corretor if perfil == "corretor" else "ADMIN"] = cache_usuario
    _salvar_cache(cache)
