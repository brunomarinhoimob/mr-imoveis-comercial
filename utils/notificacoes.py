import streamlit as st
import pandas as pd


def verificar_notificacoes(df: pd.DataFrame):
    """
    Registra notificações persistentes quando:
    - um cliente recebe uma NOVA LINHA
    - o STATUS_BASE muda em relação ao último estado conhecido

    Regras:
    - Funciona por corretor (perfil corretor)
    - Não duplica notificação
    - Sobrevive a refresh
    - Só some quando o usuário clicar no ❌ (controle no bootstrap)
    """

    # -------------------------------------------------
    # VALIDAÇÕES BÁSICAS
    # -------------------------------------------------
    if df is None or df.empty:
        return

    perfil = st.session_state.get("perfil")
    nome_corretor = st.session_state.get("nome_usuario", "").upper().strip()

    colunas_necessarias = {"CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR"}
    if not colunas_necessarias.issubset(df.columns):
        return

    # -------------------------------------------------
    # INICIALIZA SESSION STATE
    # -------------------------------------------------
    if "notificacoes_cache" not in st.session_state:
        st.session_state["notificacoes_cache"] = {}

    if "alertas_fixos" not in st.session_state:
        st.session_state["alertas_fixos"] = []

    if "alertas_fixos_ids" not in st.session_state:
        st.session_state["alertas_fixos_ids"] = set()

    # cache separado por usuário
    chave_cache = nome_corretor if perfil == "corretor" else "ADMIN"
    cache_usuario = st.session_state["notificacoes_cache"].get(chave_cache, {})

    # -------------------------------------------------
    # FILTRO POR CORRETOR (SEGURANÇA)
    # -------------------------------------------------
    if perfil == "corretor":
        df = df[df["CORRETOR"] == nome_corretor]

    if df.empty:
        return

    # -------------------------------------------------
    # ORDENAÇÃO SEGURA (CRÍTICA)
    # -------------------------------------------------
    df = df.copy()
    df["_ord"] = range(len(df))

    if "DIA" in df.columns:
        df["_dia_dt"] = pd.to_datetime(df["DIA"], errors="coerce")
        df = df.sort_values(["_dia_dt", "_ord"])
    else:
        df = df.sort_values("_ord")

    # -------------------------------------------------
    # ÚLTIMO STATUS POR CLIENTE
    # -------------------------------------------------
    ultimos_status = (
        df.groupby("CHAVE_CLIENTE", as_index=False)
        .tail(1)[["CHAVE_CLIENTE", "STATUS_BASE"]]
        .set_index("CHAVE_CLIENTE")["STATUS_BASE"]
        .astype(str)
        .to_dict()
    )

    contagens = df["CHAVE_CLIENTE"].value_counts().to_dict()

    # -------------------------------------------------
    # LOOP PRINCIPAL
    # -------------------------------------------------
    for chave_cliente, status_atual in ultimos_status.items():

        if not status_atual:
            continue

        status_atual = status_atual.upper().strip()
        count_atual = int(contagens.get(chave_cliente, 0))

        estado_antigo = cache_usuario.get(chave_cliente)

        # ---------------------------------------------
        # PRIMEIRA VEZ → SÓ REGISTRA ESTADO
        # ---------------------------------------------
        if not estado_antigo:
            cache_usuario[chave_cliente] = {
                "count": count_atual,
                "status": status_atual
            }
            continue

        antigo_count = int(estado_antigo.get("count", 0))
        antigo_status = estado_antigo.get("status", "")

        # ---------------------------------------------
        # REGRA DE DISPARO
        # nova linha + status diferente
        # ---------------------------------------------
        if count_atual > antigo_count and status_atual != antigo_status:

            cliente_nome = chave_cliente.split("|")[0].strip()
            alerta_id = f"{chave_cliente}|{status_atual}"

            # evita duplicação mesmo com refresh
            if alerta_id not in st.session_state["alertas_fixos_ids"]:
                st.session_state["alertas_fixos"].append({
                    "id": alerta_id,
                    "cliente": cliente_nome,
                    "de": antigo_status,
                    "para": status_atual
                })
                st.session_state["alertas_fixos_ids"].add(alerta_id)

        # ---------------------------------------------
        # ATUALIZA CACHE DO CLIENTE
        # ---------------------------------------------
        cache_usuario[chave_cliente] = {
            "count": count_atual,
            "status": status_atual
        }

    # -------------------------------------------------
    # SALVA CACHE DO USUÁRIO
    # -------------------------------------------------
    st.session_state["notificacoes_cache"][chave_cache] = cache_usuario
