import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from io import BytesIO
import hashlib

# =============================
# CONFIGURAÇÃO
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
def hash_senha(s):
    return hashlib.sha256(s.encode()).hexdigest()

USUARIOS = {
    "carlos": {"senha": hash_senha("1234"), "perfil": "gerente"},
    "vendedor": {"senha": hash_senha("1234"), "perfil": "vendedor"}
}

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if u in USUARIOS and hash_senha(s) == USUARIOS[u]["senha"]:
            st.session_state.logado = True
            st.session_state.usuario = u
            st.session_state.perfil = USUARIOS[u]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# =============================
# INICIALIZAÇÃO DO CSV
# =============================
COLUNAS = [
    "Nome", "CPF", "Veiculo", "Valor_Venda",
    "Percentual_Cashback", "Valor_Cashback",
    "Saldo_Cashback",
    "Data_Venda", "Data_Expiracao",
    "Tipo_Movimento",  # CONCESSAO / USO / ESTORNO
    "Valor_Movimento",
    "Vendedor", "CPF_Vendedor",
    "Motivo"
]

if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype=str)
else:
    df = pd.DataFrame(columns=COLUNAS)

for c in COLUNAS:
    if c not in df.columns:
        df[c] = ""

df["Valor_Venda"] = pd.to_numeric(df["Valor_Venda"], errors="coerce").fillna(0)
df["Valor_Cashback"] = pd.to_numeric(df["Valor_Cashback"], errors="coerce").fillna(0)
df["Saldo_Cashback"] = pd.to_numeric(df["Saldo_Cashback"], errors="coerce").fillna(0)
df["Valor_Movimento"] = pd.to_numeric(df["Valor_Movimento"], errors="coerce").fillna(0)
df["Data_Venda"] = pd.to_datetime(df["Data_Venda"], errors="coerce")
df["Data_Expiracao"] = pd.to_datetime(df["Data_Expiracao"], errors="coerce")

# =============================
# EXPIRAÇÃO AUTOMÁTICA
# =============================
hoje = pd.Timestamp.today()
df.loc[
    (df["Saldo_Cashback"] > 0) &
    (df["Data_Expiracao"] < hoje),
    "Saldo_Cashback"
] = 0

df.to_csv(ARQUIVO_DADOS, index=False)

# =============================
# TÍTULO
# =============================
st.title("🚗 Sistema de Vendas - Auto Nunes")
st.markdown("---")

# =============================
# MENU
# =============================
st.sidebar.title("📌 Menu")
menu = st.sidebar.radio(
    "Selecione:",
    ["📊 Dashboard de Vendas", "➕ Nova Venda", "🔍 Buscar Cliente", "📄 Relatórios"]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard de Vendas":
    total = len(df[df["Tipo_Movimento"] == "CONCESSAO"])
    vendido = df["Valor_Venda"].sum()
    cashback = df[df["Tipo_Movimento"] == "CONCESSAO"]["Valor_Cashback"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Vendas", total)
    c2.metric("Valor Vendido", f"R$ {vendido:,.2f}")
    c3.metric("Cashback Concedido", f"R$ {cashback:,.2f}")

    st.markdown("---")

    carros = df[df["Tipo_Movimento"] == "CONCESSAO"].groupby("Veiculo").size()
    st.subheader("🚗 Carros Vendidos")
    st.bar_chart(carros)

    st.subheader("🏆 Ranking de Vendedores")
    ranking = df[df["Tipo_Movimento"] == "CONCESSAO"].groupby("Vendedor").size()
    st.dataframe(ranking.reset_index(name="Vendas"))

    alerta = df[
        (df["Saldo_Cashback"] > 0) &
        (df["Data_Expiracao"] <= hoje + timedelta(days=7))
    ]
    if not alerta.empty:
        st.warning("⚠ Cashback a vencer em até 7 dias")
        st.dataframe(alerta[["Nome", "CPF", "Saldo_Cashback", "Data_Expiracao"]])

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    st.header("➕ Registrar Nova Venda")

    with st.form("venda"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome *")
            cpf = st.text_input("CPF *")
            veiculo = st.selectbox(
                "Veículo",
                ["Onix", "Onix Plus", "Tracker", "Spin", "Montana", "S10", "Blazer"]
            )
        with col2:
            valor = st.number_input("Valor Venda", min_value=0.0)
            perc = st.selectbox("Cashback %", [0, 5, 10, 15, 20])

        if st.form_submit_button("Salvar"):
            cashback = valor * perc / 100
            nova = {
                "Nome": nome,
                "CPF": cpf,
                "Veiculo": veiculo,
                "Valor_Venda": valor,
                "Percentual_Cashback": perc,
                "Valor_Cashback": cashback,
                "Saldo_Cashback": cashback,
                "Data_Venda": date.today(),
                "Data_Expiracao": date.today() + timedelta(days=90),
                "Tipo_Movimento": "CONCESSAO",
                "Valor_Movimento": cashback,
                "Vendedor": st.session_state.usuario,
                "CPF_Vendedor": "",
                "Motivo": ""
            }
            df = pd.concat([df, pd.DataFrame([nova])])
            df.to_csv(ARQUIVO_DADOS, index=False)
            st.success("Venda registrada")

# =============================
# BUSCAR CLIENTE / USAR CASHBACK
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Nome ou CPF")

    res = df[df["Nome"].str.contains(busca, case=False, na=False) |
             df["CPF"].str.contains(busca, case=False, na=False)]

    st.dataframe(res)

    saldo = res.groupby(["Nome", "CPF"])["Saldo_Cashback"].sum().reset_index()
    if not saldo.empty:
        st.subheader("💰 Saldo Cashback")
        st.dataframe(saldo)

        if st.button("Usar Cashback"):
            with st.form("usar"):
                vendedor = st.text_input("Vendedor *")
                cpf_vend = st.text_input("CPF Vendedor *")
                valor = st.number_input("Valor a usar", min_value=0.0)
                motivo = st.text_input("Motivo")
                if st.form_submit_button("Confirmar"):
                    if vendedor and cpf_vend:
                        idx = res.index[0]
                        df.at[idx, "Saldo_Cashback"] -= valor
                        uso = {
                            **df.loc[idx],
                            "Tipo_Movimento": "USO",
                            "Valor_Movimento": -valor,
                            "Vendedor": vendedor,
                            "CPF_Vendedor": cpf_vend,
                            "Motivo": motivo
                        }
                        df = pd.concat([df, pd.DataFrame([uso])])
                        df.to_csv(ARQUIVO_DADOS, index=False)
                        st.success("Cashback usado")

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.perfil != "gerente":
        st.warning("Acesso restrito")
    else:
        st.dataframe(df)
        buf = BytesIO()
        df.to_excel(buf, index=False)
        st.download_button("⬇ Excel", buf.getvalue(), "relatorio.xlsx")

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Sistema desenvolvido por Carlos Jr - Supervisor BDC")
