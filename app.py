import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
from io import BytesIO

# -----------------------------
# Configuração da página
# -----------------------------
st.set_page_config(
    page_title="Sistema de Cashback - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Sistema de Vendas - Auto Nunes")

# -----------------------------
# Banco de Dados
# -----------------------------
os.makedirs("data", exist_ok=True)
DB_PATH = "data/vendas_auto_nunes.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_cliente TEXT,
            cpf TEXT UNIQUE,
            carro TEXT,
            valor_venda REAL,
            percentual_cashback INTEGER,
            valor_cashback REAL,
            valor_final REAL,
            data_venda TEXT,
            data_expiracao_cashback TEXT,
            cashback_utilizado INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Funções
# -----------------------------
def registrar_venda(nome, cpf, carro, valor_venda, percentual):
    valor_cashback = round(valor_venda * (percentual / 100), 2)
    valor_final = round(valor_venda - valor_cashback, 2)

    data_venda = datetime.today().date()
    data_expiracao = data_venda + timedelta(days=90)

    conn = get_conn()
    c = conn.cursor()

    try:
        c.execute("""
            INSERT INTO vendas (
                nome_cliente, cpf, carro, valor_venda,
                percentual_cashback, valor_cashback, valor_final,
                data_venda, data_expiracao_cashback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome,
            cpf,
            carro,
            valor_venda,
            percentual,
            valor_cashback,
            valor_final,
            data_venda.strftime("%Y-%m-%d"),
            data_expiracao.strftime("%Y-%m-%d")
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_vendas():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM vendas", conn)
    conn.close()
    return df

def get_cashbacks_ativos():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT nome_cliente, cpf, carro, valor_cashback, data_expiracao_cashback
        FROM vendas
        WHERE cashback_utilizado = 0
          AND valor_cashback > 0
    """, conn)
    conn.close()

    if df.empty:
        return df

    df["data_expiracao_cashback"] = pd.to_datetime(df["data_expiracao_cashback"])
    hoje = pd.Timestamp.today().normalize()
    df["dias_restantes"] = (df["data_expiracao_cashback"] - hoje).dt.days
    df = df[df["dias_restantes"] >= 0]

    return df

def relatorio_carros_vendidos():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT carro AS Modelo, COUNT(*) AS Quantidade
        FROM vendas
        GROUP BY carro
        ORDER BY Quantidade DESC
    """, conn)
    conn.close()
    return df

def gerar_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Relatório")
    buffer.seek(0)
    return buffer

# -----------------------------
# Interface
# -----------------------------
menu = st.sidebar.radio(
    "Menu",
    ["➕ Nova Venda", "💰 Cashbacks Ativos", "📊 Relatórios", "📋 Histórico"]
)

# -----------------------------
# Nova Venda
# -----------------------------
if menu == "➕ Nova Venda":
    st.header("➕ Registrar Nova Venda")

    col1, col2 = st.columns(2)

    with col1:
        nome = st.text_input("Nome do Cliente")
        cpf = st.text_input("CPF")
        carro = st.selectbox(
            "Modelo do Veículo",
            ["Onix", "Onix Plus", "Tracker", "Spin", "Montana", "S10", "Captiva"]
        )

    with col2:
        valor_venda = st.number_input("Valor do Veículo (R$)", min_value=0.0, step=1000.0)
        percentual = st.selectbox("Cashback (%)", [0, 5, 10, 15, 20])

    valor_cashback = round(valor_venda * (percentual / 100), 2)
    valor_final = round(valor_venda - valor_cashback, 2)

    st.markdown("### 📋 Resumo da Venda")
    c1, c2, c3 = st.columns(3)
    c1.metric("Valor do Veículo", f"R$ {valor_venda:,.2f}")
    c2.metric("Cashback", f"R$ {valor_cashback:,.2f}")
    c3.metric("Valor Final", f"R$ {valor_final:,.2f}")

    if st.button("✅ Registrar Venda"):
        if nome and cpf and valor_venda > 0:
            if registrar_venda(nome, cpf, carro, valor_venda, percentual):
                st.success("Venda registrada com sucesso!")
                st.balloons()
            else:
                st.error("CPF já cadastrado.")
        else:
            st.error("Preencha todos os campos.")

# -----------------------------
# Cashbacks Ativos
# -----------------------------
elif menu == "💰 Cashbacks Ativos":
    st.header("💰 Cashbacks Ativos")
    df = get_cashbacks_ativos()

    if df.empty:
        st.info("Nenhum cashback ativo.")
    else:
        st.dataframe(df, use_container_width=True)

# -----------------------------
# Relatórios
# -----------------------------
elif menu == "📊 Relatórios":
    st.header("📊 Relatórios")

    st.subheader("🚗 Quantidade de Carros Vendidos por Modelo")
    df_carros = relatorio_carros_vendidos()

    if df_carros.empty:
        st.info("Nenhuma venda registrada.")
    else:
        st.dataframe(df_carros, use_container_width=True)

        st.bar_chart(df_carros.set_index("Modelo"))

        excel = gerar_excel(df_carros)
        st.download_button(
            "📥 Baixar Relatório em Excel",
            data=excel,
            file_name="relatorio_carros_vendidos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# -----------------------------
# Histórico
# -----------------------------
elif menu == "📋 Histórico":
    st.header("📋 Histórico de Vendas")
    df = get_vendas()

    if df.empty:
        st.info("Nenhuma venda registrada.")
    else:
        st.dataframe(df, use_container_width=True)

# -----------------------------
# Rodapé
# -----------------------------
st.markdown("---")
st.caption("Sistema Auto Nunes © 2024 | Cashback válido por 90 dias")
