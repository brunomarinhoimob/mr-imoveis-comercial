# ==========================================
# AUTENTICAÇÃO DE USUÁRIOS – DASHBOARD MR
# ==========================================

def normalizar_nome(nome: str) -> str:
    return " ".join(nome.strip().upper().split())


def gerar_login(nome: str) -> str:
    partes = nome.lower().split()
    return f"{partes[0]}.{partes[-1]}"


def gerar_senha(nome: str) -> str:
    primeiro_nome = nome.split()[0].capitalize()
    return f"{primeiro_nome}123"


# ------------------------------------------
# USUÁRIOS FIXOS (ADMIN / GESTÃO)
# ------------------------------------------
USUARIOS = {
    "bruno.marinho": {
        "nome": "BRUNO MARINHO",
        "senha": "511712bm",
        "perfil": "admin"
    },
    "djacir.adm": {
        "nome": "DJACIR ADM",
        "senha": "Djacir123",
        "perfil": "admin"
    },
    "nicolas.adm": {
        "nome": "NICOLAS ADM",
        "senha": "Nicolas123",
        "perfil": "admin"
    },
    "leandro.rodrigues": {
        "nome": "LEANDRO RODRIGUES",
        "senha": "Leandro123",
        "perfil": "gestor"
    },
    "magda.rayanne": {
        "nome": "MAGDA RAYANNE",
        "senha": "Magda123",
        "perfil": "gestor"
    },
    "diego.pinheiro": {
        "nome": "DIEGO PINHEIRO",
        "senha": "Diego123",
        "perfil": "gestor"
    }
}

# ------------------------------------------
# LISTA DE CORRETORES (SEM REPETIÇÃO)
# ------------------------------------------
NOMES_CORRETORES = sorted(set([
    "ANA RITA",
    "DEIVIANE",
    "MAGNO",
    "MIKAELY LIMA",
    "MARIA DE FATIMA",
    "IVAN JUNIOR",
    "DIEGO PINHEIRO",
    "PATRICIA SALES",
    "PALOMA",
    "VIVIAN",
    "RAYANNE",
    "ANA LIRA",
    "DANIEL SOUZA",
    "MAGDA RAYANNE",
    "MARCIA MATOS",
    "FRANCISCO CELBER",
    "WELLIA CAMARA",
    "RICARDO NASCIMENTO",
    "CLARA BRAGA",
    "LEANDRO RODRIGUES",
    "HENRIQUE",
    "GUTEMBERG FILGUEIRAS",
    "GABRIEL BEZERRA",
    "TAINA VIANA",
    "JANICE ALCANTARA",
    "MIKAEL DOUGLAS",
    "REBEKA GONÇALVES",
    "ALICE SILVA",
    "SAMUEL SOUTO",
    "DJACIR SILVA",
    "ADRIAN FERREIRA",
    "FABIO SOUSA",
    "VANESSA",
    "LUANA BRAGA",
    "RYAN FERRARI",
    "EDUARDA ROCHA",
    "KATHARINA SANTANA",
    "VALDEMIR",
    "PEDRO GABRIEL",
    "ARNOLD LENAR",
    "MARIA EDUARDA",
    "VANESSA MARTINS",
    "ALINE",
    "ALEXANDRE RODRIGUES",
    "BRITO",
    "MARCELLO BARBOSA"
]))

# ------------------------------------------
# CRIA LOGINS AUTOMATICAMENTE
# ------------------------------------------
for nome in NOMES_CORRETORES:
    nome_norm = normalizar_nome(nome)
    login = gerar_login(nome_norm)

    if login not in USUARIOS:
        USUARIOS[login] = {
            "nome": nome_norm,
            "senha": gerar_senha(nome_norm),
            "perfil": "corretor"
        }
