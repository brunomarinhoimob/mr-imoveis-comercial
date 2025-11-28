import streamlit as st
import pandas as pd
import numpy as np
from datetime import date

from app_dashboard import carregar_dados_planilha

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes MR – MR Imóveis",
    page_icon="🧑‍💼",
    layout="wide",
)

# ---------------------------------------------------------
# LOGO MR IMÓVEIS
# ---------------------------------------------------------
LOGO_PATH = "logo_mr.png"

col_logo, col_tit = st.columns([1, 4])
with col_logo:
    try:
        st.image(LOGO_PATH, use_column_width=True)
    except Exception:
        st.write("MR Imóveis")

with col_tit:
    st.markdown("## Clientes MR – Visão Geral")
    st.caption(
        "Visão consolidada dos clientes da MR Imóveis. "
        "Na busca, a situação atual segue a regra:\n"
        "- Se houver **VENDA GERADA** ou **VENDA INFORMADA** após o último `DESISTIU`, "
        "essa venda será SEMPRE considerada a situação atual.\n"
        "- A venda só deixa de ser atual quando, em alguma linha POSTERIOR, houver o status **DESISTIU**.\n"
        "- O `DESISTIU` funciona como um **reset**, abrindo um novo ciclo para o cliente."
    )

# ---------------------------------------------------------
# CARREGAMENTO DOS DADOS
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados_clientes() -> pd.DataFrame:
    df = carregar_dados_planilha()
    if df is None or df.empty:
        return pd.DataFrame()

    # Colunas em caixa alta
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DIA" in df.columns:
        df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
    elif "DATA" in df.columns:
        df["DIA"] = pd.to_datetime(df["DATA"], errors="coerce")
    else:
        df["DIA"] = pd.NaT

    # NOME CLIENTE
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    # CPF
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)
    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    # EQUIPE / CORRETOR
    for col in ["EQUIPE", "CORRETOR"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .fillna("NÃO INFORMADO")
                .astype(str)
                .str.upper()
                .str.strip()
            )
        else:
            df[col] = "NÃO INFORMADO"

    # CONSTRUTORA / EMPREENDIMENTO
    possiveis_construtora = ["CONSTRUTORA", "INCORPORADORA"]
    possiveis_empreend = ["EMPREENDIMENTO", "PRODUTO", "IMÓVEL", "IMOVEL"]

    col_construtora = next((c for c in possiveis_construtora if c in df.columns), None)
    col_empreend = next((c for c in possiveis_empreend if c in df.columns), None)

    if col_construtora is None:
        df["CONSTRUTORA_BASE"] = "NÃO INFORMADO"
    else:
        df["CONSTRUTORA_BASE"] = (
            df[col_construtora]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    if col_empreend is None:
        df["EMPREENDIMENTO_BASE"] = "NÃO INFORMADO"
    else:
        df["EMPREENDIMENTO_BASE"] = (
            df[col_empreend]
            .fillna("NÃO INFORMADO")
            .astype(str)
            .str.upper()
            .str.strip()
        )

    # SITUAÇÃO / STATUS
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next((c for c in possiveis_cols_situacao if c in df.columns), None)

    df["STATUS_BASE"] = ""
    if col_situacao:
        status_original = df[col_situacao].fillna("").astype(str).str.strip()
        status_upper = status_original.str.upper()

        df.loc[status_upper.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status_upper.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status_upper.str.contains(r"\bAPROVAÇÃO\b"), "STATUS_BASE"] = "APROVADO"
        df.loc[status_upper.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status_upper.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status_upper.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"
        df.loc[status_upper.str.contains("DESIST"), "STATUS_BASE"] = "DESISTIU"

        df["SITUACAO_ORIGINAL"] = status_original
    else:
        df["SITUACAO_ORIGINAL"] = "NÃO INFORMADO"

    # OBS / OBS2 / VGV
    if "OBSERVAÇÕES" in df.columns:
        df["OBSERVACOES_RAW"] = df["OBSERVAÇÕES"].fillna("").astype(str).str.strip()
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["OBSERVACOES_RAW"] = ""
        df["VGV"] = 0.0

    if "OBSERVAÇÕES 2" in df.columns:
        df["OBSERVACOES2_RAW"] = df["OBSERVAÇÕES 2"].fillna("").astype(str).str.strip()
    else:
        df["OBSERVACOES2_RAW"] = ""

    # CHAVE CLIENTE (pra linkar histórico)
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df


df = carregar_dados_clientes()
if df is None or df.empty:
    st.error("Não foi possível carregar dados de clientes.")
    st.stop()

# ---------------------------------------------------------
# FILTROS DO PERÍODO (PARA KPIs E TABELA GERAL)
# ---------------------------------------------------------
st.sidebar.title("Filtros – Clientes MR")

hoje = date.today()
data_min = df["DIA"].min()
data_max = df["DIA"].max()

if pd.isna(data_min) or pd.isna(data_max):
    data_min = hoje
    data_max = hoje

periodo = st.sidebar.date_input(
    "Período (data de movimentação)",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
)

if isinstance(periodo, (tuple, list)):
    data_ini, data_fim = periodo
else:
    data_ini = periodo
    data_fim = periodo

if data_ini > data_fim:
    st.sidebar.error("Data inicial maior que data final. Ajuste o período.")
    st.stop()

mask_periodo = (df["DIA"] >= pd.to_datetime(data_ini)) & (df["DIA"] <= pd.to_datetime(data_fim))
df_periodo = df[mask_periodo].copy()

if df_periodo.empty:
    st.info("Não há movimentações de clientes no período selecionado.")
    st.stop()

st.sidebar.markdown("---")
equipe_sel = st.sidebar.selectbox(
    "Filtrar por equipe (para os KPIs):",
    options=["Todas"] + sorted(df_periodo["EQUIPE"].dropna().unique().tolist()),
    index=0,
)
if equipe_sel != "Todas":
    df_periodo = df_periodo[df_periodo["EQUIPE"] == equipe_sel].copy()

corretor_sel = st.sidebar.selectbox(
    "Filtrar por corretor (para os KPIs):",
    options=["Todos"] + sorted(df_periodo["CORRETOR"].dropna().unique().tolist()),
    index=0,
)
if corretor_sel != "Todos":
    df_periodo = df_periodo[df_periodo["CORRETOR"] == corretor_sel].copy()

if df_periodo.empty:
    st.info("Nenhum cliente encontrado com esse filtro para o período.")
    st.stop()

# ---------------------------------------------------------
# VISÃO GERAL (KPIs DO PERÍODO)
# ---------------------------------------------------------
total_registros = len(df_periodo)
total_clientes_unicos = df_periodo["CHAVE_CLIENTE"].nunique()
total_analises = df_periodo["STATUS_BASE"].isin(["EM ANÁLISE", "REANÁLISE"]).sum()
total_aprovacoes = (df_periodo["STATUS_BASE"] == "APROVADO").sum()
total_vendas_geradas = (df_periodo["STATUS_BASE"] == "VENDA GERADA").sum()
total_vendas_informadas = (df_periodo["STATUS_BASE"] == "VENDA INFORMADA").sum()
vgv_total = df_periodo["VGV"].sum()


def format_currency(valor: float) -> str:
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros no período", int(total_registros))
c2.metric("Clientes únicos", int(total_clientes_unicos))
c3.metric("Total análises (EM+RE)", int(total_analises))
c4.metric("Total aprovações", int(total_aprovacoes))

c5, c6, c7 = st.columns(3)
c5.metric("Vendas geradas", int(total_vendas_geradas))
c6.metric("Vendas informadas", int(total_vendas_informadas))
c7.metric("VGV estimado", format_currency(vgv_total))

st.markdown("---")

# ---------------------------------------------------------
# BUSCA DE CLIENTES (NOME / CPF) – USA HISTÓRICO COMPLETO
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.title("Busca de clientes MR 🔎")

tipo_busca = st.sidebar.radio(
    "Buscar por:",
    ("Nome (parcial)", "CPF"),
)

termo_busca = st.sidebar.text_input(
    "Digite o nome ou CPF do cliente",
    placeholder="Ex: MARIA / 12345678901",
)

st.sidebar.caption(
    "• Nome: pode digitar só uma parte (ex: 'SILVA')\n"
    "• CPF: digite só números (não precisa de ponto ou traço)."
)

# Helper: checa se observação é só número/valor
def observacao_e_numero(txt: str) -> bool:
    if not txt:
        return False
    t = (
        txt.upper()
        .replace("R$", "")
        .replace(".", "")
        .replace(",", "")
        .replace(" ", "")
    )
    return t.isdigit()


def obter_ultima_linha_regra_venda_reset(df_cli: pd.DataFrame) -> pd.Series:
    """
    Aplica a regra:
    - Considera somente o trecho após o último DESISTIU (se existir).
    - Dentro desse trecho, se houver VENDA GERADA/INFORMADA, a situação atual é a última venda.
    - Se não houver venda nesse trecho, a situação atual é a última linha do trecho.
    """
    if df_cli.empty:
        return pd.Series()

    df_cli_ord = df_cli.sort_values("DIA")
    status = df_cli_ord["STATUS_BASE"].fillna("")

    # Último DESISTIU
    idx_reset = df_cli_ord.index[status == "DESISTIU"]
    if len(idx_reset) > 0:
        last_reset_idx = idx_reset[-1]
        df_segmento = df_cli_ord.loc[last_reset_idx:]
    else:
        df_segmento = df_cli_ord

    status_seg = df_segmento["STATUS_BASE"].fillna("")
    vendas_mask = status_seg.isin(["VENDA GERADA", "VENDA INFORMADA"])

    if vendas_mask.any():
        ultima = df_segmento.loc[vendas_mask].iloc[-1]
    else:
        ultima = df_segmento.iloc[-1]

    return ultima


if termo_busca.strip():
    termo = termo_busca.strip().upper()

    # Busca no HISTÓRICO COMPLETO (df), NÃO só no período
    if tipo_busca.startswith("Nome"):
        df_resultado = df[
            df["NOME_CLIENTE_BASE"].str.contains(termo, na=False)
        ].copy()
    else:
        termo_cpf = "".join(ch for ch in termo_busca if ch.isdigit())
        df_resultado = df[
            df["CPF_CLIENTE_BASE"].str.contains(termo_cpf, na=False)
        ].copy()

    if df_resultado.empty:
        st.warning("Nenhum cliente encontrado na base completa com esse critério de busca.")
    else:
        df_resultado["DIA"] = pd.to_datetime(df_resultado["DIA"], errors="coerce")

        # ---- função que gera o resumo de CADA cliente x corretor ----
        def resumo_cliente(gr: pd.DataFrame) -> pd.Series:
            gr = gr.sort_values("DIA")
            status = gr["STATUS_BASE"].fillna("")

            analises = status.isin(["EM ANÁLISE", "REANÁLISE"]).sum()
            aprovacoes = (status == "APROVADO").sum()
            vendas = status.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()
            vgv = gr["VGV"].sum()

            # aplica a regra da última situação (venda x desistiu)
            ultima = obter_ultima_linha_regra_venda_reset(gr)

            ult_status = ultima.get("SITUACAO_ORIGINAL", "")
            ult_data = ultima.get("DIA", pd.NaT)

            return pd.Series(
                {
                    "NOME": gr["NOME_CLIENTE_BASE"].iloc[0],
                    "CPF": gr["CPF_CLIENTE_BASE"].iloc[0],
                    "CORRETOR_RESUMO": gr["CORRETOR"].iloc[0],
                    "ANALISES": analises,
                    "APROVACAOES": aprovacoes,
                    "VENDAS": vendas,
                    "VGV": vgv,
                    "ULT_STATUS": ult_status,
                    "ULT_DATA": ult_data,
                }
            )

        # Agrupa por cliente + corretor (história com aquele corretor)
        resumo = (
            df_resultado.groupby(["CHAVE_CLIENTE", "CORRETOR"])
            .apply(resumo_cliente)
            .reset_index()
        )

        st.markdown(
            f"### 🔎 Resultado da busca – {len(resumo)} registro(s) de cliente x corretor encontrado(s)"
        )

        # ---------- VISÃO GERAL (TABELA DO TOPO) ----------
        visao = resumo[
            [
                "NOME",
                "CPF",
                "CORRETOR_RESUMO",
                "ULT_STATUS",
                "ULT_DATA",
                "ANALISES",
                "APROVACAOES",
                "VENDAS",
                "VGV",
            ]
        ].copy()

        visao["ULT_DATA"] = pd.to_datetime(
            visao["ULT_DATA"], errors="coerce"
        ).dt.strftime("%d/%m/%Y")
        visao["VGV"] = visao["VGV"].apply(format_currency)

        visao = visao.rename(
            columns={
                "CORRETOR_RESUMO": "Corretor",
                "ULT_STATUS": "Situação atual (regra venda/desistiu)",
                "ULT_DATA": "Data última movimentação",
                "ANALISES": "Qtd análises (histórico)",
                "APROVACAOES": "Qtd aprovações (histórico)",
                "VENDAS": "Qtd vendas (histórico)",
                "VGV": "VGV total (histórico)",
            }
        )

        st.markdown("#### 🗂 Visão geral cliente x corretor")
        st.dataframe(
            visao.sort_values(["VENDAS", "VGV total (histórico)"], ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        # ---------- DETALHES POR CLIENTE + LINHA DO TEMPO ----------
        st.markdown("#### 📂 Detalhamento por cliente (história com o corretor)")

        for _, row in resumo.sort_values(["VENDAS", "VGV"], ascending=False).iterrows():
            chave = row["CHAVE_CLIENTE"]
            corr = row["CORRETOR"]

            # História do cliente SOMENTE com aquele corretor
            df_cli = df[
                (df["CHAVE_CLIENTE"] == chave) & (df["CORRETOR"] == corr)
            ].copy()
            if df_cli.empty:
                continue

            df_cli = df_cli.sort_values("DIA")

            ultima_linha = obter_ultima_linha_regra_venda_reset(df_cli)

            ult_constr = ultima_linha.get("CONSTRUTORA_BASE", "NÃO INFORMADO")
            ult_empr = ultima_linha.get("EMPREENDIMENTO_BASE", "NÃO INFORMADO")
            ult_corretor = ultima_linha.get("CORRETOR", "NÃO INFORMADO")
            ult_status_original = ultima_linha.get("SITUACAO_ORIGINAL", row["ULT_STATUS"])
            data_ult = ultima_linha.get("DIA", row["ULT_DATA"])

            # OBS: se for venda, tenta pegar OBS2; senão, última OBS normal
            status_ultima = str(ultima_linha.get("STATUS_BASE", "")).upper()
            ultima_obs = ""
            if status_ultima in ["VENDA GERADA", "VENDA INFORMADA"]:
                obs2 = str(ultima_linha.get("OBSERVACOES2_RAW", "")).strip()
                if obs2:
                    ultima_obs = obs2

            if not ultima_obs:
                obs_validas = [
                    obs
                    for obs in df_cli["OBSERVACOES_RAW"].fillna("")
                    if obs and not observacao_e_numero(obs)
                ]
                ultima_obs = obs_validas[-1] if obs_validas else ""

            analises_em = (df_cli["STATUS_BASE"] == "EM ANÁLISE").sum()
            reanalises = (df_cli["STATUS_BASE"] == "REANÁLISE").sum()
            analises_total = analises_em + reanalises
            aprovacoes_cli = (df_cli["STATUS_BASE"] == "APROVADO").sum()
            vendas_cli = df_cli["STATUS_BASE"].isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()
            vgv_cli = df_cli["VGV"].sum()

            st.markdown("---")
            st.markdown(f"##### 👤 {row['NOME']} — Corretor: `{ult_corretor}`")

            col_top1, col_top2 = st.columns(2)

            with col_top1:
                cpf_fmt = row["CPF"] if row["CPF"] else "NÃO INFORMADO"
                situacao_fmt = ult_status_original or "NÃO INFORMADO"

                st.write(f"**CPF:** `{cpf_fmt}`")
                st.write(f"**Situação atual (regra venda/desistiu):** `{situacao_fmt}`")
                st.write(
                    f"**Corretor responsável (última movimentação):** `{ult_corretor}`"
                )
                st.write(f"**Construtora (última movimentação):** `{ult_constr}`")
                st.write(f"**Empreendimento (última movimentação):** `{ult_empr}`")
                if ultima_obs:
                    st.write(f"**Última observação:** `{ultima_obs}`")

            with col_top2:
                if pd.notna(data_ult):
                    data_fmt = pd.to_datetime(data_ult).strftime("%d/%m/%Y")
                else:
                    data_fmt = "NÃO INFORMADA"
                st.write(f"**Última movimentação:** `{data_fmt}`")

            m1, m2, m3 = st.columns(3)
            m1.metric("Análises (só EM)", int(analises_em))
            m2.metric("Reanálises", int(reanalises))
            m3.metric("Análises (EM + RE)", int(analises_total))

            m4, m5, m6 = st.columns(3)
            m4.metric("Aprovações (histórico)", int(aprovacoes_cli))
            m5.metric("Vendas (GER+INF histórico)", int(vendas_cli))
            m6.metric("VGV total (cliente x corretor)", format_currency(vgv_cli))

            # ---------- LINHA DO TEMPO COMPLETA (TABELA) ----------
            st.markdown("**Linha do tempo completa desse cliente com esse corretor:**")

            colunas_timeline = [
                "DIA",
                "EQUIPE",
                "CORRETOR",
                "CONSTRUTORA_BASE",
                "EMPREENDIMENTO_BASE",
                "SITUACAO_ORIGINAL",
                "STATUS_BASE",
                "OBSERVACOES_RAW",
                "OBSERVACOES2_RAW",
            ]
            colunas_existentes = [c for c in colunas_timeline if c in df_cli.columns]

            df_timeline = df_cli[colunas_existentes].copy()
            if "DIA" in df_timeline.columns:
                df_timeline["DIA"] = pd.to_datetime(
                    df_timeline["DIA"], errors="coerce"
                ).dt.strftime("%d/%m/%Y")

            df_timeline = df_timeline.rename(
                columns={
                    "DIA": "Data",
                    "EQUIPE": "Equipe",
                    "CORRETOR": "Corretor",
                    "CONSTRUTORA_BASE": "Construtora",
                    "EMPREENDIMENTO_BASE": "Empreendimento",
                    "SITUACAO_ORIGINAL": "Situação (planilha)",
                    "STATUS_BASE": "Status (classificado)",
                    "OBSERVACOES_RAW": "Observações",
                    "OBSERVACOES2_RAW": "Observações 2",
                }
            )

            st.dataframe(
                df_timeline,
                use_container_width=True,
                hide_index=True,
            )

# ---------------------------------------------------------
# LISTA COMPLETA – CLIENTES DO PERÍODO (FILTRO)
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 📋 Lista de clientes do período (filtro aplicado)")

cols_preferidas = [
    "NOME_CLIENTE_BASE",
    "CPF_CLIENTE_BASE",
    "EQUIPE",
    "CORRETOR",
    "EMPREENDIMENTO_BASE",
    "STATUS_BASE",
    "DIA",
    "VGV",
]
cols_existentes = [c for c in cols_preferidas if c in df_periodo.columns]

df_tabela = df_periodo[cols_existentes].copy()

if "DIA" in df_tabela.columns:
    df_tabela["DIA"] = pd.to_datetime(
        df_tabela["DIA"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

if "VGV" in df_tabela.columns:
    df_tabela["VGV"] = df_tabela["VGV"].apply(format_currency)

df_tabela = df_tabela.rename(
    columns={
        "NOME_CLIENTE_BASE": "Cliente",
        "CPF_CLIENTE_BASE": "CPF",
        "EQUIPE": "Equipe",
        "CORRETOR": "Corretor",
        "EMPREENDIMENTO_BASE": "Empreendimento",
        "STATUS_BASE": "Situação",
        "DIA": "Última movimentação",
    }
)

df_tabela = df_tabela.sort_values("Última movimentação", ascending=False)

st.dataframe(
    df_tabela,
    use_container_width=True,
    hide_index=True,
)
