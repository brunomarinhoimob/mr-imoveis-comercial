import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------
# ARQUIVO DE CACHE LOCAL
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# NOTIFICAÇÕES (NOVA LINHA = EVENTO)
# ---------------------------------------------------------
def verificar_notificacoes(df: pd.DataFrame):
    if df.empty:
        return

    perfil = st.session_state.get("perfil")
    nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

    colunas = {"CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR", "DIA"}
    if not colunas.issubset(df.columns):
        return

    # filtro por perfil
    if perfil == "corretor":
        df = df[df["CORRETOR"] == nome_corretor]

    if df.empty:
        return

    # ordena histórico
    df = df.sort_values("DIA")

    cache = _carregar_cache()
    chave_cache = nome_corretor if perfil == "corretor" else "ADMIN"
    cache_usuario = cache.get(chave_cache, {})

    for _, row in df.iterrows():
        chave = row["CHAVE_CLIENTE"]
        status = row["STATUS_BASE"]
        dia = str(row["DIA"])

        if not status:
            continue

        ultimo = cache_usuario.get(chave)

        # NOVA LINHA + STATUS DIFERENTE = NOTIFICA
        if ultimo:
            if ultimo["status"] != status and ultimo["dia"] != dia:
                cliente = chave.split("|")[0].strip()
                st.toast(
                    f"🔔 Cliente {cliente}\n{ultimo['status']} → {status}",
                    icon="🔔",
                )

        # atualiza cache sempre
        cache_usuario[chave] = {
            "status": status,
            "dia": dia,
        }

    cache[chave_cache] = cache_usuario
    _salvar_cache(cache)
