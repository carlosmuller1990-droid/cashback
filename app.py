import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from io import BytesIO

# =============================
# LOGIN
# =============================
USUARIOS = {
    "carlos": {"senha": "1234", "perfil": "admin"},
    "vendedor": {"senha": "1234", "perfil": "vendedor"}
}

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")

    user = st.text_input("Usuário")
    pwd = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if user in USUARIOS and pwd == USUARIOS[user]["senha"]:
            st.session_state.logado = True
            st.session_state.usuario = user
            st.session_state.perfil = USUARIOS[user]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

ARQUIVO_DADOS = "backup-vendas-auto.csv"
ARQUIVO_HISTORICO = "historico-cashback.csv"

# =============================
# FUNÇÃO CPF
# =============================
def cpf_valido(cpf):
    cpf = ''.join(filter(str.isdigit, cpf))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[num]) * ((i + 1) - num) for num in range(i))
        dig = ((soma * 10) % 11) % 10
        if dig != int(cpf[i]):
            return False
    return True

# =============================
# DADOS
# =============================
if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype={"CPF": str})
    df["Data_Venda"] = pd.to_datetime(df["Data_Venda"])
else:
    df = pd.DataFrame(columns=[
        "Nome","CPF","Veiculo","Valor_Venda",
        "Percentual_Cashback","Valor_Cashback",
        "Saldo_Cashback","Data_Venda","Data_Expiracao"
    ])
    df.to_csv(ARQUIVO_DADOS, index=False)

if os.path.exists(ARQUIVO_HISTORICO):
    hist = pd.read_csv(ARQUIVO_HISTORICO, dtype={"CPF": str, "CPF_Vendedor": str})
else:
    hist = pd.DataFrame(columns=[
        "Nome","CPF","Valor_Usado","Motivo",
        "Vendedor","CPF_Vendedor","Data"
    ])
    hist.to_csv(ARQUIVO_HISTORICO, index=False)

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
    ["📊 Dashboard de Vendas","➕ Nova Venda","🔍 Buscar Cliente"] +
    (["📄 Relatórios"] if st.session_state.perfil == "admin" else [])
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard de Vendas":
    total_vendas = len(df)
    valor_total = df["Valor_Venda"].sum()
    cashback_total = df["Valor_Cashback"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", total_vendas)
    c2.metric("Valor Total Vendido", f"R$ {valor_total:,.2f}")
    c3.metric("Cashback Concedido", f"R$ {cashback_total:,.2f}")

    st.subheader("🚗 Quantidade de Carros Vendidos")
    if not df.empty:
        carros = df.groupby("Veiculo").size().reset_index(name="Qtd")
        st.bar_chart(carros.set_index("Veiculo"))

    alerta = df[
        (df["Saldo_Cashback"] > 0) &
        (df["Data_Expiracao"] <= date.today() + timedelta(days=7))
    ]
    if not alerta.empty:
        st.warning("🔔 Cashback a vencer em até 7 dias")

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    with st.form("venda"):
        nome = st.text_input("Nome do Cliente *")
        cpf = st.text_input("CPF *")
        veiculo = st.selectbox("Veículo", [
            "Onix","Onix Plus","Tracker","Spin",
            "Montana","S10","Blazer","Spark EV","Captiva EV"
        ])
        valor = st.number_input("Valor da Venda", min_value=0.0, step=1000.0)
        perc = st.selectbox("Cashback (%)", [0,5,10,15,20])

        salvar = st.form_submit_button("Salvar")

        if salvar:
            if not cpf_valido(cpf):
                st.error("CPF inválido")
            else:
                cashback = valor * (perc/100)
                nova = {
                    "Nome": nome,
                    "CPF": cpf,
                    "Veiculo": veiculo,
                    "Valor_Venda": valor,
                    "Percentual_Cashback": perc,
                    "Valor_Cashback": cashback,
                    "Saldo_Cashback": cashback,
                    "Data_Venda": date.today(),
                    "Data_Expiracao": date.today() + timedelta(days=90)
                }
                df = pd.concat([df, pd.DataFrame([nova])])
                df.to_csv(ARQUIVO_DADOS, index=False)
                st.success("Venda registrada")

# =============================
# BUSCAR CLIENTE / USAR CASHBACK
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Nome ou CPF")
    resultado = df[df["Nome"].str.contains(busca, case=False, na=False) | df["CPF"].str.contains(busca, na=False)]

    st.dataframe(resultado)

    if not resultado.empty:
        linha = resultado.iloc[0]
        if linha["Saldo_Cashback"] > 0:
            with st.form("usar_cashback"):
                valor = st.number_input("Valor a usar", max_value=linha["Saldo_Cashback"])
                motivo = st.text_input("Motivo *")
                vendedor = st.text_input("Nome do Vendedor *")
                cpf_v = st.text_input("CPF do Vendedor *")
                usar = st.form_submit_button("Usar Cashback")

                if usar:
                    df.loc[linha.name,"Saldo_Cashback"] -= valor
                    hist.loc[len(hist)] = [
                        linha["Nome"],linha["CPF"],valor,motivo,
                        vendedor,cpf_v,date.today()
                    ]
                    df.to_csv(ARQUIVO_DADOS, index=False)
                    hist.to_csv(ARQUIVO_HISTORICO, index=False)
                    st.success("Cashback utilizado")

# =============================
# RELATÓRIO
# =============================
elif menu == "📄 Relatórios":
    st.dataframe(df)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    st.download_button("⬇ Baixar Excel", buffer.getvalue(), "relatorio.xlsx")
