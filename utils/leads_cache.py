import os
import pickle
from datetime import datetime, timedelta

import pandas as pd
import requests

from utils.supremo_config import TOKEN_SUPREMO

# ---------------------------------------------------------
# CONFIGURAÇÃO DO CACHE
# ---------------------------------------------------------
BASE_URL_LEADS = "https://api.supremocrm.com.br/v1/leads"

CACHE_DIR = "cache"
CACHE_FILE = os.path.join(CACHE_DIR, "leads_cache.pkl")
CACHE_TTL_MINUTES = 30  # tempo de vida do cache em minutos

# Garante que a pasta de cache existe
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_leads_page(pagina: int = 1) -> pd.DataFrame:
    """
    Busca UMA página de leads na API do Supremo.
    Em caso de erro, devolve DataFrame vazio SEM mostrar nada no Streamlit.
    """
    headers = {"Authorization": f"Bearer {TOKEN_SUPREMO}"}
    params = {"pagina": pagina}

    try:
        resp = requests.get(BASE_URL_LEADS, headers=headers, params=params, timeout=30)
    except:
        return pd.DataFrame()

    if resp.status_code != 200:
        return pd.DataFrame()

    try:
        data = resp.json()
    except:
        return pd.DataFrame()

    if isinstance(data, dict) and "data" in data:
        return pd.DataFrame(data["data"])

    if isinstance(data, list):
        return pd.DataFrame(data)

    return pd.DataFrame()


def _carregar_leads_from_disk() -> pd.DataFrame | None:
    """
    Carrega o cache de leads do disco, se existir e estiver válido.
    NÃO mostra erros no Streamlit.
    """
    if not os.path.exists(CACHE_FILE):
        return None

    try:
        with open(CACHE_FILE, "rb") as f:
            cache_data = pickle.load(f)
    except:
        return None

    ts = cache_data.get("timestamp")
    df_cached = cache_data.get("df")

    if ts is None or df_cached is None:
        return None

    # se passou do TTL, expirou
    if datetime.now() - ts > timedelta(minutes=CACHE_TTL_MINUTES):
        return None

    return df_cached


def _salvar_leads_no_disk(df_leads: pd.DataFrame) -> None:
    """
    Salva leads + timestamp em arquivo .pkl.
    Nunca mostra erro.
    """
    try:
        payload = {
            "timestamp": datetime.now(),
            "df": df_leads
        }
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(payload, f)
    except:
        pass  # ignora


def carregar_leads(limit: int = 1000, max_pages: int = 100) -> pd.DataFrame:
    """
    Carrega leads do Supremo usando cache silencioso.
    Nunca mostra aviso, nunca mostra erro.
    Apenas retorna o DF disponível.
    """
    # 1) tenta cache
    df_cache = _carregar_leads_from_disk()
    if df_cache is not None:
        return df_cache

    # 2) busca da API
    dfs = []
    total = 0
    pagina = 1

    while total < limit and pagina <= max_pages:
        df_page = _get_leads_page(pagina)
        if df_page.empty:
            break

        dfs.append(df_page)
        total += len(df_page)
        pagina += 1

    if dfs:
        df_all = pd.concat(dfs, ignore_index=True)

        # remove duplicados
        if "id" in df_all.columns:
            df_all = df_all.drop_duplicates(subset="id")

        df_all = df_all.head(limit)

        # converte data
        if "data_captura" in df_all.columns:
            df_all["data_captura"] = pd.to_datetime(df_all["data_captura"], errors="coerce")
    else:
        df_all = pd.DataFrame()

    # 3) salva no cache sempre
    _salvar_leads_no_disk(df_all)

    return df_all
