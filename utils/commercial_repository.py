from datetime import datetime

import pandas as pd


SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


def limpar_para_data(serie: pd.Series) -> pd.Series:
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


def mes_ano_ptbr_para_date(valor: str):
    if pd.isna(valor):
        return pd.NaT

    texto = str(valor).strip().lower()
    if not texto:
        return pd.NaT

    meses = {
        "janeiro": 1,
        "fevereiro": 2,
        "marco": 3,
        "março": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }

    partes = texto.split()
    try:
        mes = meses.get(partes[0])
        ano = int(partes[-1])
        if mes is None:
            return pd.NaT
        return datetime(ano, mes, 1).date()
    except Exception:
        return pd.NaT


def normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df


def preparar_datas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

    possiveis_cols_base = [
        "DATA BASE",
        "DATA_BASE",
        "DT BASE",
        "DATA REF",
        "DATA REFERENCIA",
        "DATA REFERÊNCIA",
    ]
    col_data_base = next((col for col in possiveis_cols_base if col in df.columns), None)

    if col_data_base:
        base_raw = df[col_data_base].astype(str).str.strip()
        df["DATA_BASE_LABEL"] = base_raw.str.lower().str.title()
        df["DATA_BASE"] = base_raw.apply(mes_ano_ptbr_para_date)

        if df["DATA_BASE"].dropna().empty:
            df["DATA_BASE"] = df["DIA"]
            df["DATA_BASE_LABEL"] = df["DIA"].apply(lambda d: d.strftime("%m/%Y") if pd.notnull(d) else "")
    else:
        df["DATA_BASE"] = df["DIA"]
        df["DATA_BASE_LABEL"] = df["DIA"].apply(lambda d: d.strftime("%m/%Y") if pd.notnull(d) else "")

    return df


def preparar_equipe_corretor(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = df[col].fillna("NAO INFORMADO").astype(str).str.upper().str.strip()
        else:
            df[col] = "NAO INFORMADO"
    return df


def preparar_status(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((col for col in possiveis_cols_situacao if col in df.columns), None)
    df["STATUS_BASE"] = ""

    if not col_situacao:
        return df

    status = df[col_situacao].fillna("").astype(str).str.upper()
    df.loc[status.str.contains("EM ANÁLISE|EM ANALISE", na=False), "STATUS_BASE"] = "EM ANALISE"
    df.loc[status.str.contains("REANÁLISE|REANALISE", na=False), "STATUS_BASE"] = "REANALISE"
    df.loc[status.str.strip() == "APROVAÇÃO", "STATUS_BASE"] = "APROVADO"
    df.loc[status.str.strip() == "APROVACAO", "STATUS_BASE"] = "APROVADO"
    df.loc[status.str.contains("APROVADO BACEN", na=False), "STATUS_BASE"] = "APROVADO BACEN"
    df.loc[status.str.contains("APROVADO COM RESTRIÇÃO|APROVADO COM RESTRICAO", na=False), "STATUS_BASE"] = "APROVADO COM RESTRICAO"
    df.loc[status.str.contains("REPROV", na=False), "STATUS_BASE"] = "REPROVADO"
    df.loc[status.str.contains("VENDA GERADA", na=False), "STATUS_BASE"] = "VENDA GERADA"
    df.loc[status.str.contains("VENDA INFORMADA", na=False), "STATUS_BASE"] = "VENDA INFORMADA"
    df.loc[status.str.contains("DESIST", na=False), "STATUS_BASE"] = "DESISTIU"
    return df


def preparar_cliente_vgv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0) if "OBSERVAÇÕES" in df.columns else 0

    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]
    col_nome = next((col for col in possiveis_nome if col in df.columns), None)
    col_cpf = next((col for col in possiveis_cpf if col in df.columns), None)

    df["NOME_CLIENTE_BASE"] = (
        df[col_nome].fillna("NAO INFORMADO").astype(str).str.upper().str.strip()
        if col_nome
        else "NAO INFORMADO"
    )
    df["CPF_CLIENTE_BASE"] = (
        df[col_cpf].fillna("").astype(str).str.replace(r"\D", "", regex=True)
        if col_cpf
        else ""
    )
    df["CHAVE_CLIENTE"] = df["NOME_CLIENTE_BASE"].fillna("NAO INFORMADO") + " | " + df["CPF_CLIENTE_BASE"].fillna("")
    return df


def preparar_base_comercial(df: pd.DataFrame) -> pd.DataFrame:
    df = normalizar_colunas(df)
    df = preparar_datas(df)
    df = preparar_equipe_corretor(df)
    df = preparar_status(df)
    df = preparar_cliente_vgv(df)
    return df


def carregar_google_sheets() -> pd.DataFrame:
    df = pd.read_csv(CSV_URL)
    return preparar_base_comercial(df)


def carregar_base_comercial(fonte: str = "google_sheets") -> pd.DataFrame:
    if fonte == "google_sheets":
        return carregar_google_sheets()
    raise ValueError(f"Fonte de dados nao suportada: {fonte}")


def aplicar_perfil_corretor(df: pd.DataFrame, perfil: str, nome_usuario: str) -> pd.DataFrame:
    if perfil == "corretor" and "CORRETOR" in df.columns:
        return df[df["CORRETOR"] == str(nome_usuario or "").upper().strip()].copy()
    return df.copy()
