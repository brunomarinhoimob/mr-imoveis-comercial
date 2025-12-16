import streamlit as st
import re

# ---------------------------------------------------------
# BLOQUEIO SEM LOGIN
# ---------------------------------------------------------
if "logado" not in st.session_state or not st.session_state.logado:
    st.warning("🔒 Faça login para continuar.")
    st.stop()

from auth_users import USUARIOS

st.set_page_config(
    page_title="Alterar Senha",
    page_icon="🔐",
    layout="centered"
)

st.markdown("## 🔐 Alterar Senha")
st.caption("Altere sua senha de acesso ao dashboard.")

usuario = st.session_state.get("usuario")
perfil = st.session_state.get("perfil")

st.markdown(f"👤 **Usuário:** `{usuario}`")

st.markdown("---")

senha_atual = st.text_input("Senha atual", type="password")
nova_senha = st.text_input("Nova senha", type="password")
confirmar_senha = st.text_input("Confirmar nova senha", type="password")

def salvar_nova_senha(usuario_login, nova_senha):
    """
    Atualiza a senha diretamente no arquivo auth_users.py
    """
    import auth_users
    import inspect

    caminho = inspect.getfile(auth_users)

    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()

    padrao = rf'"{usuario_login}"\s*:\s*{{[^}}]*"senha"\s*:\s*"[^"]*"'
    novo = rf'"{usuario_login}": {{\n        "nome": "{USUARIOS[usuario_login]["nome"]}",\n        "senha": "{nova_senha}",\n        "perfil": "{USUARIOS[usuario_login]["perfil"]}"'

    conteudo_novo = re.sub(padrao, novo, conteudo)

    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo_novo)

if st.button("Salvar nova senha", use_container_width=True):

    if usuario not in USUARIOS:
        st.error("Usuário inválido.")
        st.stop()

    if senha_atual != USUARIOS[usuario]["senha"]:
        st.error("Senha atual incorreta.")
        st.stop()

    if nova_senha != confirmar_senha:
        st.error("Nova senha e confirmação não conferem.")
        st.stop()

    if nova_senha == senha_atual:
        st.error("A nova senha não pode ser igual à atual.")
        st.stop()

    if len(nova_senha) < 6:
        st.error("A nova senha deve ter pelo menos 6 caracteres.")
        st.stop()

    salvar_nova_senha(usuario, nova_senha)

    st.success("✅ Senha alterada com sucesso!")
    st.info("Na próxima vez que entrar, use a nova senha.")
