import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import hashlib

# ======================
# CONFIGURAÇÃO
# ======================
st.set_page_config(page_title="Cashback", layout="wide")

ARQUIVO = "cashback.csv"
BACKUP = "backup_cashback.csv"
LIMITE_USO = 200.00  # limite máximo de uso por compra
ALERTA_DIAS = 7

# ======================
# USUÁRIOS (hash)
# ======================
def hash_senha(s):
    return hashlib.sha256(s.encode()).hexdigest()

USUARIOS = {
    "carlos": {"senha": hash_senha("1234"), "perfil": "admin"},
    "vendedor": {"senha": hash_senha("1234"), "perfil": "vendedor"}
}

COLUNAS = [
    "Cliente", "CPF", "Valor_Compra", "Cashback_Gerado",
    "Saldo_Cashback", "Data_Venda", "Data_Expiracao",
    "Usado", "Valor_Usado",
    "Vendedor", "CPF_Vendedor", "Data_Uso"
]

# ======================
# INICIALIZA CSV
# ======================
if not os.path.exists(ARQUIVO):
    pd.DataFrame(columns=COLUNAS).to_csv(ARQUIVO, index=False)

df = pd.read_csv(ARQUIVO, dtype={"CPF": str, "CPF_Vendedor": str})
if not df.empty:
    df["Data_Venda"] = pd.to_datetime(df["Data_Venda"])
    df["Data_Expiracao"] = pd.to_datetime(df["Data_Expiracao"])
    df["Data_Uso"] = pd.to_datetime(df["Data_Uso"], errors="coerce")

# ======================
# LOGIN
# ======================
if "usuario" not in st.session_state:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if u in USUARIOS and hash_senha(s) == USUARIOS[u]["senha"]:
            st.session_state.usuario = u
            st.session_state.perfil = USUARIOS[u]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# ======================
# HEADER
# ======================
st.sidebar.success(f"Logado como: {st.session_state.usuario}")

if st.sidebar.button("🚪 Sair"):
    st.session_state.clear()
    st.rerun()

# ======================
# ALERTA CASHBACK A VENCER
# ======================
alertas = df[
    (~df["Usado"]) &
    (df["Data_Expiracao"] <= datetime.now() + timedelta(days=ALERTA_DIAS))
]

if not alertas.empty:
    st.warning(f"🔔 {len(alertas)} cashback(s) vencendo em até 7 dias")

# ======================
# SALDO CONSOLIDADO
# ======================
st.subheader("📊 Saldo por Cliente")
saldo_cliente = (
    df[~df["Usado"]]
    .groupby(["Cliente", "CPF"])["Saldo_Cashback"]
    .sum()
    .reset_index()
)
st.dataframe(saldo_cliente)

# ======================
# REGISTRAR VENDA
# ======================
st.subheader("🧾 Registrar Venda")

with st.form("venda"):
    cliente = st.text_input("Cliente")
    cpf = st.text_input("CPF Cliente")
    valor = st.number_input("Valor da Compra", min_value=0.0)
    vendedor = st.text_input("Vendedor", value=st.session_state.usuario)
    cpf_vendedor = st.text_input("CPF do Vendedor")

    salvar = st.form_submit_button("Salvar")

if salvar:
    cashback = valor * 0.05
    nova = {
        "Cliente": cliente,
        "CPF": cpf,
        "Valor_Compra": valor,
        "Cashback_Gerado": cashback,
        "Saldo_Cashback": cashback,
        "Data_Venda": datetime.now(),
        "Data_Expiracao": datetime.now() + timedelta(days=90),
        "Usado": False,
        "Valor_Usado": 0.0,
        "Vendedor": vendedor,
        "CPF_Vendedor": cpf_vendedor,
        "Data_Uso": None
    }

    df = pd.concat([df, pd.DataFrame([nova])])
    df.to_csv(ARQUIVO, index=False)
    df.to_csv(BACKUP, index=False)
    st.success("✅ Venda registrada")

# ======================
# USAR CASHBACK
# ======================
st.subheader("💳 Usar Cashback")

cpf_uso = st.text_input("CPF do Cliente para Uso")

if cpf_uso:
    saldo = df[(df["CPF"] == cpf_uso) & (~df["Usado"])]["Saldo_Cashback"].sum()
    st.info(f"Saldo disponível: R$ {saldo:.2f}")

    valor_uso = st.number_input(
        "Valor a usar",
        min_value=0.0,
        max_value=min(saldo, LIMITE_USO)
    )

    if st.button("Usar Cashback"):
        if valor_uso > 0:
            restante = valor_uso
            for i, row in df[(df["CPF"] == cpf_uso) & (~df["Usado"])].iterrows():
                if restante <= 0:
                    break
                uso = min(row["Saldo_Cashback"], restante)
                df.at[i, "Saldo_Cashback"] -= uso
                df.at[i, "Valor_Usado"] += uso
                df.at[i, "Data_Uso"] = datetime.now()
                if df.at[i, "Saldo_Cashback"] == 0:
                    df.at[i, "Usado"] = True
                restante -= uso

            df.to_csv(ARQUIVO, index=False)
            df.to_csv(BACKUP, index=False)
            st.success("✅ Cashback utilizado")

# ======================
# HISTÓRICO
# ======================
st.subheader("📜 Histórico de Uso")
st.dataframe(df[df["Valor_Usado"] > 0])

# ======================
# EXPORTAÇÃO (SÓ CARLOS)
# ======================
if st.session_state.perfil == "admin":
    st.subheader("📥 Exportar Relatório")
    st.download_button(
        "Baixar CSV",
        df.to_csv(index=False).encode("utf-8"),
        "relatorio_cashback.csv",
        "text/csv"
    )
