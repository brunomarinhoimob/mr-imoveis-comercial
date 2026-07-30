from datetime import date, timedelta

import pandas as pd
import streamlit as st

from login import tela_login
from utils.commercial_repository import aplicar_perfil_corretor, baixar_export_atividades_piperun, carregar_base_comercial
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

    st_autorefresh(interval=30 * 60 * 1000, key="auto_refresh_dashboard")
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


@st.cache_data(ttl=30 * 60, show_spinner=False)
def carregar_dados(max_pages: int, per_page: int, data_ini: date, data_fim: date, _refresh_key=None):
    return carregar_base_comercial(
        fonte="piperun",
        max_pages=max_pages,
        per_page=per_page,
        data_ini=data_ini,
        data_fim=data_fim,
    )


def serie_data(valor):
    datas = pd.to_datetime(valor, errors="coerce")
    return datas.apply(lambda item: item.date() if pd.notna(item) else None)


per_page = 100
max_pages = 5

st.sidebar.title("Filtros")
hoje = date.today()
data_ini = st.sidebar.date_input("Data inicial", value=hoje - timedelta(days=7), format="DD/MM/YYYY")
data_fim = st.sidebar.date_input("Data final", value=hoje, format="DD/MM/YYYY")
if data_ini > data_fim:
    st.error("A data inicial nao pode ser maior que a data final.")
    st.stop()

st.sidebar.markdown("### Exportacao")
if st.sidebar.button("Atualizar atividades do PipeRun"):
    with st.spinner("Baixando exportacao de atividades do PipeRun..."):
        ok, mensagem = baixar_export_atividades_piperun(data_ini, data_fim)
    if ok:
        carregar_dados.clear()
        st.session_state["refresh_planilha"] = str(pd.Timestamp.now())
        st.sidebar.success("Exportacao atualizada.")
        st.rerun()
    else:
        st.sidebar.warning(mensagem)
        st.sidebar.link_button("Abrir exportacao no PipeRun", "https://app.pipe.run/v2/settings/exports/activities")

with st.spinner("Carregando base comercial..."):
    df = carregar_dados(
        max_pages=max_pages,
        per_page=per_page,
        data_ini=data_ini,
        data_fim=data_fim,
        _refresh_key=st.session_state.get("refresh_planilha"),
    )

df = aplicar_perfil_corretor(df, perfil, nome_usuario)
if df.empty:
    st.error("Nenhuma informacao carregada. Coloque a exportacao do PipeRun na pasta data com nome iniciando por atividades.")
    st.stop()

dias_validos = df["DIA"].dropna()
bases_validas = df["DATA_BASE"].dropna()
if dias_validos.empty and bases_validas.empty:
    st.error("Sem datas validas para filtrar.")
    st.stop()

lista_equipes = sorted(df["EQUIPE"].dropna().unique())
equipe_sel = st.sidebar.selectbox("Equipe", ["Todas"] + lista_equipes)
base_cor = df if equipe_sel == "Todas" else df[df["EQUIPE"] == equipe_sel]

lista_corretor = sorted(base_cor["CORRETOR"].dropna().unique())
corretor_sel = st.sidebar.selectbox("Corretor", ["Todos"] + lista_corretor)

dia_ref = serie_data(df["DIA"])
mask_dia = dia_ref.notna() & (dia_ref >= data_ini) & (dia_ref <= data_fim)
if "DATA_1_ANALISE" in df.columns:
    data_analise = serie_data(df["DATA_1_ANALISE"])
    mask_analise = data_analise.notna() & (data_analise >= data_ini) & (data_analise <= data_fim)
else:
    mask_analise = pd.Series(False, index=df.index)
df_filtrado = df[mask_dia | mask_analise].copy()

if equipe_sel != "Todas":
    df_filtrado = df_filtrado[df_filtrado["EQUIPE"] == equipe_sel]
if corretor_sel != "Todos":
    df_filtrado = df_filtrado[df_filtrado["CORRETOR"] == corretor_sel]

registros_filtrados = len(df_filtrado)

periodo_str = f"{data_ini.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')}"

hero(
    "Painel Comercial",
    f"{registros_filtrados} registros filtrados · {equipe_sel} · {corretor_sel}",
    periodo_str,
)

filtro_vendas = "Somente GERADAS"

resumo = calcular_resumo_comercial(df_filtrado, df, filtro_vendas)

section("Resumo do Credito", "Leads unicos com atividade registrada no periodo")
metric_grid(
    [
        ("Analises", resumo["nova_analise"]),
        ("Conferencia Pasteiro", resumo["conferencia_pasteiro"]),
        ("Recusa Pasteiro", resumo["recusa_pasteiro"]),
        ("Analise de credito", resumo["analise_credito"]),
        ("Doc pendente", resumo["doc_pendente"]),
    ],
    columns=5,
)

metric_grid(
    [
        ("Condicionado", resumo["condicionado"]),
        ("Restricao", resumo["restricao"]),
        ("Reprovado", resumo["reprovado"]),
        ("Aprovado c/ pendencia", resumo["aprovado_pendencia"]),
        ("Aprovado", resumo["aprovado"]),
    ],
    columns=5,
)

section("Vendas", "Somente leads marcados como ganho no PipeRun")
metric_grid(
    [
        ("Vendas geradas", resumo["venda_gerada"]),
        ("Total vendas", resumo["vendas_total"]),
    ],
    columns=2,
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
    f"<p style='text-align:center; color:#64748b; margin-top:2rem;'>Painel Comercial - base atual: PipeRun - VGV total {format_currency(resumo['vgv_total'])}</p>",
    unsafe_allow_html=True,
)
