import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
import hashlib
from io import BytesIO

# =============================
# CONFIGURAÇÃO
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

ARQUIVO = "backup-vendas-auto.csv"
LIMITE_USO = 200.0
ALERTA_DIAS = 7

# =============================
# LOGIN (HASH)
# =============================
def hash_senha(s):
    return hashlib.sha256(s.encode()).hexdigest()

USUARIOS = {
    "carlos": {"senha": hash_senha("1234"), "perfil": "admin"},
    "vendedor": {"senha": hash_senha("1234"), "perfil": "vendedor"}
}

if "usuario" not in st.session_state:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if u in USUARIOS and hash_senha(s) == USUARIOS[u]["senha"]:
            st.session_state.usuario = u
            st.session_state.perfil = USUARIOS[u]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# =============================
# CARREGA DADOS
# =============================
COLUNAS = [
    "Nome", "CPF", "Veiculo", "Valor_Venda",
    "Percentual_Cashback", "Valor_Cashback",
    "Saldo_Cashback", "Data_Venda", "Data_Expiracao",
    "Cashback_Usado", "Valor_Usado",
    "Vendedor_Uso", "CPF_Vendedor_Uso", "Data_Uso"
]

if os.path.exists(ARQUIVO):
    df = pd.read_csv(ARQUIVO, dtype={"CPF": str, "CPF_Vendedor_Uso": str})
else:
    df = pd.DataFrame(columns=COLUNAS)
    df.to_csv(ARQUIVO, index=False)

# Datas
for c in ["Data_Venda", "Data_Expiracao", "Data_Uso"]:
    if c in df.columns:
        df[c] = pd.to_datetime(df[c], errors="coerce")

# =============================
# ALERTA CASHBACK
# =============================
alertas = df[
    (df["Saldo_Cashback"] > 0) &
    (df["Data_Expiracao"] <= datetime.now() + timedelta(days=ALERTA_DIAS))
]

if not alertas.empty:
    st.warning(f"🔔 {len(alertas)} cashback(s) vencendo em até 7 dias")

# =============================
# MENU
# =============================
st.sidebar.success(f"👤 {st.session_state.usuario}")

menu = st.sidebar.radio(
    "Menu",
    ["📊 Dashboard", "➕ Nova Venda", "💳 Usar Cashback", "🔍 Buscar Cliente", "📄 Relatórios"]
)

if st.sidebar.button("🚪 Sair"):
    st.session_state.clear()
    st.rerun()

# =============================
# DASHBOARD (ORIGINAL)
# =============================
if menu == "📊 Dashboard":
    st.header("📊 Dashboard de Vendas")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", len(df))
    c2.metric("Valor Total", f"R$ {df['Valor_Venda'].sum():,.2f}")
    c3.metric("Cashback Gerado", f"R$ {df['Valor_Cashback'].sum():,.2f}")

    st.subheader("📊 Saldo de Cashback por Cliente")
    saldo = df.groupby(["Nome", "CPF"])["Saldo_Cashback"].sum().reset_index()
    st.dataframe(saldo, use_container_width=True)

# =============================
# NOVA VENDA (ORIGINAL + SALDO)
# =============================
elif menu == "➕ Nova Venda":
    st.header("➕ Nova Venda")

    with st.form("venda"):
        nome = st.text_input("Nome")
        cpf = st.text_input("CPF")
        veiculo = st.selectbox("Veículo", ["Onix", "Tracker", "Spin", "S10"])
        valor = st.number_input("Valor da Venda", min_value=0.0)
        perc = st.selectbox("Cashback (%)", [0, 5, 10, 15])
        salvar = st.form_submit_button("Salvar")

    if salvar:
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
            "Cashback_Usado": False,
            "Valor_Usado": 0,
            "Vendedor_Uso": "",
            "CPF_Vendedor_Uso": "",
            "Data_Uso": None
        }
        df = pd.concat([df, pd.DataFrame([nova])])
        df.to_csv(ARQUIVO, index=False)
        st.success("Venda registrada")

# =============================
# USAR CASHBACK
# =============================
elif menu == "💳 Usar Cashback":
    st.header("💳 Usar Cashback")

    cpf = st.text_input("CPF do Cliente")
    vendedor = st.text_input("Vendedor")
    cpf_vendedor = st.text_input("CPF do Vendedor")

    if cpf:
        saldo = df[(df["CPF"] == cpf)]["Saldo_Cashback"].sum()
        st.info(f"Saldo disponível: R$ {saldo:.2f}")

        valor = st.number_input(
            "Valor a usar",
            min_value=0.0,
            max_value=min(saldo, LIMITE_USO)
        )

        if st.button("Usar"):
            if vendedor and cpf_vendedor and valor > 0:
                restante = valor
                for i, r in df[(df["CPF"] == cpf) & (df["Saldo_Cashback"] > 0)].iterrows():
                    if restante <= 0:
                        break
                    uso = min(r["Saldo_Cashback"], restante)
                    df.at[i, "Saldo_Cashback"] -= uso
                    df.at[i, "Valor_Usado"] += uso
                    df.at[i, "Cashback_Usado"] = True
                    df.at[i, "Vendedor_Uso"] = vendedor
                    df.at[i, "CPF_Vendedor_Uso"] = cpf_vendedor
                    df.at[i, "Data_Uso"] = datetime.now()
                    restante -= uso

                df.to_csv(ARQUIVO, index=False)
                st.success("Cashback utilizado")
            else:
                st.error("Informe vendedor e CPF")

# =============================
# BUSCAR CLIENTE
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Nome ou CPF")
    st.dataframe(df[df["Nome"].str.contains(busca, case=False, na=False) |
                     df["CPF"].str.contains(busca, na=False)])

# =============================
# RELATÓRIOS (SÓ CARLOS)
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.perfil != "admin":
        st.error("Acesso restrito")
    else:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            "⬇ Baixar Excel",
            buffer.getvalue(),
            "relatorio.xlsx"
        )
