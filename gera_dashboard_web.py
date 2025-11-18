import pandas as pd
from pathlib import Path

ARQUIVO = "dados_imobiliaria.csv"

# Lê o CSV
df = pd.read_csv(ARQUIVO, sep=",", encoding="utf-8-sig")
df.columns = [c.strip().upper() for c in df.columns]

# Datas
df["DATA"] = pd.to_datetime(df["DATA"], dayfirst=True, errors="coerce")

# Situações
df["EM_ANALISE"]      = (df["SITUAÇÃO"] == "EM ANÁLISE").astype(int)
df["REANALISE"]       = (df["SITUAÇÃO"] == "REANÁLISE").astype(int)
df["APROVACAO"]       = (df["SITUAÇÃO"] == "APROVAÇÃO").astype(int)
df["APROVADO_BACEN"]  = (df["SITUAÇÃO"] == "APROVADO BACEN").astype(int)
df["REPROVACAO"]      = (df["SITUAÇÃO"] == "REPROVAÇÃO").astype(int)
df["VENDA_GERADA"]    = (df["SITUAÇÃO"] == "VENDA GERADA").astype(int)
df["VENDA_INFORMADA"] = (df["SITUAÇÃO"] == "VENDA INFORMADA").astype(int)

df["APROVACAO_TOTAL"] = df["APROVACAO"] + df["APROVADO_BACEN"]
df["VENDAS_TOTAL"]    = df["VENDA_GERADA"] + df["VENDA_INFORMADA"]

# ===== KPIs gerais =====
total_em_analise      = int(df["EM_ANALISE"].sum())
total_reanalise       = int(df["REANALISE"].sum())
total_aprovacoes      = int(df["APROVACAO_TOTAL"].sum())
total_reprovacoes     = int(df["REPROVACAO"].sum())
total_vendas          = int(df["VENDAS_TOTAL"].sum())
total_venda_gerada    = int(df["VENDA_GERADA"].sum())
total_venda_informada = int(df["VENDA_INFORMADA"].sum())

etapa1 = total_em_analise
etapa2 = total_reanalise
etapa3 = total_aprovacoes
etapa4 = total_vendas

taxa_aprov_sobre_etapa1 = (total_aprovacoes / etapa1 * 100) if etapa1 > 0 else 0
taxa_venda_sobre_etapa1 = (total_vendas / etapa1 * 100) if etapa1 > 0 else 0
taxa_venda_sobre_aprov  = (total_vendas / total_aprovacoes * 100) if total_aprovacoes > 0 else 0

# ===== Rankings =====
tabela_corretor = (
    df.groupby("CORRETOR")
    .agg(
        em_analise=("EM_ANALISE", "sum"),
        reanalise=("REANALISE", "sum"),
        aprovacoes=("APROVACAO_TOTAL", "sum"),
        vendas_total=("VENDAS_TOTAL", "sum")
    )
    .sort_values(by="vendas_total", ascending=False)
)

tabela_corretor["analises_total"] = (
    tabela_corretor["em_analise"] + tabela_corretor["reanalise"]
)

tabela_corretor_html = tabela_corretor.head(20).to_html(classes="tabela", border=0)

tabela_equipe = (
    df.groupby("EQUIPE")
    .agg(
        em_analise=("EM_ANALISE", "sum"),
        reanalise=("REANALISE", "sum"),
        vendas_total=("VENDAS_TOTAL", "sum")
    )
)
tabela_equipe["analises_total"] = (
    tabela_equipe["em_analise"] + tabela_equipe["reanalise"]
)
tabela_equipe = tabela_equipe[["analises_total", "vendas_total"]]
tabela_equipe_html = tabela_equipe.to_html(classes="tabela", border=0)

tabela_construtora = (
    df.groupby("CONSTRUTORA")
    .agg(vendas_total=("VENDAS_TOTAL", "sum"))
    .sort_values(by="vendas_total", ascending=False)
)
tabela_construtora_html = tabela_construtora.head(15).to_html(classes="tabela", border=0)

tabela_empreendimento = (
    df.groupby("EMPREENDIMENTO")
    .agg(vendas_total=("VENDAS_TOTAL", "sum"))
    .sort_values(by="vendas_total", ascending=False)
)
tabela_empreendimento_html = tabela_empreendimento.head(15).to_html(classes="tabela", border=0)

# ===== HTML =====
html = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Dashboard Imobiliária</title>
<style>
    body {{
        font-family: Arial, sans-serif;
        margin: 20px;
        background-color: #f5f7fb;
    }}
    h1, h2, h3 {{
        color: #0b2e4e;
    }}
    .kpis {{
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        margin-bottom: 25px;
    }}
    .card {{
        background: #ffffff;
        padding: 12px 16px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        min-width: 160px;
    }}
    .card .label {{
        font-size: 12px;
        color: #666;
    }}
    .card .value {{
        font-size: 20px;
        font-weight: bold;
        color: #0b2e4e;
    }}
    .card .sub {{
        font-size: 11px;
        color: #888;
    }}
    .section {{
        margin-top: 30px;
        margin-bottom: 10px;
    }}
    .tabela {{
        border-collapse: collapse;
        width: 100%;
        font-size: 12px;
        background: #ffffff;
    }}
    .tabela th, .tabela td {{
        border: 1px solid #ddd;
        padding: 6px 8px;
        text-align: left;
    }}
    .tabela th {{
        background-color: #0b2e4e;
        color: #fff;
    }}
    img {{
        max-width: 100%;
        height: auto;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        background: #fff;
    }}
    .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 20px;
        align-items: start;
    }}
</style>
</head>
<body>
    <h1>📊 Dashboard Imobiliária – Versão Web (HTML)</h1>
    <p>Arquivo base: <strong>{ARQUIVO}</strong></p>

    <div class="kpis">
        <div class="card">
            <div class="label">Em análise</div>
            <div class="value">{total_em_analise}</div>
        </div>
        <div class="card">
            <div class="label">Reanálise</div>
            <div class="value">{total_reanalise}</div>
        </div>
        <div class="card">
            <div class="label">Aprovações (total)</div>
            <div class="value">{total_aprovacoes}</div>
            <div class="sub">Aprovação: {df['APROVACAO'].sum()} | Bacen: {df['APROVADO_BACEN'].sum()}</div>
        </div>
        <div class="card">
            <div class="label">Reprovações</div>
            <div class="value">{total_reprovacoes}</div>
        </div>
        <div class="card">
            <div class="label">Vendas totais</div>
            <div class="value">{total_vendas}</div>
            <div class="sub">Gerada: {total_venda_gerada} | Informada: {total_venda_informada}</div>
        </div>
        <div class="card">
            <div class="label">Aprovações / Em análise</div>
            <div class="value">{taxa_aprov_sobre_etapa1:.1f}%</div>
        </div>
        <div class="card">
            <div class="label">Vendas / Em análise</div>
            <div class="value">{taxa_venda_sobre_etapa1:.1f}%</div>
        </div>
        <div class="card">
            <div class="label">Vendas / Aprovações</div>
            <div class="value">{taxa_venda_sobre_aprov:.1f}%</div>
        </div>
    </div>

    <div class="section">
        <h2>Funil de conversão</h2>
        <p>Em análise → Reanálise → Aprovações → Vendas</p>
        <img src="funil_conversao_4_etapas.png" alt="Funil de conversão">
    </div>

    <div class="section">
        <h2>Equipes – Análises x Vendas</h2>
        <div class="grid">
            <div>
                <h3>Gráfico</h3>
                <img src="equipes_analises_vendas.png" alt="Equipes - Análises x Vendas">
            </div>
            <div>
                <h3>Tabela</h3>
                {tabela_equipe_html}
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Top 20 Corretores por Vendas</h2>
        <div class="grid">
            <div>
                <h3>Gráfico (Top 10)</h3>
                <img src="top10_corretores_vendas.png" alt="Top 10 corretores por vendas">
            </div>
            <div>
                <h3>Tabela (Top 20)</h3>
                {tabela_corretor_html}
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Top Construtoras por Vendas</h2>
        {tabela_construtora_html}
    </div>

    <div class="section">
        <h2>Top Empreendimentos por Vendas</h2>
        {tabela_empreendimento_html}
    </div>

    <hr>
    <p style="font-size: 11px; color: #777;">
        Página gerada automaticamente em Python a partir de <strong>{ARQUIVO}</strong>.
    </p>
</body>
</html>
"""

# Salva o HTML
saida = Path("dashboard_web.html")
saida.write_text(html, encoding="utf-8")
print(f"Dashboard web gerado em: {saida.resolve()}")
