import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ========== CONFIGURAÇÃO CRÍTICA PARA STREAMLIT CLOUD ==========
# Cria pasta persistente para o banco de dados
os.makedirs('/data', exist_ok=True)

def get_db_connection():
    """Conexão com banco na pasta persistente do Streamlit"""
    return sqlite3.connect('/data/vendas_auto_nunes.db')

# ========== CONFIGURAÇÃO DA PÁGINA ==========
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Sistema de Vendas - Auto Nunes Concessionária")
st.markdown("---")

# ========== INICIALIZAR BANCO DE DADOS ==========
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabela de vendas
    c.execute('''CREATE TABLE IF NOT EXISTS vendas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome_cliente TEXT NOT NULL,
                  cpf TEXT UNIQUE NOT NULL,
                  data_nascimento DATE NOT NULL,
                  carro_comprado TEXT NOT NULL,
                  valor_original REAL NOT NULL,
                  percentual_cashback INTEGER NOT NULL,
                  valor_com_cashback REAL NOT NULL,
                  valor_cashback REAL NOT NULL,
                  data_compra DATE NOT NULL,
                  data_expiracao_cashback DATE NOT NULL,
                  cashback_utilizado BOOLEAN DEFAULT 0,
                  data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de utilização de cashback
    c.execute('''CREATE TABLE IF NOT EXISTS uso_cashback
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  venda_id INTEGER NOT NULL,
                  valor_utilizado REAL NOT NULL,
                  data_utilizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (venda_id) REFERENCES vendas (id))''')
    
    conn.commit()
    conn.close()

init_db()

# ========== DADOS FIXOS - OPÇÕES PRÉ-DEFINIDAS ==========
# NÃO PRECISA ESCREVER - APENAS SELECIONAR
CARROS_DISPONIVEIS = [
    "Onix",
    "Onix Plus", 
    "Tracker",
    "Spin",
    "Captiva",
    "Blazer",
    "Blazer Elétrica",
    "S10",
    "Montana"
]

# Opções de cashback
OPCOES_CASHBACK = [
    {"label": "Sem Cashback", "percentual": 0},
    {"label": "Cashback 5%", "percentual": 5},
    {"label": "Cashback 10%", "percentual": 10},
    {"label": "Cashback 15%", "percentual": 15},
    {"label": "Cashback 20%", "percentual": 20}
]

# ========== FUNÇÕES COMPLETAS ==========
def add_venda(nome, cpf, data_nasc, carro, valor_original, percentual_cashback):
    """Adiciona nova venda com cashback"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Calcular valores com cashback
    valor_cashback = valor_original * (percentual_cashback / 100)
    valor_com_cashback = valor_original - valor_cashback
    
    # Datas
    data_compra = datetime.now().date()
    data_expiracao = data_compra + relativedelta(months=3)
    
    try:
        c.execute('''INSERT INTO vendas 
                     (nome_cliente, cpf, data_nascimento, carro_comprado, 
                      valor_original, percentual_cashback, valor_com_cashback, 
                      valor_cashback, data_compra, data_expiracao_cashback)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (nome, cpf, data_nasc, carro, valor_original, 
                   percentual_cashback, valor_com_cashback, valor_cashback,
                   data_compra, data_expiracao))
        conn.commit()
        return True, "✅ Venda registrada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "❌ CPF já cadastrado no sistema!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def search_vendas(termo):
    """Busca vendas por nome ou CPF"""
    conn = get_db_connection()
    
    query = '''SELECT * FROM vendas 
               WHERE nome_cliente LIKE ? OR cpf LIKE ?
               ORDER BY data_cadastro DESC'''
    
    df = pd.read_sql_query(query, conn, params=(f'%{termo}%', f'%{termo}%'))
    conn.close()
    
    # Converter datas
    if not df.empty:
        df['data_nascimento'] = pd.to_datetime(df['data_nascimento'])
        df['data_compra'] = pd.to_datetime(df['data_compra'])
        df['data_expiracao_cashback'] = pd.to_datetime(df['data_expiracao_cashback'])
    
    return df

def get_all_vendas():
    """Obtém todas as vendas"""
    conn = get_db_connection()
    df = pd.read_sql_query('SELECT * FROM vendas ORDER BY data_cadastro DESC', conn)
    conn.close()
    
    if not df.empty:
        df['data_nascimento'] = pd.to_datetime(df['data_nascimento'])
        df['data_compra'] = pd.to_datetime(df['data_compra'])
        df['data_expiracao_cashback'] = pd.to_datetime(df['data_expiracao_cashback'])
    
    return df

def get_cashbacks_ativos():
    """Busca cashbacks ativos (válidos por 3 meses)"""
    conn = get_db_connection()
    hoje = datetime.now().date()
    
    query = '''SELECT * FROM vendas 
               WHERE data_expiracao_cashback >= ? 
               AND cashback_utilizado = 0
               AND valor_cashback > 0
               ORDER BY data_expiracao_cashback'''
    
    df = pd.read_sql_query(query, conn, params=(hoje,))
    conn.close()
    
    if not df.empty:
        df['data_nascimento'] = pd.to_datetime(df['data_nascimento'])
        df['data_compra'] = pd.to_datetime(df['data_compra'])
        df['data_expiracao_cashback'] = pd.to_datetime(df['data_expiracao_cashback'])
        
        # Calcular dias restantes
        df['dias_restantes'] = (df['data_expiracao_cashback'].dt.date - hoje).dt.days
    
    return df

def usar_cashback(venda_id, valor_utilizado):
    """Registra utilização de cashback"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Registrar utilização
        c.execute('''INSERT INTO uso_cashback (venda_id, valor_utilizado)
                     VALUES (?, ?)''', (venda_id, valor_utilizado))
        
        # Marcar como utilizado se valor total for usado
        c.execute('''UPDATE vendas 
                     SET cashback_utilizado = 1
                     WHERE id = ?''', (venda_id,))
        
        conn.commit()
        return True, "✅ Cashback utilizado com sucesso!"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def get_stats():
    """Estatísticas do sistema"""
    conn = get_db_connection()
    
    # Total de vendas
    total_vendas = pd.read_sql_query('SELECT COUNT(*) as total FROM vendas', conn).iloc[0]['total']
    
    # Valor total vendido
    valor_total = pd.read_sql_query('SELECT SUM(valor_com_cashback) as total FROM vendas', conn).iloc[0]['total']
    valor_total = valor_total if valor_total else 0
    
    # Cashback total
    cashback_total = pd.read_sql_query('SELECT SUM(valor_cashback) as total FROM vendas', conn).iloc[0]['total']
    cashback_total = cashback_total if cashback_total else 0
    
    # Carros mais vendidos
    carros_top = pd.read_sql_query('''SELECT carro_comprado, COUNT(*) as quantidade 
                                       FROM vendas 
                                       GROUP BY carro_comprado 
                                       ORDER BY quantidade DESC''', conn)
    
    # Cashbacks ativos
    hoje = datetime.now().date()
    cashbacks_ativos = pd.read_sql_query('''SELECT COUNT(*) as ativos 
                                            FROM vendas 
                                            WHERE data_expiracao_cashback >= ? 
                                            AND cashback_utilizado = 0
                                            AND valor_cashback > 0''', 
                                         conn, params=(hoje,)).iloc[0]['ativos']
    
    conn.close()
    
    return total_vendas, valor_total, cashback_total, carros_top, cashbacks_ativos

# ========== INTERFACE COMPLETA ==========
st.sidebar.title("🚗 Menu Auto Nunes")
menu = st.sidebar.radio(
    "Selecione uma opção:",
    ["🏠 Dashboard", "➕ Nova Venda", "🔍 Buscar Cliente", "💰 Cashbacks Ativos", "📊 Relatórios"]
)

st.sidebar.markdown("---")
st.sidebar.info("**Concessionária Chevrolet**\n\nCashback válido por 3 meses")

# DASHBOARD
if menu == "🏠 Dashboard":
    st.header("📊 Dashboard de Vendas")
    
    total_vendas, valor_total, cashback_total, carros_top, cashbacks_ativos = get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Vendas", total_vendas)
    
    with col2:
        st.metric("Valor Total Vendido", f"R$ {valor_total:,.2f}")
    
    with col3:
        st.metric("Cashback Concedido", f"R$ {cashback_total:,.2f}")
    
    with col4:
        st.metric("Cashbacks Ativos", cashbacks_ativos)
    
    if not carros_top.empty:
        st.subheader("🚗 Modelos Mais Vendidos")
        st.bar_chart(carros_top.set_index('carro_comprado'))
    
    st.subheader("🆕 Últimas Vendas")
    todas_vendas = get_all_vendas()
    if not todas_vendas.empty:
        st.dataframe(todas_vendas[['nome_cliente', 'carro_comprado', 'valor_com_cashback', 
                                  'percentual_cashback', 'data_compra']].head(10), 
                    use_container_width=True)

# NOVA VENDA
elif menu == "➕ Nova Venda":
    st.header("➕ Registrar Nova Venda")
    
    with st.form("form_venda"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome Completo do Cliente *", max_chars=100)
            cpf = st.text_input("CPF *", max_chars=14, 
                               help="Formato: 000.000.000-00")
            data_nasc = st.date_input("Data de Nascimento *", 
                                     max_value=datetime.now().date())
        
        with col2:
            # SELECTBOX - NÃO PRECISA ESCREVER
            carro = st.selectbox("Carro Comprado *", CARROS_DISPONIVEIS)
            valor_original = st.number_input("Valor do Veículo (R$) *", 
                                           min_value=0.0, 
                                           step=1000.0,
                                           format="%.2f")
            
            cashback_opcao = st.selectbox(
                "Cashback *",
                options=OPCOES_CASHBACK,
                format_func=lambda x: x["label"]
            )
            
            percentual = cashback_opcao["percentual"]
            valor_cashback = valor_original * (percentual / 100)
            valor_final = valor_original - valor_cashback
        
        st.markdown("---")
        st.subheader("📋 Resumo da Venda")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            st.metric("Valor Original", f"R$ {valor_original:,.2f}")
        
        with col_res2:
            st.metric(f"Cashback ({percentual}%)", f"-R$ {valor_cashback:,.2f}")
        
        with col_res3:
            st.metric("Valor Final", f"R$ {valor_final:,.2f}")
        
        data_expiracao = datetime.now().date() + relativedelta(months=3)
        if percentual > 0:
            st.info(f"💰 **Cashback válido até:** {data_expiracao.strftime('%d/%m/%Y')}")
        
        submitted = st.form_submit_button("✅ Registrar Venda", type="primary")
        
        if submitted:
            if not all([nome, cpf, carro, valor_original > 0]):
                st.error("Por favor, preencha todos os campos obrigatórios (*)")
            else:
                success, message = add_venda(nome, cpf, data_nasc, carro, 
                                           valor_original, percentual)
                if success:
                    st.success(message)
                    st.balloons()
                else:
                    st.error(message)

# BUSCAR CLIENTE
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")
    
    termo_busca = st.text_input("Digite nome ou CPF do cliente:")
    
    if termo_busca:
        resultados = search_vendas(termo_busca)
        
        if not resultados.empty:
            st.success(f"✅ {len(resultados)} cliente(s) encontrado(s)")
            
            display_df = resultados.copy()
            display_df['valor_com_cashback'] = display_df['valor_com_cashback'].apply(lambda x: f"R$ {x:,.2f}")
            display_df['valor_cashback'] = display_df['valor_cashback'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "-")
            display_df['data_compra'] = display_df['data_compra'].dt.strftime('%d/%m/%Y')
            display_df['data_expiracao_cashback'] = display_df['data_expiracao_cashback'].dt.strftime('%d/%m/%Y')
            
            st.dataframe(display_df[['nome_cliente', 'cpf', 'carro_comprado', 
                                    'valor_com_cashback', 'valor_cashback',
                                    'data_compra', 'data_expiracao_cashback']], 
                        use_container_width=True)
        else:
            st.warning("Nenhum cliente encontrado")

# CASHBACKS ATIVOS
elif menu == "💰 Cashbacks Ativos":
    st.header("💰 Cashbacks Ativos (Válidos por 3 meses)")
    
    cashbacks = get_cashbacks_ativos()
    
    if not cashbacks.empty:
        st.success(f"✅ {len(cashbacks)} cashback(s) ativo(s)")
        
        display_df = cashbacks.copy()
        display_df['valor_cashback'] = display_df['valor_cashback'].apply(lambda x: f"R$ {x:,.2f}")
        display_df['data_compra'] = display_df['data_compra'].dt.strftime('%d/%m/%Y')
        display_df['data_expiracao_cashback'] = display_df['data_expiracao_cashback'].dt.strftime('%d/%m/%Y')
        
        def color_status(dias):
            if dias <= 7: return "🔴"
            elif dias <= 15: return "🟡"
            else: return "🟢"
        
        if 'dias_restantes' in display_df.columns:
            display_df['Status'] = display_df['dias_restantes'].apply(color_status)
            display_df['Dias Restantes'] = display_df['dias_restantes']
        
        st.dataframe(display_df[['nome_cliente', 'carro_comprado', 'valor_cashback',
                                'data_expiracao_cashback', 'Status', 'Dias Restantes']], 
                    use_container_width=True)
        
        total = cashbacks['valor_cashback'].sum()
        st.metric("💰 Total em Cashbacks Ativos", f"R$ {total:,.2f}")
    else:
        st.info("✨ Não há cashbacks ativos no momento.")

# RELATÓRIOS
elif menu == "📊 Relatórios":
    st.header("📊 Relatórios Analíticos")
    
    todas_vendas = get_all_vendas()
    
    if not todas_vendas.empty:
        # Vendas por mês
        todas_vendas['mes_ano'] = todas_vendas['data_compra'].dt.strftime('%b/%Y')
        vendas_por_mes = todas_vendas.groupby('mes_ano').agg({
            'id': 'count',
            'valor_com_cashback': 'sum'
        }).reset_index()
        
        vendas_por_mes.columns = ['Mês/Ano', 'Quantidade', 'Valor Total']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📦 Vendas por Mês")
            st.bar_chart(vendas_por_mes.set_index('Mês/Ano')['Quantidade'])
        
        with col2:
            st.subheader("💰 Faturamento por Mês")
            st.line_chart(vendas_por_mes.set_index('Mês/Ano')['Valor Total'])
        
        # Carros mais vendidos
        st.subheader("🚗 Top Modelos")
        vendas_por_modelo = todas_vendas.groupby('carro_comprado').agg({
            'id': 'count',
            'valor_com_cashback': 'sum'
        }).reset_index()
        
        vendas_por_modelo.columns = ['Modelo', 'Vendas', 'Faturamento']
        vendas_por_modelo = vendas_por_modelo.sort_values('Vendas', ascending=False)
        
        st.dataframe(vendas_por_modelo, use_container_width=True)
    else:
        st.info("Ainda não há dados para relatórios")

# Rodapé
st.markdown("---")
st.caption(f"© 2024 Auto Nunes Concessionária • Sistema de Vendas • {datetime.now().strftime('%d/%m/%Y')}")
