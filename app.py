import streamlit as st
import pandas as pd
import hashlib
import os
from datetime import date, timedelta
from io import BytesIO
import matplotlib.pyplot as plt

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

# =============================
# LOGIN CRIPTOGRAFADO
# =============================
USUARIOS = {
    "carlos": hashlib.sha256("1234".encode()).hexdigest(),
    "vendedor": hashlib.sha256("1234".encode()).hexdigest()
}

def autenticar(u, s):
    return USUARIOS.get(u) == hashlib.sha256(s.encode()).hexdigest()

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = ""

if not st.session_state.logado:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if autenticar(u, s):
            st.session_state.logado = True
            st.session_state.usuario = u
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# =============================
# ARQUIVOS
# =============================
ARQ_VENDAS = "backup-vendas-auto.csv"
ARQ_HIST = "historico-cashback.csv"

COL_VENDAS = [
    "Nome","CPF","Veiculo","Valor_Venda",
    "Percentual_Cashback","Valor_Cashback",
    "Saldo_Cashback","Data_Venda","Data_Expiracao"
]

COL_HIST = [
    "Nome_Cliente","CPF_Cliente",
    "Valor","Tipo","Motivo",
    "Data","Vendedor","CPF_Vendedor"
]

if os.path.exists(ARQ_VENDAS):
    df = pd.read_csv(ARQ_VENDAS, parse_dates=["Data_Venda","Data_Expiracao"])
else:
    df = pd.DataFrame(columns=COL_VENDAS)
    df.to_csv(ARQ_VENDAS, index=False)

if os.path.exists(ARQ_HIST):
    hist = pd.read_csv(ARQ_HIST, parse_dates=["Data"])
else:
    hist = pd.DataFrame(columns=COL_HIST)
    hist.to_csv(ARQ_HIST, index=False)

# =============================
# EXPIRAÇÃO AUTOMÁTICA DIÁRIA
# =============================
hoje = pd.Timestamp.today().normalize()
expirados = df[
    (df["Saldo_Cashback"] > 0) &
    (df["Data_Expiracao"] < hoje)
]

if not expirados.empty:
    df.loc[expirados.index, "Saldo_Cashback"] = 0
    df.to_csv(ARQ_VENDAS, index=False)

# =============================
# ALERTA 7 DIAS
# =============================
alerta = df[
    (df["Saldo_Cashback"] > 0) &
    (df["Data_Expiracao"] <= hoje + pd.Timedelta(days=7))
]

if not alerta.empty:
    st.warning("🔔 Existem cashbacks a vencer nos próximos 7 dias")

# =============================
# MENU
# =============================
st.sidebar.title("📌 Menu")
menu = st.sidebar.radio(
    "Selecione",
    ["📊 Dashboard","➕ Nova Venda","🔍 Buscar Cliente","📄 Relatórios"]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard":
    st.header("📊 Dashboard")

    c1,c2,c3 = st.columns(3)
    c1.metric("Vendas", len(df))
    c2.metric("Valor Vendido", f"R$ {df['Valor_Venda'].sum():,.2f}")
    c3.metric("Cashback Ativo", f"R$ {df['Saldo_Cashback'].sum():,.2f}")

    st.subheader("📊 Saldo por Cliente")
    saldo = df.groupby(["Nome","CPF"])["Saldo_Cashback"].sum().reset_index()
    st.dataframe(saldo, use_container_width=True)

    st.subheader("🚗 Vendas por Veículo")
    if not df.empty:
        graf = df.groupby("Veiculo")["Valor_Venda"].sum()
        fig, ax = plt.subplots()
        ax.bar(graf.index, graf.values)
        ax.set_ylabel("Valor (R$)")
        ax.set_xlabel("Veículo")
        st.pyplot(fig)

    st.subheader("📊 Ranking de Vendedores")
    ranking = hist[hist["Tipo"]=="USO"].groupby("Vendedor")["Valor"].sum().reset_index()
    ranking = ranking.sort_values("Valor", ascending=False)
    st.dataframe(ranking, use_container_width=True)

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    st.header("➕ Nova Venda")

    with st.form("venda"):
        nome = st.text_input("Nome *")
        cpf = st.text_input("CPF *")
        veiculo = st.selectbox(
            "Veículo",
            ["Onix","Onix Plus","Tracker","Spin","Montana","S10","Blazer"]
        )
        valor = st.number_input("Valor da Venda", min_value=0.0, step=1000.0)
        perc = st.selectbox("Cashback (%)",[0,5,10,15,20])
        if st.form_submit_button("Salvar"):
            cashback = valor * (perc/100)
            nova = {
                "Nome":nome,"CPF":cpf,"Veiculo":veiculo,
                "Valor_Venda":valor,
                "Percentual_Cashback":perc,
                "Valor_Cashback":cashback,
                "Saldo_Cashback":cashback,
                "Data_Venda":date.today(),
                "Data_Expiracao":date.today()+timedelta(days=90)
            }
            df = pd.concat([df,pd.DataFrame([nova])])
            df.to_csv(ARQ_VENDAS,index=False)
            st.success("Venda registrada")

# =============================
# BUSCAR CLIENTE
# =============================
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")
    busca = st.text_input("Nome ou CPF")

    res = df[
        df["Nome"].str.contains(busca,case=False,na=False) |
        df["CPF"].str.contains(busca,case=False,na=False)
    ]

    st.dataframe(res, use_container_width=True)

    if not res.empty:
        saldo = res["Saldo_Cashback"].sum()
        st.info(f"Saldo disponível: R$ {saldo:,.2f}")

        valor = st.number_input("Valor a usar", min_value=0.0)
        vendedor = st.text_input("Vendedor")
        cpf_v = st.text_input("CPF Vendedor")

        if st.button("Usar Cashback"):
            if valor <= saldo and vendedor and cpf_v:
                restante = valor
                for idx in res.index:
                    if restante <= 0: break
                    disp = df.loc[idx,"Saldo_Cashback"]
                    uso = min(disp, restante)
                    df.loc[idx,"Saldo_Cashback"] -= uso
                    restante -= uso

                hist = pd.concat([hist,pd.DataFrame([{
                    "Nome_Cliente":res.iloc[0]["Nome"],
                    "CPF_Cliente":res.iloc[0]["CPF"],
                    "Valor":valor,
                    "Tipo":"USO",
                    "Motivo":"",
                    "Data":date.today(),
                    "Vendedor":vendedor,
                    "CPF_Vendedor":cpf_v
                }])])

                df.to_csv(ARQ_VENDAS,index=False)
                hist.to_csv(ARQ_HIST,index=False)
                st.success("Cashback utilizado")
            else:
                st.error("Erro nos dados")

        st.subheader("🔄 Estorno de Cashback")
        valor_est = st.number_input("Valor do Estorno", min_value=0.0)
        motivo = st.text_input("Motivo do Estorno")

        if st.button("Estornar"):
            if valor_est > 0 and motivo:
                df.loc[res.index[0],"Saldo_Cashback"] += valor_est

                hist = pd.concat([hist,pd.DataFrame([{
                    "Nome_Cliente":res.iloc[0]["Nome"],
                    "CPF_Cliente":res.iloc[0]["CPF"],
                    "Valor":valor_est,
                    "Tipo":"ESTORNO",
                    "Motivo":motivo,
                    "Data":date.today(),
                    "Vendedor":st.session_state.usuario,
                    "CPF_Vendedor":""
                }])])

                df.to_csv(ARQ_VENDAS,index=False)
                hist.to_csv(ARQ_HIST,index=False)
                st.success("Estorno realizado")

        st.subheader("🧾 Histórico")
        st.dataframe(hist[hist["CPF_Cliente"]==res.iloc[0]["CPF"]], use_container_width=True)

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.usuario != "carlos":
        st.warning("Acesso restrito")
    else:
        st.dataframe(df, use_container_width=True)
        buf = BytesIO()
        df.to_excel(buf,index=False)
        st.download_button("⬇ Vendas", buf.getvalue(), "vendas.xlsx")

        st.dataframe(hist, use_container_width=True)
        buf2 = BytesIO()
        hist.to_excel(buf2,index=False)
        st.download_button("⬇ Histórico", buf2.getvalue(), "historico.xlsx")

st.caption("Sistema Auto Nunes | Carlos Jr")
