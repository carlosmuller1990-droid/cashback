import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime, timedelta
import os

# ================== CONFIG ==================
st.set_page_config(page_title="Sistema de Cashback", layout="wide")

ARQ_DADOS = "cashback.csv"
ARQ_HIST = "historico.csv"

LIMITE_POR_COMPRA = 500.0

USUARIOS = {
    "carlos": {
        "senha": hashlib.sha256("1234".encode()).hexdigest(),
        "perfil": "admin"
    },
    "vendedor": {
        "senha": hashlib.sha256("1234".encode()).hexdigest(),
        "perfil": "vendedor"
    }
}

# ================== FUNÇÕES ==================
def salvar_csv(df, arq):
    df.to_csv(arq, index=False)

def hash_senha(s):
    return hashlib.sha256(s.encode()).hexdigest()

def carregar_dados():
    if os.path.exists(ARQ_DADOS):
        return pd.read_csv(ARQ_DADOS, parse_dates=["Data_Venda", "Data_Expiracao"])
    return pd.DataFrame(columns=[
        "Cliente", "CPF", "Veiculo", "Valor_Venda",
        "Cashback", "Saldo_Cashback",
        "Data_Venda", "Data_Expiracao"
    ])

def carregar_historico():
    if os.path.exists(ARQ_HIST):
        return pd.read_csv(ARQ_HIST)
    return pd.DataFrame(columns=[
        "Cliente", "CPF", "Tipo", "Valor",
        "Vendedor", "CPF_Vendedor", "Motivo", "Data"
    ])

def registrar_historico(df, **dados):
    df.loc[len(df)] = dados
    salvar_csv(df, ARQ_HIST)

# ================== LOGIN ==================
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

# ================== CARGA ==================
df = carregar_dados()
hist = carregar_historico()

# ================== EXPIRAÇÃO AUTOMÁTICA ==================
hoje = datetime.now()
df.loc[df["Data_Expiracao"] < hoje, "Saldo_Cashback"] = 0
salvar_csv(df, ARQ_DADOS)

# ================== DASHBOARD ==================
st.title("💳 Sistema de Cashback")

# ALERTA 7 DIAS
alerta = df[
    (df["Saldo_Cashback"] > 0) &
    (df["Data_Expiracao"] <= hoje + timedelta(days=7))
]
if not alerta.empty:
    st.warning("🔔 Existem cashbacks a vencer nos próximos 7 dias")

# SALDO CONSOLIDADO
saldo_cliente = df.groupby("Cliente")["Saldo_Cashback"].sum().reset_index()

# RANKING VENDEDORES
ranking = hist[hist["Tipo"] == "USO"]
ranking = ranking.groupby("Vendedor")["Valor"].sum().reset_index()

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Saldo por Cliente")
    st.bar_chart(saldo_cliente.set_index("Cliente"))

with col2:
    st.subheader("🏆 Ranking de Vendedores")
    if not ranking.empty:
        st.bar_chart(ranking.set_index("Vendedor"))

# ================== PESQUISA CLIENTE ==================
st.subheader("🔎 Pesquisar Cliente")

busca = st.text_input("Nome ou CPF do Cliente")

resultado = df[
    df["Cliente"].str.contains(busca, case=False, na=False) |
    df["CPF"].astype(str).str.contains(busca, na=False)
]

st.dataframe(resultado)

# ================== USAR CASHBACK ==================
if not resultado.empty:
    st.subheader("💸 Usar Cashback")

    valor = st.number_input("Valor a usar", min_value=0.0)

    vendedor = st.text_input("Nome do Vendedor")
    cpf_vendedor = st.text_input("CPF do Vendedor")

    if st.button("Confirmar Uso"):
        if valor > LIMITE_POR_COMPRA:
            st.error("Valor excede o limite por compra")
        else:
            idx = resultado.index[0]
            if valor > df.loc[idx, "Saldo_Cashback"]:
                st.error("Saldo insuficiente")
            else:
                df.loc[idx, "Saldo_Cashback"] -= valor
                salvar_csv(df, ARQ_DADOS)

                registrar_historico(
                    hist,
                    Cliente=df.loc[idx, "Cliente"],
                    CPF=df.loc[idx, "CPF"],
                    Tipo="USO",
                    Valor=valor,
                    Vendedor=vendedor,
                    CPF_Vendedor=cpf_vendedor,
                    Motivo="",
                    Data=datetime.now()
                )
                st.success("Cashback utilizado com sucesso")
                st.rerun()

# ================== ESTORNO ==================
st.subheader("🔄 Estorno de Cashback")

motivo = st.text_input("Motivo do estorno")
valor_estorno = st.number_input("Valor do estorno", min_value=0.0)

if st.button("Estornar"):
    if not resultado.empty:
        idx = resultado.index[0]
        df.loc[idx, "Saldo_Cashback"] += valor_estorno
        salvar_csv(df, ARQ_DADOS)

        registrar_historico(
            hist,
            Cliente=df.loc[idx, "Cliente"],
            CPF=df.loc[idx, "CPF"],
            Tipo="ESTORNO",
            Valor=valor_estorno,
            Vendedor=st.session_state.usuario,
            CPF_Vendedor="",
            Motivo=motivo,
            Data=datetime.now()
        )
        st.success("Estorno realizado")
        st.rerun()

# ================== HISTÓRICO ==================
st.subheader("🧾 Histórico Completo")
st.dataframe(hist)

# ================== RELATÓRIO ==================
if st.session_state.perfil == "admin":
    st.subheader("⬇️ Exportar Relatórios")
    st.download_button(
        "Baixar Histórico CSV",
        hist.to_csv(index=False),
        "historico_cashback.csv",
        "text/csv"
    )
