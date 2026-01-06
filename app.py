import streamlit as st
import pandas as pd
from datetime import date, timedelta
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

ARQUIVO_DADOS = "backup-vendas-auto.csv"

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
            st.error("Login inválido")

    st.stop()

# =============================
# CARREGAMENTO / COMPATIBILIDADE CSV
# =============================
if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype=str)
else:
    df = pd.DataFrame()

# Garante colunas (compatível com CSV antigo)
colunas_padrao = {
    "Nome": "",
    "CPF": "",
    "Veiculo": "",
    "Valor_Venda": 0.0,
    "Percentual_Cashback": 0,
    "Valor_Cashback": 0.0,
    "Saldo_Cashback": 0.0,
    "Data_Venda": pd.NaT,
    "Data_Expiracao": pd.NaT,
    "Tipo": "VENDA",  # VENDA / USO
    "Vendedor": "",
    "CPF_Vendedor": "",
    "Motivo": ""
}

for col, default in colunas_padrao.items():
    if col not in df.columns:
        df[col] = default

# Conversões seguras
for col in ["Valor_Venda", "Valor_Cashback", "Saldo_Cashback"]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df["Data_Venda"] = pd.to_datetime(df["Data_Venda"], errors="coerce")
df["Data_Expiracao"] = pd.to_datetime(df["Data_Expiracao"], errors="coerce")

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
    [
        "📊 Dashboard de Vendas",
        "➕ Nova Venda",
        "🔍 Buscar Cliente",
        "📄 Relatórios"
    ]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard de Vendas":
    vendas = df[df["Tipo"] == "VENDA"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", len(vendas))
    c2.metric("Valor Total Vendido", f"R$ {vendas['Valor_Venda'].sum():,.2f}")
    c3.metric("Cashback Ativo", f"R$ {vendas['Saldo_Cashback'].sum():,.2f}")

    st.markdown("---")
    st.subheader("🚗 Quantidade de Carros Vendidos")

    if not vendas.empty:
        carros = vendas.groupby("Veiculo").size().reset_index(name="Qtd")

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

        salvar = st.form_submit_button("Salvar Venda")

        if salvar:
            if nome and cpf and valor_venda > 0:
                nova = {
                    "Nome": nome,
                    "CPF": cpf,
                    "Veiculo": veiculo,
                    "Valor_Venda": valor_venda,
                    "Percentual_Cashback": percentual,
                    "Valor_Cashback": valor_cashback,
                    "Saldo_Cashback": valor_cashback,
                    "Data_Venda": data_venda,
                    "Data_Expiracao": data_venda + timedelta(days=90),
                    "Tipo": "VENDA",
                    "Vendedor": "",
                    "CPF_Vendedor": "",
                    "Motivo": ""
                }

                df = pd.concat([df, pd.DataFrame([nova])], ignore_index=True)
                df.to_csv(ARQUIVO_DADOS, index=False)
                st.success("Venda registrada com sucesso!")
            else:
                st.error("Preencha todos os campos obrigatórios.")

# =============================
# BUSCAR CLIENTE + USAR CASHBACK
# =============================
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")

    busca = st.text_input("Nome ou CPF")

    clientes = df[
        (df["Tipo"] == "VENDA") &
        (df["Saldo_Cashback"] > 0) &
        (df["Data_Expiracao"] >= pd.Timestamp.today())
    ]

    if busca:
        clientes = clientes[
            clientes["Nome"].str.contains(busca, case=False, na=False) |
            clientes["CPF"].str.contains(busca, na=False)
        ]

    if clientes.empty:
        st.info("Nenhum cashback disponível.")
    else:
        for idx, row in clientes.iterrows():
            with st.expander(
                f"{row['Nome']} | CPF {row['CPF']} | Saldo R$ {row['Saldo_Cashback']:.2f}"
            ):
                with st.form(f"uso_{idx}"):
                    vendedor = st.text_input("Nome do Vendedor")
                    cpf_vendedor = st.text_input("CPF do Vendedor")
                    motivo = st.text_input("Motivo do Uso")
                    valor_uso = st.number_input(
                        "Valor a Usar",
                        min_value=0.0,
                        max_value=row["Saldo_Cashback"]
                    )

                    if st.form_submit_button("Usar Cashback"):
                        if not vendedor or not cpf_vendedor or not motivo:
                            st.error("Preencha os dados do vendedor e o motivo.")
                        else:
                            df.at[idx, "Saldo_Cashback"] -= valor_uso

                            uso = row.copy()
                            uso["Tipo"] = "USO"
                            uso["Valor_Cashback"] = valor_uso
                            uso["Saldo_Cashback"] = 0
                            uso["Vendedor"] = vendedor
                            uso["CPF_Vendedor"] = cpf_vendedor
                            uso["Motivo"] = motivo

                            df = pd.concat([df, pd.DataFrame([uso])], ignore_index=True)
                            df.to_csv(ARQUIVO_DADOS, index=False)
                            st.success("Cashback utilizado com sucesso!")
                            st.rerun()

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.perfil != "admin":
        st.warning("Acesso restrito ao administrador.")
    else:
        st.dataframe(df, use_container_width=True)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Relatório")

        st.download_button(
            "⬇ Baixar Relatório em Excel",
            buffer.getvalue(),
            file_name="relatorio_vendas_cashback.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Sistema desenvolvido por Carlos Jr - Supervisor BDC")
