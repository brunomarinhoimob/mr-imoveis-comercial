import streamlit as st
import pandas as pd
from datetime import date, timedelta

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes Aprovados – MR Imóveis",
    page_icon="✅",
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
    st.markdown("## Clientes Aprovados")
    st.caption(
        "Aqui aparecem apenas clientes cuja **situação atual** está como "
        "**APROVADO** (ou seja, a última ação registrada na base é aprovação), "
        "com filtro por período, equipe, corretor, e busca por nome/CPF."
    )


# ---------------------------------------------------------
# FUNÇÃO AUXILIAR PARA LIMPAR DATA
# ---------------------------------------------------------
def limpar_para_data(serie):
    dt = pd.to_datetime(serie, dayfirst=True, errors="coerce")
    return dt.dt.date


# ---------------------------------------------------------
# CONFIG: LINK DA PLANILHA (MESMO DA PÁGINA CLIENTES EM ANÁLISE)
# ---------------------------------------------------------
SHEET_ID = "1Ir_fPugLsfHNk6iH0XPCA6xM92bq8tTrn7UnunGRwCw"
GID_ANALISES = "1574157905"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ANALISES}"


# ---------------------------------------------------------
# CARREGAR E PREPARAR DADOS
# (MESMA BASE E LÓGICA DO CLIENTES EM ANÁLISE)
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

    # Padroniza nomes de colunas
    df.columns = [c.strip().upper() for c in df.columns]

    # DATA / DIA
    if "DATA" in df.columns:
        df["DIA"] = limpar_para_data(df["DATA"])
    elif "DIA" in df.columns:
        df["DIA"] = limpar_para_data(df["DIA"])
    else:
        df["DIA"] = pd.NaT

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

    col_construtora = None
    for c in possiveis_construtora:
        if c in df.columns:
            col_construtora = c
            break

    col_empreend = None
    for c in possiveis_empreend:
        if c in df.columns:
            col_empreend = c
            break

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

    # STATUS BASE + SITUAÇÃO ORIGINAL
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = None
    for c in possiveis_cols_situacao:
        if c in df.columns:
            col_situacao = c
            break

    df["STATUS_BASE"] = ""
    if col_situacao:
        status = df[col_situacao].fillna("").astype(str).str.upper()
        df.loc[status.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"
        df.loc[status.str.contains("APROV"), "STATUS_BASE"] = "APROVADO"
        df.loc[status.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

        df["SITUACAO_ORIGINAL"] = (
            df[col_situacao].fillna("").astype(str).str.upper().str.strip()
        )
    else:
        df["SITUACAO_ORIGINAL"] = "NÃO INFORMADO"

    # OBSERVAÇÕES / VGV
    if "OBSERVAÇÕES" in df.columns:
        df["OBSERVACOES_RAW"] = (
            df["OBSERVAÇÕES"].fillna("").astype(str).str.strip()
        )
        df["VGV"] = pd.to_numeric(df["OBSERVAÇÕES"], errors="coerce").fillna(0.0)
    else:
        df["OBSERVACOES_RAW"] = ""
        df["VGV"] = 0.0

    # NOME / CPF
    possiveis_nome = ["NOME", "CLIENTE", "NOME CLIENTE", "NOME DO CLIENTE"]
    possiveis_cpf = ["CPF", "CPF CLIENTE", "CPF DO CLIENTE"]

    col_nome = None
    for c in possiveis_nome:
        if c in df.columns:
            col_nome = c
            break

    col_cpf = None
    for c in possiveis_cpf:
        if c in df.columns:
            col_cpf = c
            break

    if col_nome is None:
        df["NOME_CLIENTE_BASE"] = "NÃO INFORMADO"
    else:
        df["NOME_CLIENTE_BASE"] = (
            df[col_nome].fillna("NÃO INFORMADO").astype(str).str.upper().str.strip()
        )

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

    # Chave única CLIENTE (nome + CPF) para agrupar histórico
    df["CHAVE_CLIENTE"] = (
        df["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
        + " | "
        + df["CPF_CLIENTE_BASE"].fillna("")
    )

    return df


df = carregar_dados()

if df.empty:
    st.error("Não foi possível carregar dados da planilha.")
    st.stop()

# ---------------------------------------------------------
# DEFINIÇÕES BÁSICAS
# ---------------------------------------------------------
if "NOME_CLIENTE_BASE" in df.columns:
    col_cliente = "NOME_CLIENTE_BASE"
elif "CLIENTE" in df.columns:
    col_cliente = "CLIENTE"
else:
    st.error("Não encontrei coluna de cliente na base.")
    st.stop()

if "DIA" not in df.columns:
    st.error("Não encontrei coluna DIA na base.")
    st.stop()

# Garantir datetime
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
df_valid = df.dropna(subset=["DIA"]).copy()
df_valid = df_valid.sort_values(by=[col_cliente, "DIA"])

# Última linha = status atual
df_status_atual = df_valid.drop_duplicates(subset=[col_cliente], keep="last").copy()

# Filtra quem está APROVADO na situação atual
df_aprovados_atual = df_status_atual[df_status_atual["STATUS_BASE"] == "APROVADO"].copy()

if df_aprovados_atual.empty:
    st.info("No momento não há clientes com status atual APROVADO.")
    st.stop()

# ---------------------------------------------------------
# BARRA LATERAL – BUSCA (NOME / CPF)
# ---------------------------------------------------------
st.sidebar.title("Busca de clientes aprovados 🔎")

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
    "• CPF: digite só números (não precisa de ponto ou traço)"
)

# ---------------------------------------------------------
# SELETOR DE PERÍODO + FILTROS POR EQUIPE E CORRETOR
# ---------------------------------------------------------
st.markdown("### 📅 Período das aprovações")

# Período (dias)
periodo = st.radio(
    "Selecione o período (dias):",
    [7, 15, 30, 60, 90],
    index=2,
    horizontal=True,
)

data_ref = df_valid["DIA"].max()
limite_tempo = data_ref - timedelta(days=periodo)

# Clientes aprovados cuja última movimentação é dentro do período
df_aprovados_periodo = df_aprovados_atual[
    df_aprovados_atual["DIA"] >= limite_tempo
].copy()

if df_aprovados_periodo.empty:
    st.info(f"Não há clientes aprovados nos últimos {periodo} dias.")
    st.stop()

# Filtro por equipe
df_filtrado = df_aprovados_periodo.copy()

st.markdown("Filtrar por equipe:")
if "EQUIPE" in df_aprovados_periodo.columns:
    equipes = (
        df_aprovados_periodo["EQUIPE"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    equipe_sel = st.selectbox(
        "",
        options=["Todas"] + equipes,
        index=0,
    )

    if equipe_sel != "Todas":
        df_filtrado = df_aprovados_periodo[
            df_aprovados_periodo["EQUIPE"] == equipe_sel
        ].copy()
else:
    st.warning("Coluna 'EQUIPE' não encontrada. Filtro por equipe desativado.")

# Filtro por corretor
st.markdown("Filtrar por corretor:")
if "CORRETOR" in df_filtrado.columns:
    corretores = (
        df_filtrado["CORRETOR"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )

    corretor_sel = st.selectbox(
        "Selecione o corretor (opcional):",
        options=["Todos"] + corretores,
        index=0,
    )

    if corretor_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel].copy()
else:
    st.warning("Coluna 'CORRETOR' não encontrada. Filtro por corretor desativado.")

if df_filtrado.empty:
    st.info("Nenhum cliente aprovado dentro desse filtro.")
    st.stop()

# ---------------------------------------------------------
# CARDS GERAIS DO PERÍODO
# ---------------------------------------------------------
total_aprovados = len(df_filtrado)
equipes_com_aprovados = df_filtrado["EQUIPE"].nunique()
vgv_total = df_filtrado["VGV"].sum()
ticket_medio = vgv_total / total_aprovados if total_aprovados > 0 else 0.0


def format_currency(valor: float) -> str:
    return (
        f"R$ {valor:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


c1, c2, c3 = st.columns(3)
c1.metric("Clientes aprovados (status atual)", total_aprovados)
c2.metric("Período (dias)", int(periodo))
c3.metric("Equipes com aprovados", int(equipes_com_aprovados))

k1, k2, k3 = st.columns(3)
k1.metric("VGV total das aprovações", format_currency(vgv_total))
k2.metric("Ticket médio (VGV/cliente)", format_currency(ticket_medio))
k3.metric("Média aprovações por equipe", f"{total_aprovados / max(equipes_com_aprovados, 1):.1f}")

# ---------------------------------------------------------
# DETALHES POR CLIENTE (CARDS via BUSCA)
# ---------------------------------------------------------
# Só mostra cards detalhados se o usuário digitou algo na busca
if termo_busca.strip():
    df_resultado = pd.DataFrame()
    termo_limpo = termo_busca.strip().upper()

    if tipo_busca.startswith("Nome"):
        df_resultado = df[df["NOME_CLIENTE_BASE"].str.contains(termo_limpo, na=False)].copy()
    else:
        termo_cpf = "".join(ch for ch in termo_busca if ch.isdigit())
        df_resultado = df[df["CPF_CLIENTE_BASE"].str.contains(termo_cpf, na=False)].copy()

    if df_resultado.empty:
        st.warning("Nenhum cliente encontrado com esse critério de busca.")
    else:
        # Usa mesma chave única
        df_resultado["CHAVE_CLIENTE"] = (
            df_resultado["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
            + " | "
            + df_resultado["CPF_CLIENTE_BASE"].fillna("")
        )

        df_filtrado["CHAVE_CLIENTE"] = (
            df_filtrado["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
            + " | "
            + df_filtrado["CPF_CLIENTE_BASE"].fillna("")
        )

        chaves_aprovados = set(df_filtrado["CHAVE_CLIENTE"].unique())

        # Resumo por cliente
        def conta_analises(s):
            return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()

        def conta_aprovacoes(s):
            return (s == "APROVADO").sum()

        def conta_vendas(s):
            return s.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()

        resumo = (
            df_resultado.groupby("CHAVE_CLIENTE")
            .agg(
                NOME=("NOME_CLIENTE_BASE", "first"),
                CPF=("CPF_CLIENTE_BASE", "first"),
                ANALISES=("STATUS_BASE", conta_analises),
                APROVACAOES=("STATUS_BASE", conta_aprovacoes),
                VENDAS=("STATUS_BASE", conta_vendas),
                VGV=("VGV", "sum"),
                ULT_STATUS=(
                    "SITUACAO_ORIGINAL",
                    lambda x: x.iloc[-1] if len(x) > 0 else "",
                ),
                ULT_DATA=("DIA", lambda x: x.max()),
            )
            .reset_index()
        )

        # Mantém apenas clientes cujo status atual (dentro do filtro) é APROVADO
        resumo = resumo[resumo["CHAVE_CLIENTE"].isin(chaves_aprovados)].copy()

        if resumo.empty:
            st.warning(
                "Cliente encontrado, mas não está com status atual APROVADO "
                f"dentro do filtro de período/equipe/corretor."
            )
        else:
            st.markdown("### 💳 Detalhes por cliente aprovado (cards)")

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

            # Cards por cliente
            for _, row in resumo.sort_values(["VENDAS", "VGV"], ascending=False).iterrows():
                chave = row["CHAVE_CLIENTE"]
                df_cli = df_resultado[df_resultado["CHAVE_CLIENTE"] == chave].copy()

                df_cli = df_cli.sort_values("DIA")
                ultima_linha = df_cli.iloc[-1]

                ult_constr = ultima_linha.get("CONSTRUTORA_BASE", "NÃO INFORMADO")
                ult_empr = ultima_linha.get("EMPREENDIMENTO_BASE", "NÃO INFORMADO")
                ult_corretor = ultima_linha.get("CORRETOR", "NÃO INFORMADO")

                obs_validas = [
                    obs
                    for obs in df_cli["OBSERVACOES_RAW"].fillna("")
                    if obs and not observacao_e_numero(obs)
                ]
                ultima_obs = obs_validas[-1] if obs_validas else ""

                analises_em = (df_cli["STATUS_BASE"] == "EM ANÁLISE").sum()
                reanalises = (df_cli["STATUS_BASE"] == "REANÁLISE").sum()
                analises_total = analises_em + reanalises

                st.markdown("---")
                st.markdown(f"##### 👤 {row['NOME']}")

                col_top1, col_top2 = st.columns(2)

                with col_top1:
                    cpf_fmt = row["CPF"] if row["CPF"] else "NÃO INFORMADO"
                    situacao_fmt = row["ULT_STATUS"] or "NÃO INFORMADO"

                    st.write(f"**CPF:** `{cpf_fmt}`")
                    st.write(f"**Situação atual:** `{situacao_fmt}`")
                    st.write(
                        f"**Corretor responsável (última movimentação):** `{ult_corretor}`"
                    )
                    st.write(
                        f"**Construtora (última movimentação):** `{ult_constr}`"
                    )
                    st.write(
                        f"**Empreendimento (última movimentação):** `{ult_empr}`"
                    )
                    if ultima_obs:
                        st.write(f"**Última observação:** `{ultima_obs}`")

                with col_top2:
                    if pd.notna(row["ULT_DATA"]):
                        data_fmt = row["ULT_DATA"].strftime("%d/%m/%Y")
                    else:
                        data_fmt = "NÃO INFORMADA"
                    st.write(f"**Última movimentação:** `{data_fmt}`")

                m1, m2, m3 = st.columns(3)
                m1.metric("Análises (só EM)", int(analises_em))
                m2.metric("Reanálises", int(reanalises))
                m3.metric("Análises (EM + RE)", int(analises_total))

                m4, m5, m6 = st.columns(3)
                m4.metric("Aprovações", int(row["APROVACAOES"]))
                m5.metric("Vendas", int(row["VENDAS"]))
                m6.metric(
                    "VGV total",
                    format_currency(row["VGV"]),
                )

# ---------------------------------------------------------
# LINHA DE SEPARAÇÃO
# ---------------------------------------------------------
st.markdown("---")

# ---------------------------------------------------------
# TABELA MAIS CLEAN (RENOMEADA E FORMATADA)
# ---------------------------------------------------------
st.markdown("### 📋 Lista de clientes aprovados (status atual)")

colunas_preferidas = [
    "NOME_CLIENTE_BASE",
    "CPF_CLIENTE_BASE",
    "EQUIPE",
    "CORRETOR",
    "EMPREENDIMENTO_BASE",
    "STATUS_BASE",
    "DIA",
]
colunas_existentes = [c for c in colunas_preferidas if c in df_filtrado.columns]

df_tabela = df_filtrado[colunas_existentes].copy()

# Formata data
if "DIA" in df_tabela.columns:
    df_tabela["DIA"] = pd.to_datetime(df_tabela["DIA"], errors="coerce").dt.strftime(
        "%d/%m/%Y"
    )

# Renomeia colunas para ficar mais bonito
renomear = {
    "NOME_CLIENTE_BASE": "Cliente",
    "CPF_CLIENTE_BASE": "CPF",
    "EQUIPE": "Equipe",
    "CORRETOR": "Corretor",
    "EMPREENDIMENTO_BASE": "Empreendimento",
    "STATUS_BASE": "Status",
    "DIA": "Última atualização",
}
df_tabela = df_tabela.rename(columns=renomear)

df_tabela = df_tabela.sort_values("Última atualização", ascending=False)

st.dataframe(
    df_tabela,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------------
# RESUMO POR EQUIPE
# ---------------------------------------------------------
if "Equipe" in df_tabela.columns:
    st.markdown("### 👥 Clientes aprovados por equipe")

    resumo_equipe = (
        df_tabela.groupby("Equipe")["Cliente"]
        .nunique()
        .reset_index(name="Qtde Clientes")
        .sort_values("Qtde Clientes", ascending=False)
    )

    st.dataframe(resumo_equipe, use_container_width=True, hide_index=True)
