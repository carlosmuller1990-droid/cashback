import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from io import BytesIO
import altair as alt

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

ARQUIVO = "backup-vendas-auto.csv"

# =============================
# LOGIN
# =============================
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None

if not st.session_state.logado:
    st.title("🔐 Login")

    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if u == "carlos" and s == "1234":
            st.session_state.logado = True
            st.session_state.perfil = "admin"
            st.rerun()
        elif u == "vendedor" and s == "1234":
            st.session_state.logado = True
            st.session_state.perfil = "vendedor"
            st.rerun()
        else:
            st.error("Login inválido")

    st.stop()

# =============================
# DADOS
# =============================
if os.path.exists(ARQUIVO):
    df = pd.read_csv(ARQUIVO, dtype=str)
else:
    df = pd.DataFrame(columns=[
        "Nome", "CPF", "Veiculo",
        "Valor_Venda", "Percentual_Cashback",
        "Valor_Cashback", "Saldo_Cashback",
        "Data_Venda", "Data_Expiracao",
        "Tipo", "Vendedor", "CPF_Vendedor", "Motivo"
    ])

for col in ["Valor_Venda", "Valor_Cashback", "Saldo_Cashback"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["Data_Venda"] = pd.to_datetime(df["Data_Venda"], errors="coerce")
df["Data_Expiracao"] = pd.to_datetime(df["Data_Expiracao"], errors="coerce")

# =============================
# TÍTULO
# =============================
st.title("🚗 Sistema de Vendas - Auto Nunes")
st.markdown("---")

menu = st.sidebar.radio(
    "📌 Menu",
    ["📊 Dashboard", "➕ Nova Venda", "🔍 Buscar Cliente", "📄 Relatórios"]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard":
    c1, c2, c3 = st.columns(3)
    c1.metric("Vendas", len(df[df["Tipo"] == "VENDA"]))
    c2.metric("Total Vendido", f"R$ {df['Valor_Venda'].sum():,.2f}")
    c3.metric("Cashback Ativo", f"R$ {df['Saldo_Cashback'].sum():,.2f}")

    vendas = df[df["Tipo"] == "VENDA"]
    if not vendas.empty:
        carros = vendas.groupby("Veiculo").size().reset_index(name="Qtd")
        graf = alt.Chart(carros).mark_bar().encode(
            x="Veiculo",
            y="Qtd",
            color="Veiculo"
        )
        st.altair_chart(graf, use_container_width=True)

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    with st.form("venda"):
        nome = st.text_input("Nome")
        cpf = st.text_input("CPF")
        veiculo = st.selectbox(
            "Veículo",
            ["Onix", "Onix Plus", "Tracker", "Montana",
             "Spark EV", "Captiva EV", "Equinox", "Equinox EV"]
        )
        valor = st.number_input("Valor da Venda", min_value=0.0)
        perc = st.selectbox("Cashback %", [0, 5, 10, 15, 20])
        data_venda = st.date_input("Data", date.today())

        if st.form_submit_button("Salvar"):
            cashback = valor * (perc / 100)
            nova = {
                "Nome": nome,
                "CPF": cpf,
                "Veiculo": veiculo,
                "Valor_Venda": valor,
                "Percentual_Cashback": perc,
                "Valor_Cashback": cashback,
                "Saldo_Cashback": cashback,
                "Data_Venda": data_venda,
                "Data_Expiracao": data_venda + timedelta(days=90),
                "Tipo": "VENDA",
                "Vendedor": "",
                "CPF_Vendedor": "",
                "Motivo": ""
            }
            df = pd.concat([df, pd.DataFrame([nova])])
            df.to_csv(ARQUIVO, index=False)
            st.success("Venda registrada")

# =============================
# BUSCAR CLIENTE + USO CASHBACK
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Nome ou CPF")

    clientes = df[
        (df["Tipo"] == "VENDA") &
        (df["Saldo_Cashback"] > 0) &
        (df["Data_Expiracao"] >= pd.Timestamp.today())
    ]

    if busca:
        clientes = clientes[
            clientes["Nome"].str.contains(busca, case=False) |
            clientes["CPF"].str.contains(busca)
        ]

    for i, row in clientes.iterrows():
        with st.expander(f"{row['Nome']} | CPF {row['CPF']} | Saldo R$ {row['Saldo_Cashback']:.2f}"):
            with st.form(f"use_{i}"):
                vendedor = st.text_input("Nome do Vendedor")
                cpf_vend = st.text_input("CPF do Vendedor")
                motivo = st.text_input("Motivo do Uso")
                valor_uso = st.number_input(
                    "Valor a Usar",
                    min_value=0.0,
                    max_value=row["Saldo_Cashback"]
                )

                if st.form_submit_button("Usar Cashback"):
                    df.at[i, "Saldo_Cashback"] -= valor_uso

                    uso = row.copy()
                    uso["Tipo"] = "USO"
                    uso["Valor_Cashback"] = valor_uso
                    uso["Saldo_Cashback"] = 0
                    uso["Vendedor"] = vendedor
                    uso["CPF_Vendedor"] = cpf_vend
                    uso["Motivo"] = motivo

                    df = pd.concat([df, pd.DataFrame([uso])])
                    df.to_csv(ARQUIVO, index=False)
                    st.success("Cashback utilizado")
                    st.rerun()

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.perfil != "admin":
        st.warning("Acesso restrito")
    else:
        st.dataframe(df, use_container_width=True)
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as w:
            df.to_excel(w, index=False)
        st.download_button("Baixar Excel", buffer.getvalue(), "relatorio.xlsx")

st.markdown("---")
st.caption("Sistema Auto Nunes") 
