import pandas as pd
import matplotlib.pyplot as plt

ARQUIVO = "dados_imobiliaria.csv"

# Lê o CSV (separado por vírgula, com acentos em UTF-8)
df = pd.read_csv(ARQUIVO, sep=",", encoding="utf-8-sig")

# Padroniza os nomes das colunas
df.columns = [c.strip().upper() for c in df.columns]

# Confere se as colunas principais existem
colunas_obrigatorias = ["DATA", "CORRETOR", "EQUIPE", "CONSTRUTORA", "EMPREENDIMENTO", "SITUAÇÃO"]
for col in colunas_obrigatorias:
    if col not in df.columns:
        raise ValueError(f"Coluna obrigatória não encontrada no arquivo: {col}")

# ==== CRIA COLUNAS PARA CADA SITUAÇÃO ====
df["EM_ANALISE"]      = (df["SITUAÇÃO"] == "EM ANÁLISE").astype(int)
df["REANALISE"]       = (df["SITUAÇÃO"] == "REANÁLISE").astype(int)
df["APROVACAO"]       = (df["SITUAÇÃO"] == "APROVAÇÃO").astype(int)
df["APROVADO_BACEN"]  = (df["SITUAÇÃO"] == "APROVADO BACEN").astype(int)
df["REPROVACAO"]      = (df["SITUAÇÃO"] == "REPROVAÇÃO").astype(int)
df["VENDA_GERADA"]    = (df["SITUAÇÃO"] == "VENDA GERADA").astype(int)
df["VENDA_INFORMADA"] = (df["SITUAÇÃO"] == "VENDA INFORMADA").astype(int)

# Agregados úteis
df["APROVACAO_TOTAL"] = df["APROVACAO"] + df["APROVADO_BACEN"]
df["VENDAS_TOTAL"]    = df["VENDA_GERADA"] + df["VENDA_INFORMADA"]

# ==== KPI GERAL ====
total_registros       = len(df)
total_em_analise      = df["EM_ANALISE"].sum()
total_reanalise       = df["REANALISE"].sum()
total_aprovacoes      = df["APROVACAO_TOTAL"].sum()
total_reprovacoes     = df["REPROVACAO"].sum()
total_vendas          = df["VENDAS_TOTAL"].sum()
total_venda_gerada    = df["VENDA_GERADA"].sum()
total_venda_informada = df["VENDA_INFORMADA"].sum()

etapa1 = total_em_analise
etapa2 = total_reanalise
etapa3 = total_aprovacoes
etapa4 = total_vendas

taxa_aprov_sobre_etapa1 = (total_aprovacoes / etapa1 * 100) if etapa1 > 0 else 0
taxa_venda_sobre_etapa1 = (total_vendas / etapa1 * 100) if etapa1 > 0 else 0
taxa_venda_sobre_aprov  = (total_vendas / total_aprovacoes * 100) if total_aprovacoes > 0 else 0

print("=== DASHBOARD GERAL IMOBILIÁRIA ===")
print(f"Registros no período: {total_registros}")
print(f"EM ANÁLISE: {total_em_analise}")
print(f"REANÁLISE: {total_reanalise}")
print(f"APROVAÇÕES (APROVAÇÃO + APROVADO BACEN): {total_aprovacoes}")
print(f"  - APROVAÇÃO: {df['APROVACAO'].sum()}")
print(f"  - APROVADO BACEN: {df['APROVADO_BACEN'].sum()}")
print(f"REPROVAÇÕES: {total_reprovacoes}")
print(f"VENDAS TOTAIS: {total_vendas}")
print(f"  - VENDA GERADA: {total_venda_gerada}")
print(f"  - VENDA INFORMADA: {total_venda_informada}")
print()
print(f"Taxa aprovações sobre EM ANÁLISE: {taxa_aprov_sobre_etapa1:.2f}%")
print(f"Taxa vendas sobre EM ANÁLISE: {taxa_venda_sobre_etapa1:.2f}%")
print(f"Taxa vendas sobre APROVAÇÕES: {taxa_venda_sobre_aprov:.2f}%")
print()

# ==== RANKING POR CORRETOR ====
tabela_corretor = df.groupby("CORRETOR").agg(
    em_analise      = ("EM_ANALISE", "sum"),
    reanalise       = ("REANALISE", "sum"),
    aprovacoes      = ("APROVACAO_TOTAL", "sum"),
    reprovacoes     = ("REPROVACAO", "sum"),
    venda_gerada    = ("VENDA_GERADA", "sum"),
    venda_informada = ("VENDA_INFORMADA", "sum"),
    vendas_total    = ("VENDAS_TOTAL", "sum")
)

tabela_corretor["analises_total"] = tabela_corretor["em_analise"] + tabela_corretor["reanalise"]

print("=== TOP CORRETORES POR VENDAS (TOTAL) ===")
print(tabela_corretor.sort_values(by="vendas_total", ascending=False).head(10))
print()

print("=== TOP CORRETORES POR ANÁLISES (EM ANÁLISE + REANÁLISE) ===")
print(tabela_corretor.sort_values(by="analises_total", ascending=False).head(10))
print()

# ==== RANKING POR EQUIPE ====
tabela_equipe = df.groupby("EQUIPE").agg(
    em_analise      = ("EM_ANALISE", "sum"),
    reanalise       = ("REANALISE", "sum"),
    aprovacoes      = ("APROVACAO_TOTAL", "sum"),
    reprovacoes     = ("REPROVACAO", "sum"),
    venda_gerada    = ("VENDA_GERADA", "sum"),
    venda_informada = ("VENDA_INFORMADA", "sum"),
    vendas_total    = ("VENDAS_TOTAL", "sum")
)
tabela_equipe["analises_total"] = tabela_equipe["em_analise"] + tabela_equipe["reanalise"]

print("=== PERFORMANCE POR EQUIPE ===")
print(tabela_equipe)
print()

# ==== CONSTRUTORA / EMPREENDIMENTO ====
tabela_construtora = df.groupby("CONSTRUTORA").agg(
    em_analise=("EM_ANALISE", "sum"),
    reanalise=("REANALISE", "sum"),
    aprovacoes=("APROVACAO_TOTAL", "sum"),
    vendas=("VENDAS_TOTAL", "sum")
).sort_values(by="vendas", ascending=False)

tabela_empreendimento = df.groupby("EMPREENDIMENTO").agg(
    em_analise=("EM_ANALISE", "sum"),
    reanalise=("REANALISE", "sum"),
    aprovacoes=("APROVACAO_TOTAL", "sum"),
    vendas=("VENDAS_TOTAL", "sum")
).sort_values(by="vendas", ascending=False)

print("=== TOP CONSTRUTORAS POR VENDAS ===")
print(tabela_construtora.head(10))
print()

print("=== TOP EMPREENDIMENTOS POR VENDAS ===")
print(tabela_empreendimento.head(10))
print()

# ==== GRÁFICOS ====

# 1) Funil de conversão (4 etapas)
etapas = ["Em análise", "Reanálise", "Aprovações", "Vendas"]
valores = [etapa1, etapa2, etapa3, etapa4]

plt.figure()
plt.plot(etapas, valores, marker="o")
plt.title("Funil de Conversão - Imobiliária")
plt.xlabel("Etapa")
plt.ylabel("Quantidade")
plt.tight_layout()
plt.savefig("funil_conversao_4_etapas.png", dpi=300)

# 2) Top 10 corretores por vendas
plt.figure()
tabela_corretor.sort_values(by="vendas_total", ascending=False).head(10)["vendas_total"].plot(kind="bar")
plt.title("Top 10 Corretores - Vendas Totais")
plt.xlabel("Corretor")
plt.ylabel("Qtd Vendas")
plt.tight_layout()
plt.savefig("top10_corretores_vendas.png", dpi=300)

# 3) Equipes - Análises x Vendas
plt.figure()
tabela_equipe[["analises_total", "vendas_total"]].plot(kind="bar")
plt.title("Equipes - Análises (EM + RE) x Vendas")
plt.xlabel("Equipe")
plt.ylabel("Quantidade")
plt.tight_layout()
plt.savefig("equipes_analises_vendas.png", dpi=300)

plt.close("all")

print("Gráficos gerados na pasta:")
print("- funil_conversao_4_etapas.png")
print("- top10_corretores_vendas.png")
print("- equipes_analises_vendas.png")
