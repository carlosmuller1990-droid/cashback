import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# ===============================
# CONFIGURAÇÃO
# ===============================
st.set_page_config(page_title="Sistema de Cashback", layout="wide")

ARQUIVO_DADOS = "cashback.csv"
ARQUIVO_BACKUP = "backup_cashback.csv"

USUARIOS = {
    "carlos": {"senha": "1234", "perfil": "admin"},
    "vendedor": {"senha": "1234", "perfil": "vendedor"}
}

COLUNAS = [
    "Cliente",
    "CPF",
    "Valor_Compra",
    "Cashback_Gerado",
    "Saldo_Cashback",
    "Data_Venda",
    "Data_Expiracao",
    "Usado",
    "Vendedor",
    "CPF_Vendedor"
]

# ===============================
# INICIALIZA ARQUIVO
# ===============================
if not os.path.exists(ARQUIVO_DADOS):
    df_vazio = pd.DataFrame(columns=COLUNAS)
    df_vazio.to_csv(ARQUIVO_DADOS, index=False)

# ===============================
# LOGIN
# ===============================
def login():
    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario in USUARIOS and senha == USUARIOS[usuario]["senha"]:
            st.session_state.usuario = usuario
            st.session_state.perfil = USUARIOS[usuario]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

if "usuario" not in st.session_state:
    login()
    st.stop()

# ===============================
# CARREGA DADOS (AGORA SEGURO)
# ===============================
df = pd.read_csv(ARQUIVO_DADOS, dtype={"CPF": str, "CPF_Vendedor": str})

if not df.empty:
    df["Data_Venda"] = pd.to_datetime(df["Data_Venda"])
    df["Data_Expiracao"] = pd.to_datetime(df["Data_Expiracao"])

# ===============================
# HEADER
# ===============================
st.sidebar.success(f"Logado como: {st.session_state.usuario}")

if st.sidebar.button("🚪 Sair"):
    st.session_state.clear()
    st.rerun()

# ===============================
# VISÃO VENDEDOR
# ===============================
if st.session_state.perfil == "vendedor":
    st.title("🧑‍💼 Lançar Cashback")

    with st.form("form_venda"):
        cliente = st.text_input("Nome do Cliente")
        cpf = st.text_input("CPF do Cliente")
        valor = st.number_input("Valor da Compra", min_value=0.0, step=0.01)
        vendedor = st.text_input("Nome do Vendedor", value=st.session_state.usuario)
        cpf_vendedor = st.text_input("CPF do Vendedor")

        enviar = st.form_submit_button("Registrar Venda")

    if enviar:
        cashback = valor * 0.05
        nova_linha = {
            "Cliente": cliente,
            "CPF": cpf,
            "Valor_Compra": valor,
            "Cashback_Gerado": cashback,
            "Saldo_Cashback": cashback,
            "Data_Venda": datetime.now(),
            "Data_Expiracao": datetime.now() + timedelta(days=90),
            "Usado": False,
            "Vendedor": vendedor,
            "CPF_Vendedor": cpf_vendedor
        }

        df = pd.concat([df, pd.DataFrame([nova_linha])])
        df.to_csv(ARQUIVO_DADOS, index=False)
        df.to_csv(ARQUIVO_BACKUP, index=False)

        st.success("✅ Venda registrada com sucesso!")

# ===============================
# VISÃO ADMIN (CARLOS)
# ===============================
if st.session_state.perfil == "admin":
    st.title("📊 Visão Gerencial")

    st.subheader("Base de Cashback")
    st.dataframe(df)

    st.subheader("📥 Exportar Relatório")
    st.download_button(
        "Baixar CSV",
        df.to_csv(index=False).encode("utf-8"),
        "relatorio_cashback.csv",
        "text/csv"
    )
