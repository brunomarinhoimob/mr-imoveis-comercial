
metricas = build_performance(
    deals_raw=deals_result.data,
    actions_raw=actions_df,
    data_ini=data_ini,
    data_fim=data_fim,
    remanejo_dias=int(remanejo_dias),
    reference_maps=reference_maps,
)

df_geral = metricas["geral"]
df_equipe = metricas["equipe"]
df_corretor = metricas["corretor"]

if perfil == "corretor" and nome_usuario and "responsavel" in df_corretor.columns:
    df_corretor = df_corretor[df_corretor["responsavel"] == nome_usuario].copy()
    equipes_visiveis = df_corretor["equipe"].unique().tolist()
    df_equipe = df_equipe[df_equipe["equipe"].isin(equipes_visiveis)].copy()
    numeric_cols = [c for c in df_corretor.columns if c not in ["equipe", "responsavel"]]
    df_geral = pd.DataFrame([{**{"visao": "GERAL"}, **{c: int(df_corretor[c].sum()) for c in numeric_cols}}])

st.caption(
    f"Periodo: {data_ini.strftime('%d/%m/%Y')} ate {data_fim.strftime('%d/%m/%Y')} | "
    f"Endpoint principal: {deals_result.endpoint} | "
    f"Leads carregados: {len(deals_result.data)} | Acoes carregadas: {len(actions_df)}"
)

metric_cols = [c for c in df_geral.columns if c != "visao"]
geral_row = df_geral.iloc[0].to_dict() if not df_geral.empty else {}

cards_principais = [
    ("Leads recebidos", "leads_recebidos"),
    ("Leads remanejados", "leads_remanejados"),
    ("Acoes totais", "acoes_total"),
    ("Analises enviadas", "analises_enviadas"),
    ("Aprovacoes", "aprovacoes"),
    ("Reprovados", "reprovados"),
]

cols = st.columns(6)
for idx, (label, key) in enumerate(cards_principais):
    cols[idx].metric(label, to_int(geral_row.get(key, 0)))

st.markdown("---")

acao_cols = [
    c
    for c in metric_cols
    if c
    not in {
        "leads_recebidos",
        "leads_remanejados",
        "acoes_total",
        "analises_enviadas",
        "aprovacoes",
        "reprovados",
    }
]

if acao_cols:
    st.subheader("Acoes registradas pelo CRM")
    cols = st.columns(min(6, max(1, len(acao_cols))))
    for i, col in enumerate(acao_cols):
        cols[i % len(cols)].metric(col.replace("_", " ").title(), to_int(geral_row.get(col, 0)))

st.markdown("---")

visao = st.radio("Visao", ["Geral", "Por equipe", "Por corretor", "Diagnostico"], horizontal=True)

if visao == "Geral":
    st.subheader("Resumo geral")
    st.dataframe(df_geral, use_container_width=True, hide_index=True)

elif visao == "Por equipe":
    st.subheader("Performance por equipe")
    if df_equipe.empty:
        st.info("Sem equipes identificadas no retorno da API.")
    else:
        st.dataframe(df_equipe, use_container_width=True, hide_index=True)

elif visao == "Por corretor":
    st.subheader("Performance por corretor")
    if df_corretor.empty:
        st.info("Sem corretores identificados no retorno da API.")
    else:
        equipe_sel = st.selectbox("Filtrar equipe", ["Todas"] + sorted(df_corretor["equipe"].dropna().unique().tolist()))
        df_view = df_corretor.copy()
        if equipe_sel != "Todas":
            df_view = df_view[df_view["equipe"] == equipe_sel]
        st.dataframe(df_view, use_container_width=True, hide_index=True)

else:
    st.subheader("Diagnostico da integracao")
    st.write("Use esta aba na primeira conexao para confirmar quais endpoints e campos o PipeRun esta entregando.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Endpoint de leads/cards**")
        st.write(
            {
                "endpoint": deals_result.endpoint,
                "ok": deals_result.ok,
                "linhas": len(deals_result.data),
                "status_code": deals_result.status_code,
            }
        )
        st.markdown("**Colunas de leads/cards**")
        st.dataframe(pd.DataFrame({"coluna": list(deals_result.data.columns)}), use_container_width=True, hide_index=True)

        st.markdown("**Tabelas auxiliares**")
        st.write(
            {
                "usuarios": {
                    "endpoint": users_result.endpoint,
                    "ok": users_result.ok,
                    "linhas": len(users_result.data),
                    "erro": users_result.error,
                },
                "etapas": {
                    "endpoint": stages_result.endpoint,
                    "ok": stages_result.ok,
                    "linhas": len(stages_result.data),
                    "erro": stages_result.error,
                },
                "tipos_atividade": {
                    "endpoint": activity_types_result.endpoint,
                    "ok": activity_types_result.ok,
                    "linhas": len(activity_types_result.data),
                    "erro": activity_types_result.error,
                },
                "mapa_corretor_equipe_planilha": {
                    "ok": bool(corretor_equipe_map),
                    "linhas": len(corretor_equipe_map),
                },
            }
        )

    with c2:
        st.markdown("**Endpoints de acoes**")
        st.dataframe(action_status, use_container_width=True, hide_index=True)
        st.markdown("**Colunas de acoes**")
        st.dataframe(pd.DataFrame({"coluna": list(actions_df.columns)}), use_container_width=True, hide_index=True)

    with st.expander("Amostra de usuarios"):
        st.dataframe(users_result.data.head(20), use_container_width=True)

    with st.expander("Amostra de etapas"):
        st.dataframe(stages_result.data.head(30), use_container_width=True)

    with st.expander("Amostra de tipos de atividade"):
        st.dataframe(activity_types_result.data.head(30), use_container_width=True)

    with st.expander("Amostra de leads/cards"):
        st.dataframe(deals_result.data.head(20), use_container_width=True)

    with st.expander("Amostra de acoes"):
        st.dataframe(actions_df.head(20), use_container_width=True)
