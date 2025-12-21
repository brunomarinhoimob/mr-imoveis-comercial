import pandas as pd
from pathlib import Path
from datetime import datetime

# =========================================================
# CAMINHOS
# =========================================================
PASTA_DATA = Path("data")
ARQ_ESTADO = PASTA_DATA / "estado_anterior_clientes.csv"
ARQ_NOTIF = PASTA_DATA / "notificacoes.csv"

# =========================================================
# GARANTIR ESTRUTURA
# =========================================================
def _garantir_arquivos():
    PASTA_DATA.mkdir(exist_ok=True)

    if not ARQ_ESTADO.exists():
        pd.DataFrame(columns=[
            "CHAVE",
            "CLIENTE",
            "CPF",
            "SITUACAO"
        ]).to_csv(ARQ_ESTADO, index=False)

    if not ARQ_NOTIF.exists():
        pd.DataFrame(columns=[
            "DATA_HORA",
            "CLIENTE",
            "CPF",
            "TIPO",
            "SITUACAO"
        ]).to_csv(ARQ_NOTIF, index=False)


# =========================================================
# GERAR NOTIFICAÇÕES
# =========================================================
def gerar_notificacoes(df_atual: pd.DataFrame):
    _garantir_arquivos()

    if df_atual.empty:
        return

    df_estado_ant = pd.read_csv(ARQ_ESTADO)
    notificacoes = pd.read_csv(ARQ_NOTIF)

    # Normalizações mínimas
    for col in ["CLIENTE", "CPF", "SITUACAO"]:
        if col in df_atual.columns:
            df_atual[col] = df_atual[col].astype(str).str.strip()

    # Criar chave única
    df_atual["CHAVE"] = df_atual.apply(
        lambda x: x["CPF"] if x.get("CPF") not in ["", "nan", "None"] else x["CLIENTE"],
        axis=1
    )

    estado_map = df_estado_ant.set_index("CHAVE")["SITUACAO"].to_dict()

    novas_notificacoes = []

    for _, row in df_atual.iterrows():
        cliente = row.get("CLIENTE", "").strip()
        situacao = row.get("SITUACAO", "").strip()
        cpf = row.get("CPF", "").strip()
        chave = row.get("CHAVE")

        if not cliente or not situacao:
            continue

        situacao_ant = estado_map.get(chave)

        # 🟢 CLIENTE NOVO
        if situacao_ant is None:
            novas_notificacoes.append({
                "DATA_HORA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "CLIENTE": cliente,
                "CPF": cpf,
                "TIPO": "CLIENTE NOVO",
                "SITUACAO": situacao
            })

        # 🔵 MUDANÇA DE SITUAÇÃO
        elif situacao_ant != situacao:
            novas_notificacoes.append({
                "DATA_HORA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "CLIENTE": cliente,
                "CPF": cpf,
                "TIPO": "MUDANÇA DE SITUAÇÃO",
                "SITUACAO": situacao
            })

    if novas_notificacoes:
        notificacoes = pd.concat(
            [pd.DataFrame(novas_notificacoes), notificacoes],
            ignore_index=True
        )

        notificacoes.to_csv(ARQ_NOTIF, index=False)

    # Atualiza estado anterior
    df_atual[["CHAVE", "CLIENTE", "CPF", "SITUACAO"]].drop_duplicates() \
        .to_csv(ARQ_ESTADO, index=False)


# =========================================================
# LER NOTIFICAÇÕES
# =========================================================
def obter_notificacoes(qtd=20):
    if not ARQ_NOTIF.exists():
        return pd.DataFrame()

    df = pd.read_csv(ARQ_NOTIF)

    if df.empty:
        return df

    return df.head(qtd)
