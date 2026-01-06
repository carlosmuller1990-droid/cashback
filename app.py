import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta
import os
from io import BytesIO

# =============================
# LOGIN SIMPLES
# =============================
USUARIOS = {
    "carlos": {"senha": "1234", "perfil": "admin"},
    "vendedor": {"senha": "1234", "perfil": "vendedor"}
}

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if u in USUARIOS and s == USUARIOS[u]["senha"]:
            st.session_state.logado = True
            st.session_state.perfil = USUARIOS[u]["perfil"]
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
ARQUIVO_HIST = "historico-cashback.csv"

# =============================
# CPF
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
else:
    df = pd.DataFrame(columns=[
        "Nome","CPF","Veiculo","Valor_Venda",
        "Percentual_Cashback","Valor_Cashback",
        "Saldo_Cashback","Data_Venda","Data_Expiracao"
    ])
    df.to_csv(ARQUIVO_DADOS, index=False)

for col in ["Data_Venda","Data_Expiracao"]:
    if col not in df.columns:
        df[col] = pd.NaT
    df[col] = pd.to_datetime(df[col], errors="coerce")

if os.path.exists(ARQUIVO_HIST):
    hist = pd.read_csv(ARQUIVO_HIST, dtype={"CPF": str,"CPF_Vendedor": str})
else:
    hist = pd.DataFrame(columns=[
        "Nome","CPF","Valor_Usado","Motivo",
        "Vendedor","CPF_Vendedor","Data"
    ])
    hist.to_csv(ARQUIVO_HIST, index=False)

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
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", len(df))
    c2.metric("Valor Total Vendido", f"R$ {df['Valor_Venda'].sum():,.2f}")
    c3.metric("Cashback Concedido", f"R$ {df['Valor_Cashback'].sum():,.2f}")

    st.subheader("🚗 Quantidade de Carros Vendidos")

    if not df.empty:
        carros = df.groupby("Veiculo").size().reset_index(name="Qtd")

        grafico = alt.Chart(carros).mark_bar().encode(
            x=alt.X("Veiculo:N", title="Veículo"),
            y=alt.Y("Qtd:Q", title="Quantidade Vendida"),
            color=alt.Color("Veiculo:N", legend=None),
            tooltip=["Veiculo","Qtd"]
        ).properties(height=400)

        st.altair_chart(grafico, use_container_width=True)

    alerta = df[
        (df["Saldo_Cashback"] > 0) &
        (df["Data_Expiracao"] <= pd.Timestamp(date.today() + timedelta(days=7)))
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
        veiculo = st.selectbox(
            "Veículo",
            ["Onix","Onix Plus","Tracker","Spin","Montana","S10","Blazer","Spark EV","Captiva EV"]
        )
        valor = st.number_input("Valor da Venda (R$)", min_value=0.0, step=1000.0)
        perc = st.selectbox("Percentual de Cashback", [0,5,10,15,20])
        salvar = st.form_submit_button("Salvar Venda")

        if salvar:
            if not nome or not cpf_valido(cpf):
                st.error("CPF inválido ou campos obrigatórios vazios")
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
                df = pd.concat([df, pd.DataFrame([nova])], ignore_index=True)
                df.to_csv(ARQUIVO_DADOS, index=False)
                st.success("Venda registrada com sucesso")

# =============================
# BUSCAR CLIENTE / USAR CASHBACK
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Digite o nome ou CPF do cliente")
    resultado = df[
        df["Nome"].str.contains(busca, case=False, na=False) |
        df["CPF"].str.contains(busca, na=False)
    ] if busca else df

    st.dataframe(resultado, use_container_width=True)

    if not resultado.empty:
        linha = resultado.iloc[0]

        if linha["Saldo_Cashback"] > 0:
            st.markdown("### 💰 Usar Cashback")
            with st.form("usar_cb"):
                valor = st.number_input(
                    "Valor a usar",
                    min_value=0.0,
                    max_value=float(linha["Saldo_Cashback"])
                )
                motivo = st.text_input("Motivo do uso *")
                vendedor = st.text_input("Nome do Vendedor *")
                cpf_v = st.text_input("CPF do Vendedor *")
                usar = st.form_submit_button("Usar Cashback")

                if usar:
                    if not cpf_valido(cpf_v) or not motivo:
                        st.error("Dados do vendedor ou motivo inválidos")
                    else:
                        df.loc[linha.name,"Saldo_Cashback"] -= valor
                        hist.loc[len(hist)] = [
                            linha["Nome"],linha["CPF"],valor,motivo,
                            vendedor,cpf_v,date.today()
                        ]
                        df.to_csv(ARQUIVO_DADOS, index=False)
                        hist.to_csv(ARQUIVO_HIST, index=False)
                        st.success("Cashback utilizado com sucesso")

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    st.subheader("📊 Vendas")
    st.dataframe(df, use_container_width=True)

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Vendas")
        hist.to_excel(writer, index=False, sheet_name="Histórico Cashback")

    st.download_button(
        "⬇ Baixar Relatório Excel",
        buffer.getvalue(),
        "relatorio_vendas.xlsx"
    )

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Sistema desenvolvido por Carlos Jr - Supervisor BDC")
