import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
import hashlib
from io import BytesIO

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

# =============================
# CONFIGURAÇÕES GERAIS
# =============================
ARQUIVO_DADOS = "backup-vendas-auto.csv"
LIMITE_USO = 200.0
ALERTA_DIAS = 7

# =============================
# LOGIN (SENHA CRIPTOGRAFADA)
# =============================
def hash_senha(s):
    return hashlib.sha256(s.encode()).hexdigest()

USUARIOS = {
    "carlos": {"senha": hash_senha("1234"), "perfil": "admin"},
    "vendedor": {"senha": hash_senha("1234"), "perfil": "vendedor"}
}

if "usuario" not in st.session_state:
    st.title("🔐 Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario in USUARIOS and hash_senha(senha) == USUARIOS[usuario]["senha"]:
            st.session_state.usuario = usuario
            st.session_state.perfil = USUARIOS[usuario]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
    st.stop()

# =============================
# INICIALIZAÇÃO / COMPATIBILIDADE CSV
# =============================
COLUNAS = [
    "Nome", "CPF", "Veiculo", "Valor_Venda",
    "Percentual_Cashback", "Valor_Cashback",
    "Saldo_Cashback",
    "Data_Venda", "Data_Expiracao",
    "Cashback_Usado", "Valor_Usado",
    "Vendedor_Uso", "CPF_Vendedor_Uso", "Data_Uso"
]

if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype={"CPF": str, "CPF_Vendedor_Uso": str})
else:
    df = pd.DataFrame()

# 🔧 Garante colunas novas sem quebrar dados antigos
for col in COLUNAS:
    if col not in df.columns:
        if col in ["Saldo_Cashback", "Valor_Usado"]:
            df[col] = 0.0
        elif col == "Cashback_Usado":
            df[col] = False
        else:
            df[col] = ""

# Datas
for d in ["Data_Venda", "Data_Expiracao", "Data_Uso"]:
    df[d] = pd.to_datetime(df[d], errors="coerce")

df.to_csv(ARQUIVO_DADOS, index=False)

# =============================
# ALERTA CASHBACK A VENCER
# =============================
alertas = df[
    (df["Saldo_Cashback"] > 0) &
    (df["Data_Expiracao"] <= datetime.now() + timedelta(days=ALERTA_DIAS))
]

if not alertas.empty:
    st.warning(f"🔔 {len(alertas)} cashback(s) vencendo em até 7 dias")

# =============================
# MENU LATERAL (ORIGINAL)
# =============================
st.sidebar.title("📌 Menu")
st.sidebar.success(f"👤 {st.session_state.usuario}")

menu = st.sidebar.radio(
    "Selecione:",
    [
        "📊 Dashboard de Vendas",
        "➕ Nova Venda",
        "💳 Usar Cashback",
        "🔍 Buscar Cliente",
        "📄 Relatórios"
    ]
)

if st.sidebar.button("🚪 Sair"):
    st.session_state.clear()
    st.rerun()

# =============================
# DASHBOARD (ORIGINAL + SALDO)
# =============================
if menu == "📊 Dashboard de Vendas":
    st.header("📊 Dashboard de Vendas")

    total_vendas = len(df)
    valor_total = df["Valor_Venda"].astype(float).sum()
    cashback_total = df["Valor_Cashback"].astype(float).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", total_vendas)
    c2.metric("Valor Total Vendido", f"R$ {valor_total:,.2f}")
    c3.metric("Cashback Gerado", f"R$ {cashback_total:,.2f}")

    st.subheader("📊 Saldo de Cashback por Cliente")
    saldo = df.groupby(["Nome", "CPF"])["Saldo_Cashback"].sum().reset_index()
    st.dataframe(saldo, use_container_width=True)

# =============================
# NOVA VENDA (ORIGINAL)
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
                ["Onix", "Onix Plus", "Tracker", "Spin", "Montana", "S10", "Blazer"]
            )
            data_venda = st.date_input("Data da Venda", value=date.today())

        with col2:
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, step=1000.0)
            percentual = st.selectbox("Percentual de Cashback", [0, 5, 10, 15, 20])

        valor_cashback = valor_venda * (percentual / 100)

        salvar = st.form_submit_button("Salvar Venda")

        if salvar:
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
                "Cashback_Usado": False,
                "Valor_Usado": 0.0,
                "Vendedor_Uso": "",
                "CPF_Vendedor_Uso": "",
                "Data_Uso": None
            }
            df = pd.concat([df, pd.DataFrame([nova])])
            df.to_csv(ARQUIVO_DADOS, index=False)
            st.success("Venda registrada com sucesso!")

# =============================
# USAR CASHBACK
# =============================
elif menu == "💳 Usar Cashback":
    st.header("💳 Usar Cashback")

    cpf = st.text_input("CPF do Cliente")
    vendedor = st.text_input("Nome do Vendedor")
    cpf_vendedor = st.text_input("CPF do Vendedor")

    if cpf:
        saldo = df[df["CPF"] == cpf]["Saldo_Cashback"].sum()
        st.info(f"Saldo disponível: R$ {saldo:.2f}")

        valor = st.number_input(
            "Valor a usar",
            min_value=0.0,
            max_value=min(saldo, LIMITE_USO)
        )

        if st.button("Usar Cashback"):
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

                df.to_csv(ARQUIVO_DADOS, index=False)
                st.success("Cashback utilizado com sucesso!")
            else:
                st.error("Informe vendedor, CPF e valor válido")

# =============================
# BUSCAR CLIENTE (ORIGINAL)
# =============================
elif menu == "🔍 Buscar Cliente":
    busca = st.text_input("Digite o nome ou CPF")
    resultado = df[
        df["Nome"].str.contains(busca, case=False, na=False) |
        df["CPF"].str.contains(busca, case=False, na=False)
    ]
    st.dataframe(resultado, use_container_width=True)

# =============================
# RELATÓRIOS (ORIGINAL + BLOQUEIO)
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.perfil != "admin":
        st.error("Acesso restrito ao administrador")
    else:
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            "⬇ Baixar Relatório em Excel",
            buffer.getvalue(),
            file_name="relatorio_vendas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Sistema desenvolvido por Carlos Jr - Supervisor BDC")
