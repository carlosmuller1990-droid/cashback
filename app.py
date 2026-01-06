import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

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
# LOAD / SAVE
# ======================
def load_csv(path, columns):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame(columns=columns)

def save_csv(df, path):
    df.to_csv(path, index=False)

clientes = load_csv(CLIENTES_FILE, ["cliente", "saldo"])
historico = load_csv(
    HISTORICO_FILE,
    ["data", "cliente", "tipo", "valor", "motivo", "vendedor"]
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
        clientes.loc[clientes["cliente"] == row["cliente"], "saldo"] -= row["valor"]
        historico = historico.append({
            "data": datetime.now(),
            "cliente": row["cliente"],
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
    st.header("👤 Clientes")

    nome = st.text_input("Nome do cliente")
    if st.button("Cadastrar"):
        if nome and nome not in clientes["cliente"].values:
            clientes = clientes.append({"cliente": nome, "saldo": 0.0}, ignore_index=True)
            save_csv(clientes, CLIENTES_FILE)
            st.success("Cliente cadastrado")

    st.dataframe(clientes)

# ======================
# VENDA / GANHO CASHBACK
# ======================
if menu == "Venda / Cashback":
    st.header("💰 Registrar Venda")

    cliente = st.selectbox("Cliente", clientes["cliente"])
    valor = st.number_input("Valor do cashback", min_value=0.0)
    vendedor = st.text_input("Vendedor")
    modelo = st.selectbox(
        "Modelo",
        ["Onix", "Tracker", "Spark EV", "Captiva EV"]
    )

    if st.button("Gerar Cashback"):
        clientes.loc[clientes["cliente"] == cliente, "saldo"] += valor
        historico = historico.append({
            "data": datetime.now(),
            "cliente": cliente,
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

    cliente = st.selectbox("Cliente", clientes["cliente"])
    saldo = clientes.loc[clientes["cliente"] == cliente, "saldo"].values[0]
    st.info(f"Saldo disponível: R$ {saldo:.2f}")

    valor = st.number_input("Valor a usar", min_value=0.0, max_value=saldo)
    motivo = st.text_input("Motivo do uso")

    if st.button("Usar Cashback"):
        if valor > 0 and motivo:
            clientes.loc[clientes["cliente"] == cliente, "saldo"] -= valor
            historico = historico.append({
                "data": datetime.now(),
                "cliente": cliente,
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

    cliente = st.selectbox("Cliente", clientes["cliente"])
    valor = st.number_input("Valor do estorno", min_value=0.0)
    motivo = st.text_input("Motivo do estorno")

    if st.button("Estornar"):
        clientes.loc[clientes["cliente"] == cliente, "saldo"] += valor
        historico = historico.append({
            "data": datetime.now(),
            "cliente": cliente,
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
