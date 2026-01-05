import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# ========== CONFIGURAÇÃO DE PERSISTÊNCIA CRÍTICA ==========
# Streamlit Cloud perde dados da pasta raiz, mas mantém na pasta /data/
os.makedirs('/data', exist_ok=True)  # Pasta persistente do Streamlit Cloud
os.makedirs('data', exist_ok=True)   # Pasta local para backup

def get_db_connection():
    """Conexão com banco em pasta PERSISTENTE"""
    # Tenta primeiro a pasta persistente do Streamlit Cloud
    db_path = '/data/vendas_auto_nunes.db'
    if not os.path.exists('/data'):
        # Fallback para pasta local
        db_path = 'data/vendas_auto_nunes.db'
    
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # Ativar WAL mode para melhor performance e prevenção de corrupção
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    return conn

# ========== CONFIGURAÇÃO DA PÁGINA ==========
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Sistema de Vendas - Auto Nunes Concessionária")
st.markdown("---")

# ========== INICIALIZAR BANCO ==========
def init_db():
    """Cria tabelas se não existirem"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabela principal de vendas
    c.execute('''CREATE TABLE IF NOT EXISTS vendas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tabela de histórico de cashback usado
    c.execute('''CREATE TABLE IF NOT EXISTS uso_cashback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL,
        valor_utilizado REAL NOT NULL,
        data_utilizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (venda_id) REFERENCES vendas (id) ON DELETE CASCADE
    )''')
    
    # Índices para performance
    c.execute('CREATE INDEX IF NOT EXISTS idx_cpf ON vendas(cpf)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_nome ON vendas(nome_cliente)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_expiracao ON vendas(data_expiracao_cashback)')
    
    conn.commit()
    conn.close()

# Inicializar banco
init_db()

# ========== DADOS FIXOS ==========
CARROS_DISPONIVEIS = [
    "Onix", "Onix Plus", "Tracker", "Spin", "Captiva",
    "Blazer", "Blazer Elétrica", "S10", "Montana"
]

OPCOES_CASHBACK = [
    {"label": "Sem Cashback", "percentual": 0},
    {"label": "Cashback 5%", "percentual": 5},
    {"label": "Cashback 10%", "percentual": 10},
    {"label": "Cashback 15%", "percentual": 15},
    {"label": "Cashback 20%", "percentual": 20}
]

# ========== FUNÇÕES COM PERSISTÊNCIA GARANTIDA ==========
def add_venda(nome, cpf, data_nasc, carro, valor_original, percentual_cashback):
    """Adiciona venda com validação de CPF único"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Calcular valores
    valor_cashback = valor_original * (percentual_cashback / 100)
    valor_com_cashback = valor_original - valor_cashback
    data_compra = datetime.now().date()
    data_expiracao = data_compra + relativedelta(months=3)
    
    try:
        # Verificar se CPF já existe
        c.execute('SELECT cpf FROM vendas WHERE cpf = ?', (cpf,))
        if c.fetchone():
            return False, "❌ CPF já cadastrado!"
        
        # Inserir nova venda
        c.execute('''INSERT INTO vendas 
                    (nome_cliente, cpf, data_nascimento, carro_comprado,
                     valor_original, percentual_cashback, valor_com_cashback,
                     valor_cashback, data_compra, data_expiracao_cashback)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                 (nome, cpf, data_nasc, carro, valor_original,
                  percentual_cashback, valor_com_cashback, valor_cashback,
                  data_compra, data_expiracao))
        
        conn.commit()
        
        # Fazer backup dos dados periodicamente
        fazer_backup_dados()
        
        return True, f"✅ Venda registrada! Cashback válido até {data_expiracao.strftime('%d/%m/%Y')}"
    
    except Exception as e:
        return False, f"❌ Erro ao salvar: {str(e)}"
    finally:
        conn.close()

@st.cache_data(ttl=60, show_spinner=False)
def search_vendas(termo=""):
    """Busca vendas com cache para performance"""
    conn = get_db_connection()
    
    if termo:
        query = '''SELECT * FROM vendas 
                   WHERE nome_cliente LIKE ? OR cpf LIKE ?
                   ORDER BY data_cadastro DESC'''
        params = (f'%{termo}%', f'%{termo}%')
    else:
        query = 'SELECT * FROM vendas ORDER BY data_cadastro DESC'
        params = ()
    
    try:
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            # Converter datas
            date_cols = ['data_nascimento', 'data_compra', 'data_expiracao_cashback', 'data_cadastro']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
        
        return df
    finally:
        conn.close()

@st.cache_data(ttl=30, show_spinner=False)
def get_cashbacks_ativos():
    """Busca cashbacks ativos com cache"""
    conn = get_db_connection()
    hoje = datetime.now().date()
    
    query = '''SELECT *, 
               (data_expiracao_cashback - ?) as dias_restantes
               FROM vendas 
               WHERE data_expiracao_cashback >= ? 
               AND cashback_utilizado = 0
               AND valor_cashback > 0
               ORDER BY data_expiracao_cashback'''
    
    try:
        df = pd.read_sql_query(query, conn, params=(hoje, hoje))
        
        if not df.empty:
            date_cols = ['data_nascimento', 'data_compra', 'data_expiracao_cashback', 'data_cadastro']
            for col in date_cols:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col])
            
            # Calcular dias restantes corretamente
            df['dias_restantes'] = (df['data_expiracao_cashback'].dt.date - hoje).dt.days
        
        return df
    finally:
        conn.close()

def usar_cashback(venda_id, valor_utilizado):
    """Registra utilização de cashback"""
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # Verificar valor disponível
        c.execute('SELECT valor_cashback, cashback_utilizado FROM vendas WHERE id = ?', (venda_id,))
        resultado = c.fetchone()
        
        if not resultado:
            return False, "Venda não encontrada"
        
        valor_disponivel, ja_utilizado = resultado
        
        if ja_utilizado:
            return False, "Cashback já foi utilizado"
        
        if valor_utilizado > valor_disponivel:
            return False, f"Valor máximo disponível: R$ {valor_disponivel:,.2f}"
        
        # Registrar uso
        c.execute('INSERT INTO uso_cashback (venda_id, valor_utilizado) VALUES (?, ?)',
                 (venda_id, valor_utilizado))
        
        # Atualizar status se usou tudo
        if valor_utilizado >= valor_disponivel:
            c.execute('UPDATE vendas SET cashback_utilizado = 1 WHERE id = ?', (venda_id,))
        
        conn.commit()
        fazer_backup_dados()  # Backup após alteração
        return True, "✅ Cashback utilizado com sucesso!"
    
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def fazer_backup_dados():
    """Faz backup dos dados periodicamente"""
    try:
        conn = get_db_connection()
        backup_path = 'data/vendas_backup.db'
        
        # Conectar ao banco de backup
        backup_conn = sqlite3.connect(backup_path)
        
        # Copiar dados
        conn.backup(backup_conn)
        
        backup_conn.close()
        conn.close()
    except:
        pass  # Silencia erros de backup

@st.cache_data(ttl=30, show_spinner=False)
def get_stats():
    """Estatísticas com cache"""
    conn = get_db_connection()
    hoje = datetime.now().date()
    
    try:
        # Total de vendas
        total_vendas = pd.read_sql_query('SELECT COUNT(*) as total FROM vendas', conn).iloc[0]['total']
        
        # Valores
        valores = pd.read_sql_query(
            'SELECT SUM(valor_com_cashback) as vendas, SUM(valor_cashback) as cashback FROM vendas', 
            conn
        )
        valor_total = valores.iloc[0]['vendas'] or 0
        cashback_total = valores.iloc[0]['cashback'] or 0
        
        # Carros mais vendidos
        carros_top = pd.read_sql_query(
            '''SELECT carro_comprado, COUNT(*) as quantidade 
               FROM vendas 
               GROUP BY carro_comprado 
               ORDER BY quantidade DESC''', 
            conn
        )
        
        # Cashbacks ativos
        cashbacks_ativos = pd.read_sql_query(
            '''SELECT COUNT(*) as ativos FROM vendas 
               WHERE data_expiracao_cashback >= ? 
               AND cashback_utilizado = 0
               AND valor_cashback > 0''', 
            conn, params=(hoje,)
        ).iloc[0]['ativos']
        
        return total_vendas, valor_total, cashback_total, carros_top, cashbacks_ativos
    
    finally:
        conn.close()

# ========== INTERFACE DO USUÁRIO ==========
st.sidebar.title("🚗 Menu Auto Nunes")
menu = st.sidebar.radio(
    "Selecione uma opção:",
    ["🏠 Dashboard", "➕ Nova Venda", "🔍 Buscar Cliente", "💰 Cashbacks Ativos"]
)

st.sidebar.markdown("---")
st.sidebar.info("**Concessionária Chevrolet**\n\nCashback válido por 3 meses")
st.sidebar.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# DASHBOARD
if menu == "🏠 Dashboard":
    st.header("📊 Dashboard de Vendas")
    
    # Obter estatísticas
    total_vendas, valor_total, cashback_total, carros_top, cashbacks_ativos = get_stats()
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Vendas", total_vendas)
    
    with col2:
        st.metric("Valor Total Vendido", f"R$ {valor_total:,.2f}")
    
    with col3:
        st.metric("Cashback Concedido", f"R$ {cashback_total:,.2f}")
    
    with col4:
        st.metric("Cashbacks Ativos", cashbacks_ativos)
    
    # Carros mais vendidos
    if not carros_top.empty:
        st.subheader("🚗 Modelos Mais Vendidos")
        st.bar_chart(carros_top.set_index('carro_comprado'))
    
    # Últimas vendas
    st.subheader("🆕 Últimas Vendas")
    todas_vendas = search_vendas()
    if not todas_vendas.empty:
        cols_display = ['nome_cliente', 'carro_comprado', 'valor_com_cashback', 
                       'percentual_cashback', 'data_compra']
        st.dataframe(todas_vendas[cols_display].head(10), use_container_width=True)
    
    # Backup status
    if os.path.exists('data/vendas_backup.db'):
        backup_size = os.path.getsize('data/vendas_backup.db') / 1024
        st.sidebar.success(f"✅ Backup ativo: {backup_size:.1f} KB")

# NOVA VENDA
elif menu == "➕ Nova Venda":
    st.header("➕ Registrar Nova Venda")
    
    with st.form("form_venda", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome Completo do Cliente *", max_chars=100)
            cpf = st.text_input("CPF *", max_chars=14, 
                               placeholder="000.000.000-00",
                               help="Apenas números, será formatado automaticamente")
            data_nasc = st.date_input("Data de Nascimento *", 
                                     max_value=datetime.now().date())
        
        with col2:
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
        
        # Resumo
        st.markdown("---")
        st.subheader("📋 Resumo da Venda")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            st.metric("Valor Original", f"R$ {valor_original:,.2f}")
        
        with col_res2:
            if percentual > 0:
                st.metric(f"Cashback ({percentual}%)", f"-R$ {valor_cashback:,.2f}")
            else:
                st.metric("Cashback", "Não aplicado")
        
        with col_res3:
            st.metric("Valor Final", f"R$ {valor_final:,.2f}", 
                     delta=f"-{percentual}%" if percentual > 0 else None)
        
        # Data de expiração
        data_expiracao = datetime.now().date() + relativedelta(months=3)
        if percentual > 0:
            st.info(f"💰 **Cashback válido até:** {data_expiracao.strftime('%d/%m/%Y')}")
        
        submitted = st.form_submit_button("✅ Registrar Venda", type="primary", use_container_width=True)
        
        if submitted:
            if not all([nome, cpf, carro, valor_original > 0]):
                st.error("Por favor, preencha todos os campos obrigatórios (*)")
            else:
                # Formatar CPF
                cpf_limpo = ''.join(filter(str.isdigit, cpf))
                if len(cpf_limpo) != 11:
                    st.error("CPF deve ter 11 dígitos")
                else:
                    with st.spinner("Salvando venda..."):
                        success, message = add_venda(nome, cpf_limpo, data_nasc, carro, 
                                                   valor_original, percentual)
                        if success:
                            st.success(message)
                            st.balloons()
                            st.cache_data.clear()  # Limpa cache para atualizar dados
                        else:
                            st.error(message)

# BUSCAR CLIENTE
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")
    
    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        termo_busca = st.text_input("Digite nome ou CPF do cliente:")
    
    with col_filter:
        tipo_busca = st.selectbox("Filtrar por:", ["Todos", "Com Cashback Ativo", "Cashback Expirado"])
    
    if termo_busca:
        with st.spinner("Buscando..."):
            resultados = search_vendas(termo_busca)
        
        if not resultados.empty:
            st.success(f"✅ {len(resultados)} cliente(s) encontrado(s)")
            
            # Aplicar filtros
            hoje = datetime.now().date()
            
            if tipo_busca == "Com Cashback Ativo":
                resultados = resultados[
                    (resultados['data_expiracao_cashback'].dt.date >= hoje) & 
                    (resultados['cashback_utilizado'] == 0) &
                    (resultados['valor_cashback'] > 0)
                ]
            elif tipo_busca == "Cashback Expirado":
                resultados = resultados[
                    (resultados['data_expiracao_cashback'].dt.date < hoje) | 
                    (resultados['cashback_utilizado'] == 1)
                ]
            
            # Formatar exibição
            display_df = resultados.copy()
            
            # Formatar colunas
            if 'valor_com_cashback' in display_df.columns:
                display_df['Valor Final'] = display_df['valor_com_cashback'].apply(lambda x: f"R$ {x:,.2f}")
            
            if 'valor_cashback' in display_df.columns:
                display_df['Cashback'] = display_df['valor_cashback'].apply(lambda x: f"R$ {x:,.2f}" if x > 0 else "-")
            
            if 'data_compra' in display_df.columns:
                display_df['Data Compra'] = display_df['data_compra'].dt.strftime('%d/%m/%Y')
            
            if 'data_expiracao_cashback' in display_df.columns:
                display_df['Cashback Válido Até'] = display_df['data_expiracao_cashback'].dt.strftime('%d/%m/%Y')
            
            # Colunas para exibir
            display_cols = []
            if 'nome_cliente' in display_df.columns:
                display_cols.append('nome_cliente')
            if 'cpf' in display_df.columns:
                display_cols.append('cpf')
            if 'carro_comprado' in display_df.columns:
                display_cols.append('carro_comprado')
            if 'Valor Final' in display_df.columns:
                display_cols.append('Valor Final')
            if 'Cashback' in display_df.columns:
                display_cols.append('Cashback')
            if 'Data Compra' in display_df.columns:
                display_cols.append('Data Compra')
            if 'Cashback Válido Até' in display_df.columns:
                display_cols.append('Cashback Válido Até')
            
            if display_cols:
                st.dataframe(display_df[display_cols], use_container_width=True)
            
            # Opção para usar cashback
            if tipo_busca == "Com Cashback Ativo" and not resultados.empty:
                st.subheader("💰 Utilizar Cashback")
                
                venda_selecionada = st.selectbox(
                    "Selecione o cashback para utilizar:",
                    options=resultados['id'].tolist(),
                    format_func=lambda x: f"{resultados[resultados['id']==x]['nome_cliente'].iloc[0]} - R$ {resultados[resultados['id']==x]['valor_cashback'].iloc[0]:,.2f}"
                )
                
                if venda_selecionada:
                    venda_info = resultados[resultados['id']==venda_selecionada].iloc[0]
                    valor_disponivel = venda_info['valor_cashback']
                    
                    col_uso1, col_uso2 = st.columns(2)
                    with col_uso1:
                        valor_uso = st.number_input("Valor a utilizar (R$)", 
                                                   min_value=0.0,
                                                   max_value=float(valor_disponivel),
                                                   value=float(valor_disponivel),
                                                   step=100.0,
                                                   format="%.2f")
                    
                    with col_uso2:
                        st.write("")  # Espaço
                        st.write("")  # Espaço
                        if st.button("💳 Utilizar Cashback", type="primary", use_container_width=True):
                            with st.spinner("Processando..."):
                                sucesso, mensagem = usar_cashback(venda_selecionada, valor_uso)
                                if sucesso:
                                    st.success(mensagem)
                                    st.cache_data.clear()  # Limpa cache
                                    st.rerun()
                                else:
                                    st.error(mensagem)
        else:
            st.warning("Nenhum cliente encontrado com esses critérios.")

# CASHBACKS ATIVOS
elif menu == "💰 Cashbacks Ativos":
    st.header("💰 Cashbacks Ativos (Válidos por 3 meses)")
    
    with st.spinner("Carregando..."):
        cashbacks = get_cashbacks_ativos()
    
    if not cashbacks.empty:
        st.success(f"✅ {len(cashbacks)} cashback(s) ativo(s)")
        
        # Formatar exibição
        display_df = cashbacks.copy()
        
        # Formatar valores
        if 'valor_cashback' in display_df.columns:
            display_df['Valor Cashback'] = display_df['valor_cashback'].apply(lambda x: f"R$ {x:,.2f}")
        
        if 'data_compra' in display_df.columns:
            display_df['Data da Compra'] = display_df['data_compra'].dt.strftime('%d/%m/%Y')
        
        if 'data_expiracao_cashback' in display_df.columns:
            display_df['Válido Até'] = display_df['data_expiracao_cashback'].dt.strftime('%d/%m/%Y')
        
        # Status de expiração
        if 'dias_restantes' in display_df.columns:
            def get_status_color(dias):
                if dias <= 7:
                    return "🔴 Crítico"
                elif dias <= 15:
                    return "🟡 Atenção"
                else:
                    return "🟢 Normal"
            
            display_df['Status'] = display_df['dias_restantes'].apply(get_status_color)
            display_df['Dias Restantes'] = display_df['dias_restantes']
        
        # Colunas para exibir
        display_cols = []
        if 'nome_cliente' in display_df.columns:
            display_cols.append('nome_cliente')
        if 'cpf' in display_df.columns:
            display_cols.append('cpf')
        if 'carro_comprado' in display_df.columns:
            display_cols.append('carro_comprado')
        if 'Valor Cashback' in display_df.columns:
            display_cols.append('Valor Cashback')
        if 'Data da Compra' in display_df.columns:
            display_cols.append('Data da Compra')
        if 'Válido Até' in display_df.columns:
            display_cols.append('Válido Até')
        if 'Status' in display_df.columns:
            display_cols.append('Status')
        if 'Dias Restantes' in display_df.columns:
            display_cols.append('Dias Restantes')
        
        if display_cols:
            st.dataframe(display_df[display_cols], use_container_width=True)
        
        # Resumo
        total_cashback = cashbacks['valor_cashback'].sum()
        st.metric("💰 Total Disponível em Cashbacks", f"R$ {total_cashback:,.2f}")
        
    else:
        st.info("✨ Não há cashbacks ativos no momento.")

# Rodapé
st.markdown("---")
st.caption(f"© 2024 Auto Nunes Concessionária • Sistema online • Dados persistentes • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# Verificação de banco de dados
try:
    conn = get_db_connection()
    count = pd.read_sql_query('SELECT COUNT(*) as total FROM vendas', conn).iloc[0]['total']
    conn.close()
    st.sidebar.metric("Registros no banco", count)
except:
    st.sidebar.warning("Banco de dados em inicialização")
