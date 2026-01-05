import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# Configuração da página
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

# Título do sistema
st.title("🚗 Sistema de Vendas - Auto Nunes Concessionária")
st.markdown("---")

# Inicializar banco de dados
def init_db():
    conn = sqlite3.connect('vendas_auto_nunes.db')
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

# Chamar função de inicialização
init_db()

# Opções fixas de carros (não podem ser escritas)
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
    {"label": "Sem Cashback", "percentual": 0, "valor": 0},
    {"label": "Cashback 5%", "percentual": 5, "valor": 0.05},
    {"label": "Cashback 10%", "percentual": 10, "valor": 0.10},
    {"label": "Cashback 15%", "percentual": 15, "valor": 0.15},
    {"label": "Cashback 20%", "percentual": 20, "valor": 0.20}
]

# Função para adicionar venda
def add_venda(nome, cpf, data_nasc, carro, valor_original, percentual_cashback):
    conn = sqlite3.connect('vendas_auto_nunes.db')
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
        return True, "Venda registrada com sucesso!"
    except sqlite3.IntegrityError:
        return False, "CPF já cadastrado no sistema!"
    finally:
        conn.close()

# Função para buscar vendas
def search_vendas(termo):
    conn = sqlite3.connect('vendas_auto_nunes.db')
    
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
        df['data_cadastro'] = pd.to_datetime(df['data_cadastro'])
    
    return df

# Função para obter todas as vendas
def get_all_vendas():
    conn = sqlite3.connect('vendas_auto_nunes.db')
    df = pd.read_sql_query('SELECT * FROM vendas ORDER BY data_cadastro DESC', conn)
    conn.close()
    
    # Converter datas
    if not df.empty:
        df['data_nascimento'] = pd.to_datetime(df['data_nascimento'])
        df['data_compra'] = pd.to_datetime(df['data_compra'])
        df['data_expiracao_cashback'] = pd.to_datetime(df['data_expiracao_cashback'])
        df['data_cadastro'] = pd.to_datetime(df['data_cadastro'])
    
    return df

# Função para verificar cashbacks ativos
def get_cashbacks_ativos():
    conn = sqlite3.connect('vendas_auto_nunes.db')
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

# Função para utilizar cashback
def usar_cashback(venda_id, valor_utilizado):
    conn = sqlite3.connect('vendas_auto_nunes.db')
    c = conn.cursor()
    
    try:
        # Registrar utilização
        c.execute('''INSERT INTO uso_cashback (venda_id, valor_utilizado)
                     VALUES (?, ?)''', (venda_id, valor_utilizado))
        
        # Marcar como utilizado se valor total for usado
        c.execute('''UPDATE vendas 
                     SET cashback_utilizado = 1
                     WHERE id = ? AND valor_cashback <= ?''', 
                  (venda_id, valor_utilizado))
        
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

# Função para obter estatísticas
def get_stats():
    conn = sqlite3.connect('vendas_auto_nunes.db')
    
    # Total de vendas
    total_vendas = pd.read_sql_query('SELECT COUNT(*) as total FROM vendas', conn).iloc[0]['total']
    
    # Valor total vendido (com cashback aplicado)
    valor_total = pd.read_sql_query('SELECT SUM(valor_com_cashback) as total FROM vendas', conn).iloc[0]['total']
    valor_total = valor_total if valor_total else 0
    
    # Valor total em cashback concedido
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

# Sidebar para navegação
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
    
    # Gráfico de carros mais vendidos
    if not carros_top.empty:
        st.subheader("🚗 Modelos Mais Vendidos")
        st.bar_chart(carros_top.set_index('carro_comprado'))
    
    # Últimas vendas
    st.subheader("🆕 Últimas Vendas")
    todas_vendas = get_all_vendas()
    if not todas_vendas.empty:
        cols_display = ['nome_cliente', 'carro_comprado', 'valor_com_cashback', 
                       'percentual_cashback', 'data_compra']
        st.dataframe(todas_vendas[cols_display].head(10), use_container_width=True)

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
                                     min_value=datetime(1900, 1, 1),
                                     max_value=datetime.now())
        
        with col2:
            carro = st.selectbox("Carro Comprado *", CARROS_DISPONIVEIS)
            valor_original = st.number_input("Valor do Veículo (R$) *", 
                                           min_value=0.0, 
                                           step=1000.0,
                                           format="%.2f")
            
            # Seleção de cashback
            cashback_opcao = st.selectbox(
                "Cashback *",
                options=OPCOES_CASHBACK,
                format_func=lambda x: x["label"]
            )
            
            percentual = cashback_opcao["percentual"]
            valor_cashback = valor_original * (percentual / 100)
            valor_final = valor_original - valor_cashback
        
        # Resumo da venda
        st.markdown("---")
        st.subheader("📋 Resumo da Venda")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        
        with col_res1:
            st.metric("Valor Original", f"R$ {valor_original:,.2f}")
        
        with col_res2:
            st.metric(f"Cashback ({percentual}%)", f"-R$ {valor_cashback:,.2f}")
        
        with col_res3:
            st.metric("Valor Final", f"R$ {valor_final:,.2f}", 
                     delta=f"-{percentual}%")
        
        # Data de expiração do cashback
        data_expiracao = datetime.now().date() + relativedelta(months=3)
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
    
    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        termo_busca = st.text_input("Digite nome ou CPF do cliente:")
    
    with col_filter:
        tipo_busca = st.selectbox("Filtrar por:", ["Todos", "Com Cashback Ativo", "Cashback Expirado"])
    
    if termo_busca:
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
            display_cols = ['nome_cliente', 'cpf', 'carro_comprado', 
                          'valor_com_cashback', 'percentual_cashback',
                          'valor_cashback', 'data_compra', 'data_expiracao_cashback']
            
            # Formatar valores
            display_df = resultados[display_cols].copy()
            display_df['valor_com_cashback'] = display_df['valor_com_cashback'].apply(lambda x: f"R$ {x:,.2f}")
            display_df['valor_cashback'] = display_df['valor_cashback'].apply(lambda x: f"R$ {x:,.2f}")
            display_df['data_compra'] = display_df['data_compra'].dt.strftime('%d/%m/%Y')
            display_df['data_expiracao_cashback'] = display_df['data_expiracao_cashback'].dt.strftime('%d/%m/%Y')
            
            st.dataframe(display_df, use_container_width=True)
            
            # Opção para usar cashback
            if tipo_busca == "Com Cashback Ativo" and not resultados.empty:
                st.subheader("💰 Utilizar Cashback")
                
                venda_selecionada = st.selectbox(
                    "Selecione o cashback para utilizar:",
                    options=resultados['id'].tolist(),
                    format_func=lambda x: f"Cliente: {resultados[resultados['id']==x]['nome_cliente'].iloc[0]} - Valor: R$ {resultados[resultados['id']==x]['valor_cashback'].iloc[0]:,.2f}"
                )
                
                if venda_selecionada:
                    venda_info = resultados[resultados['id']==venda_selecionada].iloc[0]
                    valor_disponivel = venda_info['valor_cashback']
                    
                    col_uso1, col_uso2 = st.columns(2)
                    with col_uso1:
                        valor_uso = st.number_input("Valor a utilizar (R$)", 
                                                   min_value=0.0,
                                                   max_value=float(valor_disponivel),
                                                   step=100.0,
                                                   format="%.2f")
                    
                    with col_uso2:
                        if st.button("💳 Utilizar Cashback", type="primary"):
                            if usar_cashback(venda_selecionada, valor_uso):
                                st.success(f"Cashback de R$ {valor_uso:,.2f} utilizado com sucesso!")
                                st.rerun()
                            else:
                                st.error("Erro ao utilizar cashback")
        else:
            st.warning("Nenhum cliente encontrado com esses critérios.")

# CASHBACKS ATIVOS
elif menu == "💰 Cashbacks Ativos":
    st.header("💰 Cashbacks Ativos (Válidos por 3 meses)")
    
    cashbacks = get_cashbacks_ativos()
    
    if not cashbacks.empty:
        st.info(f"✅ {len(cashbacks)} cashback(s) ativo(s)")
        
        # Formatar exibição
        display_cols = ['nome_cliente', 'cpf', 'carro_comprado', 
                       'valor_cashback', 'data_compra', 
                       'data_expiracao_cashback', 'dias_restantes']
        
        display_df = cashbacks[display_cols].copy()
        display_df['valor_cashback'] = display_df['valor_cashback'].apply(lambda x: f"R$ {x:,.2f}")
        display_df['data_compra'] = display_df['data_compra'].dt.strftime('%d/%m/%Y')
        display_df['data_expiracao_cashback'] = display_df['data_expiracao_cashback'].dt.strftime('%d/%m/%Y')
        
        # Colorir dias restantes
        def color_dias(valor):
            if valor <= 7:
                return "🔴"
            elif valor <= 15:
                return "🟡"
            else:
                return "🟢"
        
        display_df['status'] = display_df['dias_restantes'].apply(color_dias)
        display_df['dias_restantes'] = display_df['dias_restantes'].apply(lambda x: f"{x} dias")
        
        st.dataframe(display_df, use_container_width=True)
        
        # Resumo por valor
        total_cashback = cashbacks['valor_cashback'].sum()
        st.metric("💰 Total em Cashbacks Ativos", f"R$ {total_cashback:,.2f}")
        
        # Gráfico de expiração
        st.subheader("📅 Expiração dos Cashbacks")
        expiracao_df = cashbacks.copy()
        expiracao_df['mes_expiracao'] = expiracao_df['data_expiracao_cashback'].dt.strftime('%b/%Y')
        expiracao_agrupado = expiracao_df.groupby('mes_expiracao')['valor_cashback'].sum().reset_index()
        
        if not expiracao_agrupado.empty:
            st.bar_chart(expiracao_agrupado.set_index('mes_expiracao'))
    else:
        st.warning("Não há cashbacks ativos no momento.")

# RELATÓRIOS
elif menu == "📊 Relatórios":
    st.header("📊 Relatórios Analíticos")
    
    tab1, tab2, tab3 = st.tabs(["📈 Vendas por Período", "🚗 Vendas por Modelo", "💰 Cashback"])
    
    with tab1:
        st.subheader("Vendas por Período")
        
        todas_vendas = get_all_vendas()
        if not todas_vendas.empty:
            todas_vendas['mes_ano'] = todas_vendas['data_compra'].dt.strftime('%b/%Y')
            vendas_por_mes = todas_vendas.groupby('mes_ano').agg({
                'id': 'count',
                'valor_com_cashback': 'sum'
            }).reset_index()
            
            vendas_por_mes.columns = ['Mês/Ano', 'Quantidade', 'Valor Total']
            
            col_graf1, col_graf2 = st.columns(2)
            
            with col_graf1:
                st.write("📦 Quantidade de Vendas")
                st.bar_chart(vendas_por_mes.set_index('Mês/Ano')['Quantidade'])
            
            with col_graf2:
                st.write("💰 Valor Total")
                st.line_chart(vendas_por_mes.set_index('Mês/Ano')['Valor Total'])
            
            st.dataframe(vendas_por_mes, use_container_width=True)
    
    with tab2:
        st.subheader("Vendas por Modelo")
        
        todas_vendas = get_all_vendas()
        if not todas_vendas.empty:
            vendas_por_modelo = todas_vendas.groupby('carro_comprado').agg({
                'id': 'count',
                'valor_com_cashback': 'sum',
                'valor_cashback': 'sum'
            }).reset_index()
            
            vendas_por_modelo.columns = ['Modelo', 'Quantidade', 'Valor Vendido', 'Cashback Concedido']
            vendas_por_modelo = vendas_por_modelo.sort_values('Quantidade', ascending=False)
            
            col_mod1, col_mod2 = st.columns(2)
            
            with col_mod1:
                st.write("🚗 Modelos Mais Vendidos")
                st.bar_chart(vendas_por_modelo.set_index('Modelo')['Quantidade'].head(10))
            
            with col_mod2:
                st.write("🏆 Top 5 em Valor")
                top5_valor = vendas_por_modelo.nlargest(5, 'Valor Vendido')
                st.bar_chart(top5_valor.set_index('Modelo')['Valor Vendido'])
            
            st.dataframe(vendas_por_modelo, use_container_width=True)
    
    with tab3:
        st.subheader("Análise de Cashback")
        
        todas_vendas = get_all_vendas()
        if not todas_vendas.empty:
            # Cashback utilizado vs não utilizado
            cashback_status = todas_vendas.groupby('cashback_utilizado').agg({
                'id': 'count',
                'valor_cashback': 'sum'
            }).reset_index()
            
            cashback_status['Status'] = cashback_status['cashback_utilizado'].apply(
                lambda x: 'Utilizado' if x == 1 else 'Disponível/Expirado'
            )
            
            col_cash1, col_cash2 = st.columns(2)
            
            with col_cash1:
                st.write("📊 Status do Cashback")
                st.bar_chart(cashback_status.set_index('Status')['valor_cashback'])
            
            with col_cash2:
                st.write("🎯 Distribuição por Percentual")
                
                cashback_percentual = todas_vendas.groupby('percentual_cashback').agg({
                    'id': 'count',
                    'valor_cashback': 'sum'
                }).reset_index()
                
                cashback_percentual.columns = ['Percentual', 'Quantidade', 'Valor Total']
                cashback_percentual['Percentual'] = cashback_percentual['Percentual'].apply(lambda x: f"{x}%")
                
                st.bar_chart(cashback_percentual.set_index('Percentual')['Valor Total'])
            
            # Estatísticas
            total_cashback = todas_vendas['valor_cashback'].sum()
            cashback_utilizado = todas_vendas[todas_vendas['cashback_utilizado']==1]['valor_cashback'].sum()
            utilizacao_percent = (cashback_utilizado / total_cashback * 100) if total_cashback > 0 else 0
            
            st.metric("💰 Total Cashback Concedido", f"R$ {total_cashback:,.2f}")
            st.metric("💳 Cashback Utilizado", f"R$ {cashback_utilizado:,.2f}", 
                     f"{utilizacao_percent:.1f}% do total")

# Rodapé
st.markdown("---")
st.caption("Sistema de Vendas Auto Nunes © 2024 | Cashback válido por 3 meses a partir da data da compra")
