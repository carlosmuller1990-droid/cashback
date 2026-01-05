import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from io import BytesIO

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config("Sistema de Vendas - Auto Nunes", "🚗", layout="wide")

ARQUIVO_DADOS = "backup-vendas-auto.csv"
ARQUIVO_LOG = "log-uso-cashback.csv"
LIMITE_USO = 0.30  # 30%

# =============================
# LOGIN
# =============================
def login():
    st.title("🔒 Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario in st.secrets["usuarios"] and senha == st.secrets["usuarios"][usuario]:
            st.session_state["usuario"] = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

if "usuario" not in st.session_state:
    login()
    st.stop()

# =============================
# DADOS
# =============================
if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype={"CPF": str, "CPF_Vendedor": str},
                     parse_dates=["Data_Venda", "Data_Expiracao"])
else:
    df = pd.DataFrame(columns=[
        "Nome","CPF","Veiculo","Valor_Venda",
        "Percentual_Cashback","Valor_Cashback",
        "Cashback_Usado","Status_Cashback",
        "Nome_Vendedor","CPF_Vendedor",
        "Usuario_Sistema",
        "Data_Venda","Data_Expiracao"
    ])
    df.to_csv(ARQUIVO_DADOS, index=False)

if not os.path.exists(ARQUIVO_LOG):
    pd.DataFrame(columns=[
        "CPF_Cliente","Valor_Usado","Data_Uso",
        "Usuario","Nome_Vendedor","CPF_Vendedor"
    ]).to_csv(ARQUIVO_LOG, index=False)

# =============================
# ATUALIZA EXPIRAÇÃO
# =============================
hoje = pd.to_datetime(date.today())
df.loc[
    (df["Status_Cashback"] == "Ativo") & (df["Data_Expiracao"] < hoje),
    "Status_Cashback"
] = "Expirado"
df.to_csv(ARQUIVO_DADOS, index=False)

# =============================
# MENU
# =============================
menu = st.sidebar.radio("Menu", [
    "📊 Dashboard",
    "➕ Nova Venda",
    "🔍 Buscar Cliente",
    "📄 Relatórios"
])

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard":
    st.header("📊 Dashboard")

    st.metric("Total Vendas", len(df))
    st.metric("Cashback Ativo",
              f"R$ {df[df['Status_Cashback']=='Ativo']['Valor_Cashback'].sum():,.2f}")

    # ALERTA 7 DIAS
    alerta = df[
        (df["Status_Cashback"] == "Ativo") &
        ((df["Data_Expiracao"] - hoje).dt.days <= 7)
    ]
    if not alerta.empty:
        st.warning("🔔 Cashback a vencer em até 7 dias")
        st.dataframe(alerta[["Nome","CPF","Valor_Cashback","Data_Expiracao"]])

    # SALDO CONSOLIDADO
    st.subheader("📊 Saldo por Cliente")
    saldo = df[df["Status_Cashback"]=="Ativo"] \
        .groupby(["Nome","CPF"])["Valor_Cashback"] \
        .sum().reset_index()
    st.dataframe(saldo)

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    st.header("➕ Nova Venda")

    with st.form("venda"):
        nome = st.text_input("Nome Cliente")
        cpf = st.text_input("CPF Cliente")
        veiculo = st.selectbox("Veículo",
            ["Onix","Onix Plus","Tracker","Spin","Montana","S10","Blazer"])
        valor_venda = st.number_input("Valor Venda", min_value=0.0, step=1000.0)
        percentual = st.selectbox("Cashback (%)",[0,5,10,15,20])
        data_venda = st.date_input("Data", value=date.today())

        cashback_disp = df[
            (df["CPF"]==cpf)&
            (df["Status_Cashback"]=="Ativo")&
            (df["Data_Expiracao"]>=pd.to_datetime(data_venda))
        ]["Valor_Cashback"].sum()

        usar = False
        nome_vend = cpf_vend = ""

        if cashback_disp > 0:
            st.info(f"Cashback disponível: R$ {cashback_disp:,.2f}")
            usar = st.checkbox("Usar cashback")

            if usar:
                nome_vend = st.text_input("Nome Vendedor *")
                cpf_vend = st.text_input("CPF Vendedor *")

        limite = valor_venda * LIMITE_USO
        cashback_usado = min(cashback_disp, limite) if usar else 0
        valor_final = valor_venda - cashback_usado
        cashback_gerado = valor_final * (percentual / 100)

        st.markdown("### Resumo")
        st.write(f"Valor final: R$ {valor_final:,.2f}")
        st.write(f"Cashback gerado: R$ {cashback_gerado:,.2f}")

        salvar = st.form_submit_button("Salvar")

        if salvar:
            if usar and (not nome_vend or not cpf_vend):
                st.error("Informe vendedor para usar cashback")
            else:
                if usar:
                    df.loc[
                        (df["CPF"]==cpf)&(df["Status_Cashback"]=="Ativo"),
                        ["Valor_Cashback","Status_Cashback"]
                    ] = [0,"Utilizado"]

                    log = pd.read_csv(ARQUIVO_LOG)
                    log = pd.concat([log, pd.DataFrame([{
                        "CPF_Cliente": cpf,
                        "Valor_Usado": cashback_usado,
                        "Data_Uso": date.today(),
                        "Usuario": st.session_state["usuario"],
                        "Nome_Vendedor": nome_vend,
                        "CPF_Vendedor": cpf_vend
                    }])])
                    log.to_csv(ARQUIVO_LOG, index=False)

                df = pd.concat([df, pd.DataFrame([{
                    "Nome": nome,
                    "CPF": cpf,
                    "Veiculo": veiculo,
                    "Valor_Venda": valor_final,
                    "Percentual_Cashback": percentual,
                    "Valor_Cashback": cashback_gerado,
                    "Cashback_Usado": cashback_usado,
                    "Status_Cashback": "Ativo",
                    "Nome_Vendedor": nome_vend,
                    "CPF_Vendedor": cpf_vend,
                    "Usuario_Sistema": st.session_state["usuario"],
                    "Data_Venda": data_venda,
                    "Data_Expiracao": data_venda + timedelta(days=90)
                }])])

                df.to_csv(ARQUIVO_DADOS, index=False)
                st.success("Venda registrada!")

# =============================
# BUSCAR CLIENTE
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Nome ou CPF")
    st.dataframe(df[df["Nome"].str.contains(busca,case=False,na=False)|
                     df["CPF"].str.contains(busca,case=False,na=False)])

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    st.subheader("Vendas")
    st.dataframe(df)

    st.subheader("Histórico de Uso de Cashback")
    st.dataframe(pd.read_csv(ARQUIVO_LOG))

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name="Vendas")
        pd.read_csv(ARQUIVO_LOG).to_excel(w, index=False, sheet_name="Uso Cashback")

    st.download_button("Baixar Excel",
        buffer.getvalue(),
        "relatorio_completo.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption(f"Usuário logado: {st.session_state['usuario']}")
