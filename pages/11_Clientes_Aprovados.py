import streamlit as st
import pandas as pd
from datetime import date, timedelta

if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Acesso restrito. Faça login para continuar.")
    st.stop()

# ---------------------------------------------------------
# BLOQUEIO DE PERFIL CORRETOR
# ---------------------------------------------------------
if st.session_state.get("perfil") == "corretor":
    st.warning("🔒 Você não tem permissão para acessar esta página.")
    st.stop()

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Clientes Aprovados – MR Imóveis",
    page_icon="✅",
    layout="wide",
)

# ---------------------------------------------------------
# LOGO
# ---------------------------------------------------------
LOGO_PATH = "logo_bruno_marinho.jpg"

col_logo, col_tit = st.columns([1, 4])

with col_logo:
    try:
        st.image(LOGO_PATH, use_column_width=True)
    except Exception:
        pass

with col_tit:
    st.markdown("## Clientes Aprovados")
    st.caption(
        "Aqui aparecem clientes cuja **situação atual** está como "
        "**APROVAÇÃO**, **APROVADO BACEN** ou **APROVADO COM RESTRIÇÃO**."
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
# ---------------------------------------------------------
@st.cache_data(ttl=60)
def carregar_dados():
    df = pd.read_csv(CSV_URL)

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

    col_construtora = next(
        (c for c in possiveis_construtora if c in df.columns), None
    )
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

    # STATUS BASE + SITUAÇÃO ORIGINAL (EXATAMENTE COMO NA PLANILHA)
    possiveis_cols_situacao = [
        "SITUAÇÃO",
        "SITUAÇÃO ATUAL",
        "STATUS",
        "SITUACAO",
        "SITUACAO ATUAL",
    ]
    col_situacao = next(
        (c for c in possiveis_cols_situacao if c in df.columns), None
    )

    df["STATUS_BASE"] = ""
    if col_situacao:
        # guarda o texto original (do jeito da planilha)
        status_original = df[col_situacao].fillna("").astype(str).str.strip()
        status_upper = status_original.str.upper()

        df.loc[status_upper.str.contains("EM ANÁLISE"), "STATUS_BASE"] = "EM ANÁLISE"
        df.loc[status_upper.str.contains("REANÁLISE"), "STATUS_BASE"] = "REANÁLISE"

        # APROVADOS
        # considera:
        # - APROVAÇÃO
        # - APROVADO BACEN
        # - APROVADO COM RESTRIÇÃO
        df.loc[
            status_upper.str.contains(r"\bAPROVAÇÃO\b", regex=True)
            | status_upper.str.contains("APROVADO BACEN", regex=False)
            | status_upper.str.contains("APROVADO COM RESTRIÇÃO", regex=False),
            "STATUS_BASE"
        ] = "APROVADO"

        df.loc[status_upper.str.contains("REPROV"), "STATUS_BASE"] = "REPROVADO"
        df.loc[status_upper.str.contains("VENDA GERADA"), "STATUS_BASE"] = "VENDA GERADA"
        df.loc[status_upper.str.contains("VENDA INFORMADA"), "STATUS_BASE"] = "VENDA INFORMADA"

        # aqui vai exatamente o que está na planilha
        df["SITUACAO_ORIGINAL"] = status_original
    else:
        df["SITUACAO_ORIGINAL"] = "NÃO INFORMADO"

    # OBS / VGV
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

    col_nome = next((c for c in possiveis_nome if c in df.columns), None)
    col_cpf = next((c for c in possiveis_cpf if c in df.columns), None)

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

    if col_cpf is None:
        df["CPF_CLIENTE_BASE"] = ""
    else:
        df["CPF_CLIENTE_BASE"] = (
            df[col_cpf]
            .fillna("")
            .astype(str)
            .str.replace(r"\D", "", regex=True)
        )

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
else:
    st.error("Não encontrei coluna de cliente na base.")
    st.stop()

# garante datetime
df["DIA"] = pd.to_datetime(df["DIA"], errors="coerce")
df_valid = df.dropna(subset=["DIA"]).copy()
df_valid = df_valid.sort_values(by=[col_cliente, "DIA"])

# Última linha por cliente (status atual)
df_status_atual = df_valid.drop_duplicates(subset=[col_cliente], keep="last").copy()

# apenas APROVADOS
df_aprovados_atual = df_status_atual[
    df_status_atual["STATUS_BASE"] == "APROVADO"
].copy()

# ---------------------------------------------------------
# SELETOR DE TIPO DE APROVAÇÃO
# ---------------------------------------------------------
tipos_aprovacao = (
    df_aprovados_atual["SITUACAO_ORIGINAL"]
    .dropna()
    .astype(str)
    .str.upper()
    .str.strip()
    .sort_values()
    .unique()
    .tolist()
)

tipo_aprovacao_sel = st.selectbox(
    "Tipo de aprovação:",
    ["Todos"] + tipos_aprovacao,
    index=0
)

if tipo_aprovacao_sel != "Todos":
    df_aprovados_atual = df_aprovados_atual[
        df_aprovados_atual["SITUACAO_ORIGINAL"]
        .str.upper()
        .str.strip() == tipo_aprovacao_sel
    ].copy()

if df_aprovados_atual.empty:
    st.info("Nenhum cliente encontrado para esse tipo de aprovação.")
    st.stop()

# ---------------------------------------------------------
# SIDEBAR – BUSCA
# ---------------------------------------------------------
st.sidebar.title("Busca de clientes aprovados 🔎")

tipo_busca = st.sidebar.radio("Buscar por:", ("Nome (parcial)", "CPF"))
termo_busca = st.sidebar.text_input("Digite o nome ou CPF do cliente")

st.sidebar.caption(
    "• Nome: pode digitar só uma parte (ex: 'SILVA')\n"
    "• CPF: digite apenas números (sem ponto/traço)"
)

# ---------------------------------------------------------
# PERÍODO + FILTROS
# ---------------------------------------------------------
st.markdown("### 📅 Período das aprovações")

periodo = st.radio(
    "Selecione o período (dias):",
    [7, 15, 30, 60, 90],
    index=2,
    horizontal=True,
)

data_ref = df_valid["DIA"].max()
limite_tempo = data_ref - timedelta(days=periodo)

df_aprovados_periodo = df_aprovados_atual[
    df_aprovados_atual["DIA"] >= limite_tempo
].copy()

if df_aprovados_periodo.empty:
    st.info(f"Não há aprovação nos últimos {periodo} dias.")
    st.stop()

df_filtrado = df_aprovados_periodo.copy()

st.markdown("Filtrar por equipe:")
if "EQUIPE" in df_filtrado.columns:
    equipes = (
        df_filtrado["EQUIPE"]
        .dropna()
        .astype(str)
        .sort_values()
        .unique()
        .tolist()
    )
    equipe_sel = st.selectbox("", ["Todas"] + equipes, index=0)

    if equipe_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel].copy()

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
    corretor_sel = st.selectbox("", ["Todos"] + corretores, index=0)

    if corretor_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel].copy()

if df_filtrado.empty:
    st.info("Nenhum cliente aprovado dentro desse filtro.")
    st.stop()

# ---------------------------------------------------------
# CARDS GERAIS
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
c3.metric("Equipes com aprovação", int(equipes_com_aprovados))

k1, k2, k3 = st.columns(3)
k1.metric("VGV total", format_currency(vgv_total))
k2.metric("Ticket médio", format_currency(ticket_medio))
k3.metric(
    "Média aprovações por equipe",
    f"{total_aprovados / max(equipes_com_aprovados, 1):.1f}",
)

# ---------------------------------------------------------
# DETALHES POR CLIENTE – QUANDO HOUVER BUSCA
# ---------------------------------------------------------
if termo_busca.strip():
    termo_limpo = termo_busca.strip().upper()
    df_resultado = pd.DataFrame()

    if tipo_busca.startswith("Nome"):
        df_resultado = df[
            df["NOME_CLIENTE_BASE"].str.contains(termo_limpo, na=False)
        ].copy()
    else:
        termo_cpf = "".join(ch for ch in termo_busca if ch.isdigit())
        df_resultado = df[
            df["CPF_CLIENTE_BASE"].str.contains(termo_cpf, na=False)
        ].copy()

    if df_resultado.empty:
        st.warning("Nenhum cliente encontrado com esse critério de busca.")
    else:
        # garante chave e datas
        df_resultado["CHAVE_CLIENTE"] = (
            df_resultado["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
            + " | "
            + df_resultado["CPF_CLIENTE_BASE"].fillna("")
        )
        df_resultado["DIA"] = pd.to_datetime(df_resultado["DIA"], errors="coerce")

        # chaves que estão aprovadas dentro do filtro atual
        df_filtrado["CHAVE_CLIENTE"] = (
            df_filtrado["NOME_CLIENTE_BASE"].fillna("NÃO INFORMADO")
            + " | "
            + df_filtrado["CPF_CLIENTE_BASE"].fillna("")
        )
        chaves_aprovados = set(df_filtrado["CHAVE_CLIENTE"].unique())

        df_resultado_ordenado = df_resultado.sort_values(
            by=["CHAVE_CLIENTE", "DIA"]
        ).copy()

        def conta_analises(s):
            return s.isin(["EM ANÁLISE", "REANÁLISE"]).sum()

        def conta_aprovacoes(s):
            return (s == "APROVADO").sum()

        def conta_vendas(s):
            return s.isin(["VENDA GERADA", "VENDA INFORMADA"]).sum()

        resumo = (
            df_resultado_ordenado.groupby("CHAVE_CLIENTE")
            .agg(
                NOME=("NOME_CLIENTE_BASE", "first"),
                CPF=("CPF_CLIENTE_BASE", "first"),
                ANALISES=("STATUS_BASE", conta_analises),
                APROVACAOES=("STATUS_BASE", conta_aprovacoes),
                VENDAS=("STATUS_BASE", conta_vendas),
                VGV=("VGV", "sum"),
                ULT_STATUS=("SITUACAO_ORIGINAL", "last"),
                ULT_DATA=("DIA", "max"),
            )
            .reset_index()
        )

        resumo = resumo[resumo["CHAVE_CLIENTE"].isin(chaves_aprovados)].copy()

        if resumo.empty:
            st.warning(
                "Cliente encontrado, mas não está com status atual APROVAÇÃO "
                f"dentro do filtro de período/equipe/corretor."
            )
        else:
            # VISÃO GERAL
            st.markdown(
                f"### 🔍 Resultado da busca – {len(resumo)} cliente(s) encontrado(s)"
            )

            visao_cols = [
                "NOME",
                "CPF",
                "ULT_STATUS",
                "ULT_DATA",
                "ANALISES",
                "APROVACAOES",
                "VENDAS",
                "VGV",
            ]
            visao = resumo[visao_cols].copy()

            visao["ULT_DATA"] = pd.to_datetime(
                visao["ULT_DATA"], errors="coerce"
            ).dt.strftime("%d/%m/%Y")
            visao["VGV"] = visao["VGV"].apply(format_currency)

            visao = visao.rename(
                columns={
                    "NOME": "NOME",
                    "CPF": "CPF",
                    "ULT_STATUS": "ULT_STATUS",
                    "ULT_DATA": "ULT_DATA",
                    "ANALISES": "ANALISES",
                    "APROVACAOES": "APROVACAOES",
                    "VENDAS": "VENDAS",
                    "VGV": "VGV",
                }
            )

            st.markdown("#### 🗂 Visão geral")
            st.dataframe(
                visao,
                use_container_width=True,
                hide_index=True,
            )

            # DETALHAMENTO POR CLIENTE
            st.markdown("### 📂 Detalhamento por cliente")

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

            for _, row in resumo.sort_values(
                ["VENDAS", "VGV"], ascending=False
            ).iterrows():
                chave = row["CHAVE_CLIENTE"]
                df_cli = df_resultado_ordenado[
                    df_resultado_ordenado["CHAVE_CLIENTE"] == chave
                ].copy()

                df_cli = df_cli.sort_values("DIA")
                ultima_linha = df_cli.iloc[-1]

                ult_constr = ultima_linha.get("CONSTRUTORA_BASE", "NÃO INFORMADO")
                ult_empr = ultima_linha.get("EMPREENDIMENTO_BASE", "NÃO INFORMADO")
                ult_corretor = ultima_linha.get("CORRETOR", "NÃO INFORMADO")
                ult_status_original = ultima_linha.get(
                    "SITUACAO_ORIGINAL", row["ULT_STATUS"]
                )

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
                    situacao_fmt = ult_status_original or "NÃO INFORMADO"

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
                        data_fmt = pd.to_datetime(row["ULT_DATA"]).strftime(
                            "%d/%m/%Y"
                        )
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
                m6.metric("VGV total", format_currency(row["VGV"]))

# ---------------------------------------------------------
# LINHA DE SEPARAÇÃO
# ---------------------------------------------------------
st.markdown("---")

# ---------------------------------------------------------
# TABELA CLEAN
# ---------------------------------------------------------
st.markdown("### 📋 Lista de clientes aprovados (status atual)")

colunas_preferidas = [
    "NOME_CLIENTE_BASE",
    "CPF_CLIENTE_BASE",
    "EQUIPE",
    "CORRETOR",
    "EMPREENDIMENTO_BASE",
    "SITUACAO_ORIGINAL",
    "DIA",
]
colunas_existentes = [c for c in colunas_preferidas if c in df_filtrado.columns]

df_tabela = df_filtrado[colunas_existentes].copy()

if "DIA" in df_tabela.columns:
    df_tabela["DIA"] = pd.to_datetime(
        df_tabela["DIA"], errors="coerce"
    ).dt.strftime("%d/%m/%Y")

df_tabela = df_tabela.rename(
    columns={
        "NOME_CLIENTE_BASE": "Cliente",
        "CPF_CLIENTE_BASE": "CPF",
        "EQUIPE": "Equipe",
        "CORRETOR": "Corretor",
        "EMPREENDIMENTO_BASE": "Empreendimento",
        "SITUACAO_ORIGINAL": "Tipo de aprovação",
        "DIA": "Última atualização",
    }
)

df_tabela = df_tabela.sort_values("Última atualização", ascending=False)

st.dataframe(
    df_tabela,
    use_container_width=True,
    hide_index=True,
)