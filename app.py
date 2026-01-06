import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import re

# ======================
# CONFIG
# ======================
st.set_page_config(page_title="Sistema de Cashback", layout="wide")

DATA_DIR = "data"
CLIENTES_FILE = f"{DATA_DIR}/clientes.csv"
HISTORICO_FILE = f"{DATA_DIR}/historico.csv"
BACKUP_FILE = f"{DATA_DIR}/backup.csv"

os.makedirs(DATA_DIR, exist_ok=True)

# ======================
# FUNÇÃO CPF
# ======================
def validar_cpf(cpf):
    cpf = re.sub(r"\D", "", cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        digito = ((soma * 10) % 11) % 10
        if digito != int(cpf[i]):
            return False

    return True

# ======================
# LOAD / SAVE
# ======================
def load_csv(path, columns):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=columns)

def save_csv(df, path):
    df.to_csv(path, index=False)

clientes = load_csv(CLIENTES_FILE, ["cliente", "cpf", "saldo"])
historico = load_csv(
    HISTORICO_FILE,
    ["data", "cliente", "cpf", "tipo", "valor", "motivo", "vendedor"]
)

# ======================
# EXPIRAÇÃO AUTOMÁTICA
# ======================
hoje = datetime.now().date()

if not historico.empty:
    historico["data"] = pd.to_datetime(historico["data"])
    vencidos = historico[
        (historico["tipo"] == "GANHO") &
        (historico["data"].dt.date < hoje - timedelta(days=90))
    ]

    for _, row in vencidos.iterrows():
        clientes.loc[clientes["cpf"] == row["cpf"], "saldo"] -= row["valor"]
        historico = historico.append({
            "data": datetime.now(),
            "cliente": row["cliente"],
            "cpf": row["cpf"],
            "tipo": "EXPIRADO",
            "valor": row["valor"],
            "motivo": "Expiração automática",
            "vendedor": "-"
        }, ignore_index=True)

# ======================
# SIDEBAR
# ======================
menu = st.sidebar.selectbox(
    "Menu",
    ["Clientes", "Venda / Cashback", "Usar Cashback", "Estorno", "Relatórios"]
)

# ======================
# CLIENTES
# ======================
if menu == "Clientes":
    st.header("👤 Cadastro de Clientes")

    nome = st.text_input("Nome do cliente")
    cpf = st.text_input("CPF (somente números ou com pontos)")

    if st.button("Cadastrar"):
        cpf_limpo = re.sub(r"\D", "", cpf)

        if not nome or not cpf:
            st.error("Nome e CPF são obrigatórios")

        elif not validar_cpf(cpf):
            st.error("CPF inválido")

        elif cpf_limpo in clientes["cpf"].astype(str).values:
            st.error("CPF já cadastrado")

        else:
            clientes = clientes.append({
                "cliente": nome,
                "cpf": cpf_limpo,
                "saldo": 0.0
            }, ignore_index=True)

            save_csv(clientes, CLIENTES_FILE)
            st.success("Cliente cadastrado com sucesso")

    st.dataframe(clientes)

# ======================
# VENDA / GANHO
# ======================
if menu == "Venda / Cashback":
    st.header("💰 Registrar Venda")

    cliente_sel = st.selectbox("Cliente", clientes["cliente"])
    cliente = clientes[clientes["cliente"] == cliente_sel].iloc[0]

    valor = st.number_input("Valor do cashback", min_value=0.0)
    vendedor = st.text_input("Vendedor")
    modelo = st.selectbox("Modelo", ["Onix", "Tracker", "Spark EV", "Captiva EV"])

    if st.button("Gerar Cashback"):
        clientes.loc[clientes["cpf"] == cliente["cpf"], "saldo"] += valor

        historico = historico.append({
            "data": datetime.now(),
            "cliente": cliente["cliente"],
            "cpf": cliente["cpf"],
            "tipo": "GANHO",
            "valor": valor,
            "motivo": f"Venda {modelo}",
            "vendedor": vendedor
        }, ignore_index=True)

        save_csv(clientes, CLIENTES_FILE)
        save_csv(historico, HISTORICO_FILE)
        historico.to_csv(BACKUP_FILE, index=False)

        st.success("Cashback registrado")

# ======================
# USAR CASHBACK
# ======================
if menu == "Usar Cashback":
    st.header("🟢 Usar Cashback")

    cliente_sel = st.selectbox("Cliente", clientes["cliente"])
    cliente = clientes[clientes["cliente"] == cliente_sel].iloc[0]

    st.info(f"Saldo disponível: R$ {cliente['saldo']:.2f}")

    valor = st.number_input(
        "Valor a usar",
        min_value=0.0,
        max_value=float(cliente["saldo"])
    )
    motivo = st.text_input("Motivo do uso")

    if st.button("Usar Cashback"):
        if valor <= 0 or not motivo:
            st.error("Informe valor e motivo")

        else:
            clientes.loc[clientes["cpf"] == cliente["cpf"], "saldo"] -= valor

            historico = historico.append({
                "data": datetime.now(),
                "cliente": cliente["cliente"],
                "cpf": cliente["cpf"],
                "tipo": "USO",
                "valor": valor,
                "motivo": motivo,
                "vendedor": "-"
            }, ignore_index=True)

            save_csv(clientes, CLIENTES_FILE)
            save_csv(historico, HISTORICO_FILE)

            st.success("Cashback utilizado")

# ======================
# ESTORNO
# ======================
if menu == "Estorno":
    st.header("🔄 Estorno")

    cliente_sel = st.selectbox("Cliente", clientes["cliente"])
    cliente = clientes[clientes["cliente"] == cliente_sel].iloc[0]

    valor = st.number_input("Valor do estorno", min_value=0.0)
    motivo = st.text_input("Motivo do estorno")

    if st.button("Estornar"):
        clientes.loc[clientes["cpf"] == cliente["cpf"], "saldo"] += valor

        historico = historico.append({
            "data": datetime.now(),
            "cliente": cliente["cliente"],
            "cpf": cliente["cpf"],
            "tipo": "ESTORNO",
            "valor": valor,
            "motivo": motivo,
            "vendedor": "-"
        }, ignore_index=True)

        save_csv(clientes, CLIENTES_FILE)
        save_csv(historico, HISTORICO_FILE)

        st.success("Estorno realizado")

# ======================
# RELATÓRIOS
# ======================
if menu == "Relatórios":
    st.header("📊 Relatórios")

    st.subheader("Histórico completo")
    st.dataframe(historico)

    st.subheader("Ranking de vendedores")
    ranking = historico[historico["tipo"] == "GANHO"].groupby("vendedor")["valor"].sum()
    st.bar_chart(ranking)
