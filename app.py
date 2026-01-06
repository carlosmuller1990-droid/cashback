import streamlit as st
import pandas as pd
import os
from datetime import datetime
import matplotlib.pyplot as plt

# =====================
# CONFIGURAÇÃO
# =====================
st.set_page_config(page_title="Sistema de Cashback", layout="centered")

DATA_DIR = "data"
VENDAS_FILE = f"{DATA_DIR}/vendas.csv"
USO_FILE = f"{DATA_DIR}/uso_cashback.csv"

os.makedirs(DATA_DIR, exist_ok=True)

# =====================
# FUNÇÕES
# =====================
def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in [9, 10]:
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        dig = (soma * 10 % 11) % 10
        if dig != int(cpf[i]):
            return False
    return True

def carregar_csv(arquivo, colunas):
    if os.path.exists(arquivo):
        return pd.read_csv(arquivo)
    return pd.DataFrame(columns=colunas)

# =====================
# LOGIN
# =====================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.usuario = ""

if not st.session_state.login:
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if (user == "carlos" and senha == "1234") or (user == "vendedor" and senha == "1234"):
            st.session_state.login = True
            st.session_state.usuario = user
            st.rerun()
        else:
            st.error("Login inválido")

    st.stop()

# =====================
# MENU
# =====================
st.sidebar.title("Menu")
opcao = st.sidebar.radio("Escolha", ["Cadastrar Venda", "Usar Cashback", "Relatórios"])

# =====================
# CARREGAR DADOS
# =====================
vendas = carregar_csv(VENDAS_FILE, [
    "Data", "Cliente", "CPF", "Modelo", "Valor_Venda", "Cashback"
])

uso = carregar_csv(USO_FILE, [
    "Data", "Cliente", "CPF", "Vendedor", "Motivo", "Valor_Usado"
])

# =====================
# CADASTRAR VENDA
# =====================
if opcao == "Cadastrar Venda":
    st.title("🚗 Nova Venda")

    cliente = st.text_input("Nome do Cliente")
    cpf = st.text_input("CPF do Cliente")
    modelo = st.selectbox(
        "Modelo",
        [
            "Onix", "Onix Plus", "Tracker", "Montana",
            "Spark EV", "Captiva EV", "Equinox", "Equinox EV"
        ]
    )
    valor = st.number_input("Valor da Venda", min_value=0.0, step=100.0)
    cashback = st.number_input("Cashback Gerado", min_value=0.0, step=10.0)

    if st.button("Salvar Venda"):
        if not validar_cpf(cpf):
            st.error("CPF inválido")
        else:
            nova = {
                "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "Cliente": cliente,
                "CPF": cpf,
                "Modelo": modelo,
                "Valor_Venda": valor,
                "Cashback": cashback
            }
            vendas = pd.concat([vendas, pd.DataFrame([nova])], ignore_index=True)
            vendas.to_csv(VENDAS_FILE, index=False)
            st.success("Venda registrada com sucesso")

# =====================
# USAR CASHBACK
# =====================
if opcao == "Usar Cashback":
    st.title("💰 Usar Cashback")

    cpf = st.text_input("CPF do Cliente")
    cliente = st.text_input("Nome do Cliente")
    vendedor = st.text_input("Nome do Vendedor")
    motivo = st.text_area("Motivo do Uso")
    valor_uso = st.number_input("Valor a Usar", min_value=0.0, step=10.0)

    if st.button("Usar Cashback"):
        if not validar_cpf(cpf):
            st.error("CPF inválido")
        else:
            total_cashback = vendas[vendas["CPF"] == cpf]["Cashback"].sum()
            total_usado = uso[uso["CPF"] == cpf]["Valor_Usado"].sum()
            saldo = total_cashback - total_usado

            if valor_uso > saldo:
                st.error("Saldo insuficiente")
            else:
                novo_uso = {
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "Cliente": cliente,
                    "CPF": cpf,
                    "Vendedor": vendedor,
                    "Motivo": motivo,
                    "Valor_Usado": valor_uso
                }
                uso = pd.concat([uso, pd.DataFrame([novo_uso])], ignore_index=True)
                uso.to_csv(USO_FILE, index=False)
                st.success("Cashback utilizado com sucesso")

# =====================
# RELATÓRIOS
# =====================
if opcao == "Relatórios":
    st.title("📊 Relatórios")

    if not vendas.empty:
        vendas["Valor_Venda"] = pd.to_numeric(vendas["Valor_Venda"], errors="coerce").fillna(0)

        st.metric("Total Vendido", f"R$ {vendas['Valor_Venda'].sum():,.2f}")
        st.metric("Cashback Gerado", f"R$ {vendas['Cashback'].sum():,.2f}")

        st.subheader("Vendas por Modelo")

        agrupado = vendas.groupby("Modelo")["Valor_Venda"].sum()

        fig, ax = plt.subplots()
        cores = plt.cm.tab20.colors
        ax.bar(agrupado.index, agrupado.values, color=cores[:len(agrupado)])
        plt.xticks(rotation=45)
        st.pyplot(fig)

    st.subheader("Histórico de Uso de Cashback")
    st.dataframe(uso)
