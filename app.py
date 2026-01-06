import streamlit as st
import pandas as pd
from datetime import date
import os
from io import BytesIO
import altair as alt

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

# =============================
# LOGIN
# =============================
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.perfil = None

if not st.session_state.logado:
    st.title("🔐 Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario == "carlos" and senha == "1234":
            st.session_state.logado = True
            st.session_state.perfil = "admin"
            st.rerun()
        elif usuario == "vendedor" and senha == "1234":
            st.session_state.logado = True
            st.session_state.perfil = "vendedor"
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# =============================
# ARQUIVO LOCAL
# =============================
ARQUIVO_DADOS = "backup-vendas-auto.csv"

# =============================
# CARREGAMENTO SEGURO DO CSV
# =============================
if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype={"CPF": str})
else:
    df = pd.DataFrame()

# Garante colunas obrigatórias
colunas_necessarias = [
    "Nome", "CPF", "Veiculo",
    "Valor_Venda", "Percentual_Cashback",
    "Valor_Cashback", "Data_Venda"
]

for col in colunas_necessarias:
    if col not in df.columns:
        df[col] = None

df["Valor_Venda"] = pd.to_numeric(df["Valor_Venda"], errors="coerce").fillna(0)
df["Valor_Cashback"] = pd.to_numeric(df["Valor_Cashback"], errors="coerce").fillna(0)
df["Percentual_Cashback"] = pd.to_numeric(df["Percentual_Cashback"], errors="coerce").fillna(0)
df["Data_Venda"] = pd.to_datetime(df["Data_Venda"], errors="coerce")

# =============================
# TÍTULO
# =============================
st.title("🚗 Sistema de Vendas - Auto Nunes")
st.markdown("---")

# =============================
# MENU
# =============================
menu = st.sidebar.radio(
    "📌 Menu",
    ["📊 Dashboard de Vendas", "➕ Nova Venda", "🔍 Buscar Cliente", "📄 Relatórios"]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard de Vendas":
    st.header("📊 Dashboard de Vendas")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", len(df))
    c2.metric("Valor Total Vendido", f"R$ {df['Valor_Venda'].sum():,.2f}")
    c3.metric("Cashback Concedido", f"R$ {df['Valor_Cashback'].sum():,.2f}")

    st.markdown("---")
    st.subheader("🚗 Quantidade de Carros Vendidos")

    if not df.empty:
        carros = df.groupby("Veiculo").size().reset_index(name="Qtd")

        grafico = alt.Chart(carros).mark_bar().encode(
            x=alt.X("Veiculo:N", title="Veículo"),
            y=alt.Y("Qtd:Q", title="Quantidade"),
            color=alt.Color("Veiculo:N", legend=None),
            tooltip=["Veiculo", "Qtd"]
        ).properties(height=400)

        st.altair_chart(grafico, use_container_width=True)
        st.dataframe(carros, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada.")

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    st.header("➕ Registrar Nova Venda")

    with st.form("form_venda"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Cliente *")
            cpf = st.text_input("CPF *")
            veiculo = st.selectbox(
                "Veículo *",
                [
                    "Onix", "Onix Plus", "Tracker", "Montana",
                    "Spark EV", "Captiva EV",
                    "Equinox", "Equinox EV"
                ]
            )
            data_venda = st.date_input("Data da Venda", value=date.today())

        with col2:
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, step=1000.0)
            percentual = st.selectbox("Percentual de Cashback", [0, 5, 10, 15, 20])

        valor_cashback = valor_venda * (percentual / 100)

        st.markdown("### 📋 Resumo")
        r1, r2, r3 = st.columns(3)
        r1.metric("Valor da Venda", f"R$ {valor_venda:,.2f}")
        r2.metric("Cashback", f"R$ {valor_cashback:,.2f}")
        r3.metric("Percentual", f"{percentual}%")

        if st.form_submit_button("Salvar Venda"):
            if nome and cpf and valor_venda > 0:
                nova = pd.DataFrame([{
                    "Nome": nome,
                    "CPF": cpf,
                    "Veiculo": veiculo,
                    "Valor_Venda": valor_venda,
                    "Percentual_Cashback": percentual,
                    "Valor_Cashback": valor_cashback,
                    "Data_Venda": data_venda
                }])

                df = pd.concat([df, nova], ignore_index=True)
                df.to_csv(ARQUIVO_DADOS, index=False)
                st.success("Venda registrada com sucesso!")
            else:
                st.error("Preencha todos os campos obrigatórios.")

# =============================
# BUSCAR CLIENTE
# =============================
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")
    busca = st.text_input("Buscar por Nome ou CPF")

    if busca:
        resultado = df[
            df["Nome"].str.contains(busca, case=False, na=False) |
            df["CPF"].str.contains(busca, case=False, na=False)
        ]
    else:
        resultado = df

    st.dataframe(resultado, use_container_width=True)

# =============================
# RELATÓRIOS (SÓ ADMIN)
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.perfil != "admin":
        st.warning("Acesso restrito ao administrador.")
    else:
        st.header("📄 Relatórios")
        st.dataframe(df, use_container_width=True)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)

        st.download_button(
            "⬇ Baixar Relatório Excel",
            buffer.getvalue(),
            file_name="relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Sistema desenvolvido por Carlos Jr - Supervisor BDC")
