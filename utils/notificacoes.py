import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# NOTIFICAÇÕES
# REGRA:
# - NOVA LINHA NO CLIENTE
# - STATUS DIFERENTE (TEXTO EXATO)
# ---------------------------------------------------------
def verificar_notificacoes(df: pd.DataFrame):
    if df is None or df.empty:
        return

    perfil = st.session_state.get("perfil")
    nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

    colunas = {"CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR"}
    if not colunas.issubset(df.columns):
        return

    # cache por sessão
    if "notificacoes_cache" not in st.session_state:
        st.session_state["notificacoes_cache"] = {}

    cache = st.session_state["notificacoes_cache"]
    chave_cache = nome_corretor if perfil == "corretor" else "ADMIN"
    cache_usuario = cache.get(chave_cache, {})

    # filtro por corretor
    if perfil == "corretor":
        df = df[df["CORRETOR"] == nome_corretor]

    if df.empty:
        return

    # ordenação segura (linha mais recente vence)
    df = df.copy()
    df["_ord"] = range(len(df))

    if "DIA" in df.columns:
        df["_dia_dt"] = pd.to_datetime(df["DIA"], errors="coerce", dayfirst=True)
        df = df.sort_values(["_dia_dt", "_ord"])
    else:
        df = df.sort_values("_ord")

    # status mais recente por cliente (TEXTO PURO)
    ultimos = (
        df.groupby("CHAVE_CLIENTE", as_index=False)
          .tail(1)[["CHAVE_CLIENTE", "STATUS_BASE"]]
          .set_index("CHAVE_CLIENTE")["STATUS_BASE"]
          .to_dict()
    )

    contagens = df["CHAVE_CLIENTE"].value_counts().to_dict()

    for chave, status_atual in ultimos.items():
        if not status_atual:
            continue

        # ⚠️ NÃO NORMALIZA TEXTO
        status_atual = str(status_atual)

        count_atual = int(contagens.get(chave, 0))
        antigo = cache_usuario.get(chave)

        # primeira vez: só aprende o estado
        if not antigo:
            cache_usuario[chave] = {
                "count": count_atual,
                "status": status_atual
            }
            continue

        antigo_count = int(antigo.get("count", 0))
        antigo_status = antigo.get("status")

        # nova linha
        if count_atual > antigo_count:
            # texto diferente = evento real
            if antigo_status != status_atual:
                cliente = str(chave).split("|")[0].strip()
                st.toast(
                    f"🔔 Cliente {cliente}\n{antigo_status} → {status_atual}",
                    icon="🔔",
                )

        # atualiza cache
        cache_usuario[chave] = {
            "count": count_atual,
            "status": status_atual
        }

    cache[chave_cache] = cache_usuario
    st.session_state["notificacoes_cache"] = cache
