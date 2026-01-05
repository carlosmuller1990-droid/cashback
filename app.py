import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from io import BytesIO

# =============================
# LOGIN FIXO NO APP
# =============================
USUARIOS = {
    "carlos": {"senha": "1234", "perfil": "gerencial"},
    "vendedor": {"senha": "1234", "perfil": "operacional"}
}

def tela_login():
    st.title("🔒 Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario in USUARIOS and senha == USUARIOS[usuario]["senha"]:
            st.session_state["usuario"] = usuario
            st.session_state["perfil"] = USUARIOS[usuario]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

if "usuario" not in st.session_state:
    tela_login()
    st.stop()

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config("Sistema de Vendas - Auto Nunes", "🚗", layout="wide")

ARQUIVO_DADOS = "backup-vendas-auto.csv"
ARQUIVO_LOG = "log-uso-cashback.csv"
LIMITE_USO = 0.30  # 30%

# =============================
# INICIALIZAÇÃO DOS DADOS
# =============================
if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(
        ARQUIVO_DADOS,
        dtype={"CPF": str, "CPF_Vendedor": str},
        parse_dates=["Data_Venda", "Data_Expiracao"]
    )
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
# ATUALIZA CASHBACK EXPIRADO
# =============================
hoje = pd.to_datetime(date.today())
df.loc[
    (df["Status_Cashback"] == "Ativo") &
    (df["Data_Expiracao"] < hoje),
    "Status_Cashback"
] = "Expirado"
df.to_csv(ARQUIVO_DADOS, index=False)

# =============================
# MENU (POR PERFIL)
# =============================
if st.session_state["perfil"] == "gerencial":
    menu = st.sidebar.radio("Menu", [
        "📊 Dashboard",
        "➕ Nova Venda",
        "🔍 Buscar Cliente",
        "📄 Relatórios"
    ])
else:
    menu = st.sidebar.radio("Menu", ["➕ Nova Venda"])

st.sidebar.markdown("---")
st.sidebar.caption(f"Usuário: {st.session_state['usuario']}")

# =============================
# DASHBOARD (GERENCIAL)
# =============================
if menu == "📊 Dashboard":
    st.header("📊 Dashboard Gerencial")

    st.metric("Total de Vendas", len(df))
    st.metric(
        "Cashback Ativo",
        f"R$ {df[df['Status_Cashback']=='Ativo']['Valor_Cashback'].sum():,.2f}"
    )

    alerta = df[
        (df["Status_Cashback"] == "Ativo") &
        ((df["Data_Expiracao"] - hoje).dt.days <= 7)
    ]

    if not alerta.empty:
        st.warning("🔔 Cashback a vencer em até 7 dias")
        st.dataframe(alerta[["Nome","CPF","Valor_Cashback","Data_Expiracao"]])

    st.subheader("📊 Saldo Consolidado por Cliente")
    saldo = df[df["Status_Cashback"]=="Ativo"] \
        .groupby(["Nome","CPF"])["Valor_Cashback"] \
        .sum().reset_index()
    st.dataframe(saldo)

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    st.header("➕ Registrar Nova Venda")

    with st.form("form_venda"):
        nome = st.text_input("Nome do Cliente *")
        cpf = st.text_input("CPF do Cliente *")
        veiculo = st.selectbox(
            "Veículo",
            ["Onix","Onix Plus","Tracker","Spin","Montana","S10","Blazer"]
        )
        valor_venda = st.number_input("Valor da Venda", min_value=0.0, step=1000.0)
        percentual = st.selectbox("Cashback (%)", [0,5,10,15,20])
        data_venda = st.date_input("Data da Venda", value=date.today())

        cashback_disp = df[
            (df["CPF"]==cpf) &
            (df["Status_Cashback"]=="Ativo") &
            (df["Data_Expiracao"]>=pd.to_datetime(data_venda))
        ]["Valor_Cashback"].sum()

        usar_cashback = False
        nome_vend = cpf_vend = ""

        if cashback_disp > 0:
            st.info(f"💰 Cashback disponível: R$ {cashback_disp:,.2f}")
            usar_cashback = st.checkbox("Usar cashback")

            if usar_cashback:
                nome_vend = st.text_input("Nome do Vendedor *")
                cpf_vend = st.text_input("CPF do Vendedor *")

        limite = valor_venda * LIMITE_USO
        cashback_usado = min(cashback_disp, limite) if usar_cashback else 0
        valor_final = valor_venda - cashback_usado
        cashback_gerado = valor_final * (percentual / 100)

        st.markdown("### 📋 Resumo")
        st.write(f"Valor Final: R$ {valor_final:,.2f}")
        st.write(f"Cashback Gerado: R$ {cashback_gerado:,.2f}")

        salvar = st.form_submit_button("Salvar Venda")

        if salvar:
            if not nome or not cpf or valor_venda <= 0:
                st.error("Preencha todos os campos obrigatórios.")
            elif usar_cashback and (not nome_vend or not cpf_vend):
                st.error("Para usar cashback, informe o vendedor.")
            else:
                if usar_cashback:
                    df.loc[
                        (df["CPF"]==cpf) &
                        (df["Status_Cashback"]=="Ativo"),
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
                st.success("✅ Venda registrada com sucesso!")

# =============================
# BUSCAR CLIENTE (GERENCIAL)
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Nome ou CPF")
    resultado = df[
        df["Nome"].str.contains(busca, case=False, na=False) |
        df["CPF"].str.contains(busca, case=False, na=False)
    ]
    st.dataframe(resultado)

# =============================
# RELATÓRIOS (GERENCIAL)
# =============================
elif menu == "📄 Relatórios":
    st.header("📄 Relatórios Gerenciais")

    st.subheader("Vendas")
    st.dataframe(df)

    st.subheader("Histórico de Uso de Cashback")
    log = pd.read_csv(ARQUIVO_LOG)
    st.dataframe(log)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Vendas")
        log.to_excel(writer, index=False, sheet_name="Uso Cashback")

    st.download_button(
        "⬇ Baixar Relatório Completo",
        buffer.getvalue(),
        file_name="relatorio_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption(f"Usuário logado: {st.session_state['usuario']} | Perfil: {st.session_state['perfil']}")
