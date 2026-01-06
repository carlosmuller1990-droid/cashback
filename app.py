import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import os

st.set_page_config(page_title="Sistema de Cashback", layout="wide")

ARQUIVO = "dados_cashback.csv"

COLUNAS = [
    "Data",
    "Vendedor",
    "Cliente",
    "CPF",
    "Carro",
    "Valor_Venda",
    "Cashback_Gerado",
    "Cashback_Usado",
    "Saldo_Cashback",
    "Tipo",
    "Motivo"
]

# =============================
# BASE DE DADOS
# =============================
def criar_base():
    if not os.path.exists(ARQUIVO):
        pd.DataFrame(columns=COLUNAS).to_csv(ARQUIVO, index=False)

def carregar():
    criar_base()
    df = pd.read_csv(ARQUIVO)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    return df.reindex(columns=COLUNAS)

def salvar(df):
    df.to_csv(ARQUIVO, index=False)

# =============================
# CPF
# =============================
def validar_cpf(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def calc_digito(cpf, peso):
        soma = sum(int(d) * p for d, p in zip(cpf, peso))
        resto = soma % 11
        return '0' if resto < 2 else str(11 - resto)

    d1 = calc_digito(cpf[:9], range(10, 1, -1))
    d2 = calc_digito(cpf[:9] + d1, range(11, 1, -1))
    return cpf[-2:] == d1 + d2

# =============================
# EXPIRAÇÃO
# =============================
def expirar_cashback(df):
    limite = datetime.now() - timedelta(days=30)
    mask = (df["Tipo"] == "GERADO") & (df["Data"] < limite)
    df.loc[mask, "Saldo_Cashback"] = 0
    return df

# =============================
# LOGIN
# =============================
if "usuario" not in st.session_state:
    st.session_state.usuario = None
    st.session_state.perfil = None

if st.session_state.usuario is None:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if u == "carlos" and s == "admin":
            st.session_state.usuario = "Carlos"
            st.session_state.perfil = "admin"
            st.rerun()
        elif u == "vendedor" and s == "123":
            st.session_state.usuario = "Vendedor"
            st.session_state.perfil = "vendedor"
            st.rerun()
        else:
            st.error("Login inválido")
    st.stop()

# =============================
# APP
# =============================
df = carregar()
df = expirar_cashback(df)
salvar(df)

st.sidebar.success(f"Logado como: {st.session_state.usuario}")
if st.sidebar.button("Sair"):
    st.session_state.usuario = None
    st.session_state.perfil = None
    st.rerun()

# =============================
# REGISTRAR VENDA
# =============================
st.header("🚗 Registrar Venda")

with st.form("venda"):
    vendedor = st.text_input("Vendedor", value=st.session_state.usuario)
    cliente = st.text_input("Cliente")
    cpf = st.text_input("CPF (obrigatório)")

    carro = st.selectbox(
        "Carro",
        [
            "Onix",
            "Onix Plus",
            "Tracker",
            "Montana",
            "Spark EV",
            "Captiva EV",
            "Equinox",
            "Equinox EV"
        ]
    )

    valor = st.number_input("Valor da Venda", min_value=0.0, step=100.0)
    cashback = st.number_input("Cashback Gerado", min_value=0.0, step=10.0)

    if st.form_submit_button("Salvar Venda"):
        if not validar_cpf(cpf):
            st.error("CPF inválido")
        else:
            novo = {
                "Data": datetime.now(),
                "Vendedor": vendedor,
                "Cliente": cliente,
                "CPF": cpf,
                "Carro": carro,
                "Valor_Venda": valor,
                "Cashback_Gerado": cashback,
                "Cashback_Usado": 0,
                "Saldo_Cashback": cashback,
                "Tipo": "GERADO",
                "Motivo": ""
            }
            df = pd.concat([df, pd.DataFrame([novo])])
            salvar(df)
            st.success("Venda registrada com sucesso")

# =============================
# USAR CASHBACK
# =============================
st.header("💳 Usar Cashback")

cpf_uso = st.text_input("CPF do Cliente")
cliente_df = df[df["CPF"] == cpf_uso]
saldo = cliente_df["Saldo_Cashback"].sum()

st.info(f"Saldo disponível: R$ {saldo:,.2f}")

valor_uso = st.number_input("Valor a usar", min_value=0.0, max_value=float(saldo))
motivo_uso = st.text_input("Motivo do uso")

if st.button("Usar Cashback"):
    if valor_uso > 0 and motivo_uso:
        uso = {
            "Data": datetime.now(),
            "Vendedor": st.session_state.usuario,
            "Cliente": cliente_df.iloc[0]["Cliente"] if not cliente_df.empty else "",
            "CPF": cpf_uso,
            "Carro": "",
            "Valor_Venda": 0,
            "Cashback_Gerado": 0,
            "Cashback_Usado": valor_uso,
            "Saldo_Cashback": saldo - valor_uso,
            "Tipo": "USO",
            "Motivo": motivo_uso
        }
        df = pd.concat([df, pd.DataFrame([uso])])
        salvar(df)
        st.success("Cashback utilizado")

# =============================
# INDICADORES
# =============================
st.header("📊 Indicadores")

c1, c2, c3 = st.columns(3)
c1.metric("Total de Vendas", len(df[df["Tipo"] == "GERADO"]))
c2.metric("Valor Vendido", f"R$ {df['Valor_Venda'].sum():,.2f}")
c3.metric("Cashback Usado", f"R$ {df['Cashback_Usado'].sum():,.2f}")

# =============================
# GRÁFICO
# =============================
st.header("📈 Vendas por Modelo")

graf_df = (
    df[df["Tipo"] == "GERADO"]
    .groupby("Carro", as_index=False)["Valor_Venda"]
    .sum()
)

chart = (
    alt.Chart(graf_df)
    .mark_bar()
    .encode(
        x=alt.X("Carro:N", sort="-y"),
        y="Valor_Venda:Q",
        color="Carro:N",
        tooltip=["Carro", "Valor_Venda"]
    )
    .properties(height=400)
)

st.altair_chart(chart, use_container_width=True)

# =============================
# RANKING
# =============================
st.header("🏆 Ranking de Vendedores")

ranking = (
    df[df["Tipo"] == "GERADO"]
    .groupby("Vendedor")["Valor_Venda"]
    .sum()
    .sort_values(ascending=False)
)

st.dataframe(ranking)

# =============================
# HISTÓRICO
# =============================
st.header("📜 Histórico Completo")
st.dataframe(df.sort_values("Data", ascending=False))
