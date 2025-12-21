import json
import uuid
from pathlib import Path
from datetime import datetime
import pandas as pd

# =================================================
# CAMINHOS DOS DADOS
# =================================================
BASE_DIR = Path("data")
ARQ_NOTIFICACOES = BASE_DIR / "notificacoes.json"
ARQ_SNAPSHOT = BASE_DIR / "snapshot_clientes.json"

# =================================================
# UTILIDADES JSON
# =================================================
def _ler_json(caminho: Path) -> dict:
    if caminho.exists():
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}
    return {}

def _salvar_json(caminho: Path, data: dict):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =================================================
# PROCESSADOR DE EVENTOS (NOTIFICAÇÕES)
# =================================================
def processar_eventos(df: pd.DataFrame):
    """
    Gera notificações persistentes quando:
    - um cliente aparece pela primeira vez
    - o STATUS_BASE muda

    NÃO interpreta status.
    Usa exatamente o texto da planilha.
    """

    if df is None or df.empty:
        return

    colunas_necessarias = {"CHAVE_CLIENTE", "CORRETOR"}
    if not colunas_necessarias.issubset(df.columns):
        return

    # -------------------------
    # Leitura do estado salvo
    # -------------------------
    notificacoes = _ler_json(ARQ_NOTIFICACOES)
    snapshot = _ler_json(ARQ_SNAPSHOT)

    df = df.copy()

    df["STATUS_BASE"] = df["STATUS_BASE"].astype(str).str.upper().str.strip()
    df["CORRETOR"] = df["CORRETOR"].astype(str).str.upper().str.strip()

    agora = datetime.now().isoformat(timespec="seconds")

    # -------------------------
    # Último estado por cliente
    # -------------------------
    ultimos = (
        df.groupby("CHAVE_CLIENTE", as_index=False)
        .tail(1)[["CHAVE_CLIENTE", "STATUS_BASE", "CORRETOR"]]
    )

    novo_snapshot = {}

    for _, row in ultimos.iterrows():
        chave = row["CHAVE_CLIENTE"]
        status_atual = row.get("SITUACAO_EXATA", "") or row.get("STATUS_BASE", "")
        corretor = row["CORRETOR"]
        cliente = chave.split("|")[0].strip()

        # garante estrutura por corretor
        if corretor not in notificacoes:
            notificacoes[corretor] = []

        estado_antigo = snapshot.get(chave)

        # -------------------------
        # CLIENTE NOVO
        # -------------------------
        if not estado_antigo:
            notificacoes[corretor].append({
                "id": str(uuid.uuid4()),
                "cliente": cliente,
                "status": status_atual,
                "tipo": "NOVO_CLIENTE",
                "timestamp": agora,
                "lido": False
            })

        # -------------------------
        # MUDANÇA DE STATUS
        # -------------------------
        elif estado_antigo.get("status") != status_atual:
            notificacoes[corretor].append({
                "id": str(uuid.uuid4()),
                "cliente": cliente,
                "de": estado_antigo.get("status"),
                "para": status_atual,
                "tipo": "MUDANCA_STATUS",
                "timestamp": agora,
                "lido": False
            })

        # -------------------------
        # Atualiza snapshot
        # -------------------------
        novo_snapshot[chave] = {
            "status": status_atual,
            "corretor": corretor
        }

    # -------------------------
    # Persistência
    # -------------------------
    _salvar_json(ARQ_NOTIFICACOES, notificacoes)
    _salvar_json(ARQ_SNAPSHOT, novo_snapshot)
