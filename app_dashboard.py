from datetime import timedelta

import streamlit as st

from login import tela_login
from utils.commercial_repository import aplicar_perfil_corretor, carregar_base_comercial
from utils.crm_theme import apply_crm_theme, configure_page, format_currency, hero, metric_grid, section
from utils.dashboard_metrics import calcular_resumo_comercial, percentual


if "logado" not in st.session_state:
    st.session_state.logado = False

configure_page(logado=st.session_state.logado)
apply_crm_theme()

if not st.session_state.logado:
    tela_login()
    st.stop()

try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(interval=30 * 1000, key="auto_refresh_dashboard")
    if "auto_refresh_dashboard" in st.session_state:
        st.session_state["refresh_planilha"] = True
except Exception:
    pass

try:
    st.sidebar.image("logo_bruno_marinho.jpg", use_container_width=True)
except Exception:
    pass

if st.sidebar.button("Sair"):
    st.session_state.logado = False
    st.rerun()

perfil = st.session_state.get("perfil", "")
nome_usuario = st.session_state.get("nome_usuario", "").upper().strip()

if perfil == "corretor":
    st.sidebar.markdown("### Acesso do Corretor")
    st.sidebar.markdown("- Carteira de Clientes")
    st.sidebar.markdown("- Consulta de Clientes")
    st.sidebar.markdown("---")
    st.sidebar.warning("Demais paginas sao restritas")


@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados(_refresh_key=None):
    return carregar_base_comercial()


with st.spinner("Carregando base comercial..."):
    df = carregar_dados(_refresh_key=st.session_state.get("refresh_planilha"))

df = aplicar_perfil_corretor(df, perfil, nome_usuario)
if df.empty:
    st.error("Erro ao carregar base comercial.")
    st.stop()

st.sidebar.title("Filtros")
modo_periodo = st.sidebar.radio(
    "Modo de filtro do periodo",
    ["Por DIA (data do registro)", "Por DATA BASE (mes comercial)"],
    index=0,
)

dias_validos = df["DIA"].dropna()
bases_validas = df["DATA_BASE"].dropna()
if dias_validos.empty and bases_validas.empty:
    st.error("Sem datas validas para filtrar.")
    st.stop()

tipo_periodo = "DIA"
data_ini = None
data_fim = None
bases_selecionadas = []

if modo_periodo.startswith("Por DIA"):
    data_min = dias_validos.min()
    data_max = dias_validos.max()
    data_ini_default = max(data_min, data_max - timedelta(days=30))
    periodo = st.sidebar.date_input(
        "Periodo por DIA",
        value=(data_ini_default, data_max),
        min_value=data_min,
        max_value=data_max,
    )
    data_ini, data_fim = periodo
else:
    tipo_periodo = "DATA_BASE"
    bases_df = (
        df[["DATA_BASE", "DATA_BASE_LABEL"]]
        .dropna(subset=["DATA_BASE"])
        .drop_duplicates()
        .sort_values("DATA_BASE")
    )
    opcoes = bases_df["DATA_BASE_LABEL"].tolist()
    if not opcoes:
        st.error("Sem datas base validas para filtrar.")
        st.stop()
    default_labels = opcoes[-2:] if len(opcoes) >= 2 else opcoes
    bases_selecionadas = st.sidebar.multiselect(
        "Periodo por DATA BASE",
        options=opcoes,
        default=default_labels,
    )
    if not bases_selecionadas:
        bases_selecionadas = opcoes

lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)
base_cor = df if equipe_sel == "Todas" else df[df["EQUIPE"] == equipe_sel]

lista_corretor = sorted(base_cor["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

if tipo_periodo == "DIA":
    df_filtrado = df[(df["DIA"] >= data_ini) & (df["DIA"] <= data_fim)].copy()
else:
    df_filtrado = df[df["DATA_BASE_LABEL"].isin(bases_selecionadas)].copy()
    dias_sel = df_filtrado["DIA"].dropna()
    data_ini = dias_sel.min() if not dias_sel.empty else dias_validos.min()
    data_fim = dias_sel.max() if not dias_sel.empty else dias_validos.max()

if equipe_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]
if corretor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_filtrado)

if tipo_periodo == "DIA":
    periodo_str = f"{data_ini.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}"
else:
    periodo_str = bases_selecionadas[0] if len(bases_selecionadas) == 1 else f"{bases_selecionadas[0]} ate {bases_selecionadas[-1]}"

hero(
    "Painel Comercial",
    f"{registros_filtrados} registros filtrados · {equipe_sel} · {corretor_sel}",
    periodo_str,
)

filtro_vendas = st.radio(
    "Tipo de vendas consideradas nos indicadores",
    ["GERADAS + INFORMADAS", "Somente GERADAS"],
    index=0,
    horizontal=True,
)

resumo = calcular_resumo_comercial(df_filtrado, df, filtro_vendas)

section("Resumo de Analises & Vendas", "Principais indicadores comerciais do periodo")
metric_grid(
    [
        ("Em analise", resumo["em_analise"]),
        ("Reanalise", resumo["reanalise"]),
        ("Aprovacoes", resumo["aprovacoes"]),
        ("Aprovado Bacen", resumo["aprovado_bacen"]),
        ("Aprov. Restricao", resumo["aprovado_restricao"]),
        ("Reprovacoes", resumo["reprovacoes"]),
    ],
    columns=6,
)

metric_grid(
    [
        ("Vendas geradas", resumo["venda_gerada"]),
        ("Vendas informadas", resumo["venda_informada"]),
        ("Total vendas", resumo["vendas_total"]),
    ],
    columns=3,
)

section("Taxas de Conversao", "Leitura rapida da eficiencia comercial")
cols = st.columns(3)
cols[0].metric("Aprov./Analises", percentual(resumo["taxa_aprov_analise"]))
cols[1].metric("Vendas/Analises", percentual(resumo["taxa_venda_analise"]))
cols[2].metric("Vendas/Aprovacoes", percentual(resumo["taxa_venda_aprov"]))

section("Indicadores de VGV", "Valores calculados apenas sobre clientes com venda")
metric_grid(
    [
        ("VGV Total", resumo["vgv_total"]),
        ("Ticket Medio", resumo["ticket_medio"]),
        ("Maior VGV", resumo["maior_vgv"]),
    ],
    columns=3,
    currency_labels={"VGV Total", "Ticket Medio", "Maior VGV"},
)

st.markdown(
    f"<p style='text-align:center; color:#64748b; margin-top:2rem;'>Painel Comercial · base atual: Google Sheets · VGV total {format_currency(resumo['vgv_total'])}</p>",
    unsafe_allow_html=True,
)
