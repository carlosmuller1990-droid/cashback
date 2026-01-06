import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from io import BytesIO
import hashlib

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
def hash_senha(txt):
    return hashlib.sha256(txt.encode()).hexdigest()

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
# INICIALIZAÇÃO DOS DADOS
# =============================
COLUNAS = [
    "Nome", "CPF", "Veiculo",
    "Valor_Venda", "Percentual_Cashback",
    "Valor_Cashback", "Saldo_Cashback",
    "Data_Venda", "Data_Expiracao",
    "Tipo_Movimento", "Valor_Movimento",
    "Vendedor", "CPF_Vendedor", "Motivo"
]

if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype=str)
else:
    df = pd.DataFrame(columns=COLUNAS)

for c in COLUNAS:
    if c not in df.columns:
        df[c] = ""

num_cols = ["Valor_Venda", "Valor_Cashback", "Saldo_Cashback", "Valor_Movimento"]
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

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
    vendas = df[df["Tipo_Movimento"] == "CONCESSAO"]
    total_vendas = len(vendas)
    valor_total = vendas["Valor_Venda"].sum()
    cashback_total = vendas["Valor_Cashback"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", total_vendas)
    c2.metric("Valor Total Vendido", f"R$ {valor_total:,.2f}")
    c3.metric("Cashback Concedido", f"R$ {cashback_total:,.2f}")

    st.markdown("---")

    carros = vendas.groupby("Veiculo").size()
    st.subheader("🚗 Quantidade de Carros Vendidos")
    st.bar_chart(carros)

    ranking = vendas.groupby("Vendedor").size().reset_index(name="Vendas")
    st.subheader("🏆 Ranking de Vendedores")
    st.dataframe(ranking, use_container_width=True)

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

    with st.form("form_venda"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome do Cliente *")
            cpf = st.text_input("CPF *")
            veiculo = st.selectbox(
                "Veículo *",
                [
                    "Onix", "Onix Plus", "Tracker", "Spin",
                    "Montana", "S10", "Blazer",
                    "Spark EV", "Captiva EV"
                ]
            )

        with col2:
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, step=1000.0)
            percentual = st.selectbox("Percentual de Cashback", [0, 5, 10, 15, 20])

        salvar = st.form_submit_button("Salvar Venda")

        if salvar and nome and cpf and valor_venda > 0:
            cashback = valor_venda * percentual / 100

            nova = {
                "Nome": nome,
                "CPF": cpf,
                "Veiculo": veiculo,
                "Valor_Venda": valor_venda,
                "Percentual_Cashback": percentual,
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

            df = pd.concat([df, pd.DataFrame([nova])], ignore_index=True)
            df.to_csv(ARQUIVO_DADOS, index=False)
            st.success("Venda registrada com sucesso!")

# =============================
# BUSCAR CLIENTE (BOTÃO INDIVIDUAL)
# =============================
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")
    busca = st.text_input("Digite o nome ou CPF do cliente")

    if busca:
        clientes = df[
            df["Nome"].str.contains(busca, case=False, na=False) |
            df["CPF"].str.contains(busca, case=False, na=False)
        ]
    else:
        clientes = df

    saldo = clientes.groupby(["Nome", "CPF"], as_index=False)["Saldo_Cashback"].sum()

    for _, row in saldo.iterrows():
        st.markdown("---")
        c1, c2, c3 = st.columns([4, 2, 2])

        c1.markdown(f"**Cliente:** {row['Nome']}  \n**CPF:** {row['CPF']}")
        c2.metric("Saldo Cashback", f"R$ {row['Saldo_Cashback']:,.2f}")

        if c3.button("💳 Usar Cashback", key=f"usar_{row['CPF']}"):
            with st.form(f"form_uso_{row['CPF']}"):
                vendedor = st.text_input("Nome do Vendedor *")
                cpf_vend = st.text_input("CPF do Vendedor *")
                valor = st.number_input(
                    "Valor a usar (R$)",
                    min_value=0.0,
                    max_value=float(row["Saldo_Cashback"])
                )
                motivo = st.text_input("Motivo")

                confirmar = st.form_submit_button("Confirmar Uso")

                if confirmar and vendedor and cpf_vend:
                    base = df[
                        (df["Nome"] == row["Nome"]) &
                        (df["CPF"] == row["CPF"]) &
                        (df["Saldo_Cashback"] > 0)
                    ].iloc[0]

                    df.loc[
                        (df["Nome"] == row["Nome"]) &
                        (df["CPF"] == row["CPF"]),
                        "Saldo_Cashback"
                    ] -= valor

                    uso = {
                        "Nome": row["Nome"],
                        "CPF": row["CPF"],
                        "Veiculo": base["Veiculo"],
                        "Valor_Venda": 0,
                        "Percentual_Cashback": 0,
                        "Valor_Cashback": 0,
                        "Saldo_Cashback": 0,
                        "Data_Venda": date.today(),
                        "Data_Expiracao": base["Data_Expiracao"],
                        "Tipo_Movimento": "USO",
                        "Valor_Movimento": -valor,
                        "Vendedor": vendedor,
                        "CPF_Vendedor": cpf_vend,
                        "Motivo": motivo
                    }

                    df = pd.concat([df, pd.DataFrame([uso])], ignore_index=True)
                    df.to_csv(ARQUIVO_DADOS, index=False)
                    st.success("Cashback utilizado com sucesso!")
                    st.rerun()

# =============================
# RELATÓRIOS
# =============================
elif menu == "📄 Relatórios":
    if st.session_state.perfil != "gerente":
        st.warning("Acesso restrito ao gerente")
    else:
        st.dataframe(df, use_container_width=True)
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button(
            "⬇ Baixar Relatório em Excel",
            buffer.getvalue(),
            "relatorio_vendas.xlsx"
        )

# =============================
# RODAPÉ
# =============================
st.markdown("---")
st.caption("Sistema desenvolvido por Carlos Jr - Supervisor BDC")
