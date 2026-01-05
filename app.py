import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

ARQUIVO_DADOS = "backup_vendas.xlsx"

# =============================
# INICIALIZAÇÃO DO ARQUIVO
# =============================
if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_excel(ARQUIVO_DADOS)
else:
    df = pd.DataFrame(columns=[
        "Cliente",
        "Modelo",
        "Valor_Venda",
        "Percentual_Cashback",
        "Valor_Cashback",
        "Data_Venda"
    ])
    df.to_excel(ARQUIVO_DADOS, index=False)

# =============================
# TÍTULO
# =============================
st.title("🚗 Sistema de Vendas - Auto Nunes")
st.markdown("---")

# =============================
# SIDEBAR
# =============================
st.sidebar.title("📌 Menu")

menu = st.sidebar.radio(
    "Selecione:",
    [
        "📊 Dashboard",
        "➕ Nova Venda",
        "🔍 Buscar Cliente",
        "📄 Relatórios"
    ]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard":
    st.header("📊 Dashboard de Vendas")

    total_vendas = len(df)
    valor_total = df["Valor_Venda"].sum()
    cashback_total = df["Valor_Cashback"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", total_vendas)
    c2.metric("Valor Total Vendido", f"R$ {valor_total:,.2f}")
    c3.metric("Cashback Concedido", f"R$ {cashback_total:,.2f}")

    st.markdown("---")
    st.subheader("🚗 Quantidade de Carros Vendidos por Modelo")

    if not df.empty:
        carros = df.groupby("Modelo").size().reset_index(name="Quantidade")
        st.bar_chart(carros.set_index("Modelo"))
        st.dataframe(carros, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada ainda.")

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    st.header("➕ Registrar Nova Venda")

    with st.form("form_venda"):
        col1, col2 = st.columns(2)

        with col1:
            cliente = st.text_input("Nome do Cliente *")
            modelo = st.selectbox(
                "Modelo do Carro *",
                ["Onix", "Onix Plus", "Tracker", "Spin", "Montana", "S10", "Blazer"]
            )
            data_venda = st.date_input("Data da Venda", value=date.today())

        with col2:
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, step=1000.0)
            percentual = st.selectbox("Percentual de Cashback", [0, 5, 10, 15, 20])

        valor_cashback = valor_venda * (percentual / 100)

        st.markdown("### 📋 Resumo")
        c1, c2, c3 = st.columns(3)
        c1.metric("Valor Venda", f"R$ {valor_venda:,.2f}")
        c2.metric("Cashback", f"R$ {valor_cashback:,.2f}")
        c3.metric("Percentual", f"{percentual}%")

        salvar = st.form_submit_button("Salvar Venda")

        if salvar:
            if cliente and valor_venda > 0:
                nova_linha = {
                    "Cliente": cliente,
                    "Modelo": modelo,
                    "Valor_Venda": valor_venda,
                    "Percentual_Cashback": percentual,
                    "Valor_Cashback": valor_cashback,
                    "Data_Venda": data_venda
                }
                df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
                df.to_excel(ARQUIVO_DADOS, index=False)
                st.success("Venda registrada com sucesso!")
            else:
                st.error("Preencha todos os campos obrigatórios.")

# =============================
# BUSCAR CLIENTE
# =============================
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")

    busca = st.text_input("Digite o nome do cliente")

    if busca:
        resultado = df[df["Cliente"].str.contains(busca, case=False, na=False)]
    else:
        resultado = df

    st.dataframe(resultado, use_container_width=True)

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    st.header("📄 Relatórios")

    st.subheader("📊 Quantidade de Carros Vendidos")

    relatorio_carros = df.groupby("Modelo").size().reset_index(name="Quantidade")
    st.dataframe(relatorio_carros, use_container_width=True)

    caminho_excel = "relatorio_vendas.xlsx"
    df.to_excel(caminho_excel, index=False)

    with open(caminho_excel, "rb") as f:
        st.download_button(
            "⬇ Baixar relatório completo (Excel)",
            f,
            file_name="relatorio_vendas.xlsx"
        )

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Auto Nunes © Sistema de Cashback")
