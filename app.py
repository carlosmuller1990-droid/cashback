import streamlit as st
import pandas as pd
import hashlib
from datetime import date, timedelta
import plotly.express as px
import os

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Sistema de Cashback", layout="wide")

ARQUIVO_DADOS = "cashback.csv"
ARQUIVO_USUARIOS = "usuarios.csv"
LIMITE_USO_POR_COMPRA = 1000.0

# =============================
# FUNÇÕES
# =============================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        return pd.read_csv(
            ARQUIVO_DADOS,
            dtype={"CPF": str, "CPF_Vendedor_Uso": str},
            parse_dates=["Data_Venda", "Data_Expiracao", "Data_Uso"]
        )
    else:
        return pd.DataFrame(columns=[
            "Nome","CPF","Veiculo","Valor_Venda",
            "Percentual_Cashback","Valor_Cashback",
            "Saldo_Cashback","Data_Venda","Data_Expiracao",
            "Valor_Usado","Vendedor_Uso","CPF_Vendedor_Uso","Data_Uso"
        ])

def salvar_dados(df):
    df.to_csv(ARQUIVO_DADOS, index=False)

def carregar_usuarios():
    if not os.path.exists(ARQUIVO_USUARIOS):
        usuarios = pd.DataFrame([
            {"usuario":"carlos","senha":hash_senha("1234"),"perfil":"gerente"},
            {"usuario":"vendedor","senha":hash_senha("1234"),"perfil":"vendedor"},
        ])
        usuarios.to_csv(ARQUIVO_USUARIOS, index=False)
    return pd.read_csv(ARQUIVO_USUARIOS)

# =============================
# LOGIN
# =============================
if "login" not in st.session_state:
    st.session_state.login = False

usuarios = carregar_usuarios()

if not st.session_state.login:
    st.title("🔐 Login")

    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        senha_hash = hash_senha(s)
        user = usuarios[
            (usuarios["usuario"] == u) &
            (usuarios["senha"] == senha_hash)
        ]

        if not user.empty:
            st.session_state.login = True
            st.session_state.usuario = u
            st.session_state.perfil = user.iloc[0]["perfil"]
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.stop()

# =============================
# DADOS
# =============================
df = carregar_dados()

# =============================
# MENU
# =============================
menu = st.sidebar.radio(
    "Menu",
    ["📊 Dashboard","➕ Nova Venda","🔍 Pesquisar Cliente"]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard":
    st.title("📊 Dashboard de Cashback")

    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes", df["CPF"].nunique())
    col2.metric("Cashback Ativo", f"R$ {df['Saldo_Cashback'].sum():,.2f}")

    vencendo = df[
        (df["Saldo_Cashback"] > 0) &
        (df["Data_Expiracao"] <= pd.to_datetime(date.today() + timedelta(days=7)))
    ]
    col3.metric("Cashback a vencer (7 dias)", len(vencendo))

    st.subheader("📊 Saldo consolidado por cliente")
    saldo_cliente = df.groupby(["Nome","CPF"])["Saldo_Cashback"].sum().reset_index()
    st.dataframe(saldo_cliente)

    st.subheader("🚗 Vendas por Veículo")
    pizza = df.groupby("Veiculo")["Valor_Venda"].sum().reset_index()
    fig = px.pie(pizza, values="Valor_Venda", names="Veiculo")
    st.plotly_chart(fig, use_container_width=True)

    if st.session_state.perfil == "gerente":
        st.download_button(
            "⬇️ Baixar Relatório CSV",
            df.to_csv(index=False),
            file_name="cashback.csv"
        )

# =============================
# NOVA VENDA
# =============================
elif menu == "➕ Nova Venda":
    st.title("➕ Nova Venda")

    with st.form("venda"):
        nome = st.text_input("Nome do Cliente")
        cpf = st.text_input("CPF do Cliente")
        veiculo = st.selectbox(
            "Veículo",
            ["Onix","Onix Plus","Tracker","Spin","Montana","S10","Blazer"]
        )
        valor_venda = st.number_input("Valor da Venda", min_value=0.0, step=1000.0)
        percentual = st.selectbox("Cashback (%)", [0,5,10,15,20])
        salvar = st.form_submit_button("Salvar")

        if salvar:
            cashback = valor_venda * (percentual / 100)
            nova = {
                "Nome":nome,
                "CPF":cpf,
                "Veiculo":veiculo,
                "Valor_Venda":valor_venda,
                "Percentual_Cashback":percentual,
                "Valor_Cashback":cashback,
                "Saldo_Cashback":cashback,
                "Data_Venda":date.today(),
                "Data_Expiracao":date.today() + timedelta(days=90),
                "Valor_Usado":0.0,
                "Vendedor_Uso":"",
                "CPF_Vendedor_Uso":"",
                "Data_Uso":None
            }
            df = pd.concat([df, pd.DataFrame([nova])], ignore_index=True)
            salvar_dados(df)
            st.success("Venda registrada!")

# =============================
# PESQUISAR CLIENTE + USAR CASHBACK
# =============================
elif menu == "🔍 Pesquisar Cliente":
    st.title("🔍 Pesquisa de Cliente")

    termo = st.text_input("Buscar por Nome ou CPF")

    if termo:
        cliente = df[
            (df["Nome"].str.contains(termo, case=False, na=False)) |
            (df["CPF"].str.contains(termo, na=False))
        ]

        st.dataframe(cliente)

        saldo = cliente["Saldo_Cashback"].sum()
        st.metric("Saldo disponível", f"R$ {saldo:,.2f}")

        if saldo > 0:
            if st.button("💳 Usar Cashback"):
                with st.form("uso_cashback"):
                    st.subheader("Dados do Vendedor (obrigatório)")
                    vendedor = st.text_input("Nome do Vendedor")
                    cpf_vendedor = st.text_input("CPF do Vendedor")
                    valor_uso = st.number_input(
                        "Valor a usar",
                        min_value=0.0,
                        max_value=min(saldo, LIMITE_USO_POR_COMPRA)
                    )

                    confirmar = st.form_submit_button("Confirmar Uso")

                    if confirmar:
                        if vendedor and cpf_vendedor:
                            restante = valor_uso
                            for i, row in cliente.iterrows():
                                if restante <= 0:
                                    break
                                usar = min(row["Saldo_Cashback"], restante)
                                df.at[i,"Saldo_Cashback"] -= usar
                                df.at[i,"Valor_Usado"] += usar
                                df.at[i,"Vendedor_Uso"] = vendedor
                                df.at[i,"CPF_Vendedor_Uso"] = cpf_vendedor
                                df.at[i,"Data_Uso"] = date.today()
                                restante -= usar

                            salvar_dados(df)
                            st.success("Cashback utilizado com sucesso!")
                        else:
                            st.error("Nome e CPF do vendedor são obrigatórios")
