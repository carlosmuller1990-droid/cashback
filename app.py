import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ========== CONFIGURAÇÃO SIMPLIFICADA ==========
st.set_page_config(page_title="Auto Nunes", layout="wide")
st.title("🚗 Auto Nunes - Sistema de Vendas")
st.markdown("---")

# ========== BANCO DE DADOS SIMPLES ==========
def init_simple_db():
    """Banco de dados simplificado sem erros"""
    conn = sqlite3.connect('vendas.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        cpf TEXT UNIQUE,
        carro TEXT,
        valor REAL,
        cashback INTEGER,
        data DATE
    )''')
    conn.commit()
    conn.close()

init_simple_db()

# ========== DADOS FIXOS ==========
CARROS = ["Onix", "Onix Plus", "Tracker", "Spin", "Captiva", 
          "Blazer", "Blazer Elétrica", "S10", "Montana"]

# ========== FUNÇÃO PRINCIPAL SIMPLES ==========
def salvar_cliente(nome, cpf, carro, valor, cashback):
    """Função simples para testar"""
    try:
        conn = sqlite3.connect('vendas.db')
        c = conn.cursor()
        data_atual = datetime.now().strftime("%Y-%m-%d")
        
        c.execute('''INSERT INTO clientes 
                    (nome, cpf, carro, valor, cashback, data)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (nome, cpf, carro, valor, cashback, data_atual))
        
        conn.commit()
        conn.close()
        return True, "✅ Cliente salvo com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"

# ========== INTERFACE SIMPLES ==========
tab1, tab2, tab3 = st.tabs(["➕ Nova Venda", "🔍 Buscar", "📊 Dashboard"])

with tab1:
    st.header("Cadastrar Nova Venda")
    
    nome = st.text_input("Nome do Cliente")
    cpf = st.text_input("CPF")
    carro = st.selectbox("Veículo", CARROS)
    valor = st.number_input("Valor (R$)", min_value=0.0, value=50000.0)
    cashback = st.slider("Cashback %", 0, 20, 5)
    
    if st.button("💾 Salvar", type="primary"):
        if nome and cpf:
            sucesso, msg = salvar_cliente(nome, cpf, carro, valor, cashback)
            if sucesso:
                st.success(msg)
                st.balloons()
            else:
                st.error(msg)
        else:
            st.warning("Preencha nome e CPF")

with tab2:
    st.header("Buscar Clientes")
    
    conn = sqlite3.connect('vendas.db')
    df = pd.read_sql_query("SELECT * FROM clientes", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("Nenhum cliente cadastrado")

with tab3:
    st.header("Dashboard")
    
    conn = sqlite3.connect('vendas.db')
    df = pd.read_sql_query("SELECT * FROM clientes", conn)
    conn.close()
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Clientes", len(df))
        with col2:
            st.metric("Faturamento", f"R$ {df['valor'].sum():,.2f}")
        with col3:
            st.metric("Ticket Médio", f"R$ {df['valor'].mean():,.2f}")
    else:
        st.info("Aguardando dados...")

st.caption("Sistema Auto Nunes - Versão Simplificada")
