import streamlit as st
import pandas as pd
from datetime import date
import os
from io import BytesIO

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Sistema de Vendas - Auto Nunes",
    page_icon="🚗",
    layout="wide"
)

ARQUIVO_DADOS = "backup_vendas.csv"

# =============================
# INICIALIZAÇÃO DOS DADOS
# =============================
if os.path.exists(ARQUIVO_DADOS):
    df = pd.read_csv(ARQUIVO_DADOS, dtype={"CPF": str})
else:
    df = pd.DataFrame(columns=[
        "Nome",
        "CPF",
        "Veiculo",
        "Valor_Venda",
        "Percentual_Cashback",
        "Valor_Cashback",
        "Data_Venda"
    ])
    df.to_csv(ARQUIVO_DADOS, index=False)

# =============================
# TÍTULO
# =============================
st.title("🚗 Sistema de Vendas - Auto Nunes")
st.markdown("---")

# =============================
# MENU LATERAL
# =============================
st.sidebar.title("📌 Menu")

menu = st.sidebar.radio(
    "Selecione:",
    [
        "📊 Dashboard de Vendas",
        "➕ Nova Venda",
        "🔍 Buscar Cliente",
        "📄 Relatórios"
    ]
)

# =============================
# DASHBOARD
# =============================
if menu == "📊 Dashboard de Vendas":
    st.header("📊 Dashboard de Vendas")

    total_vendas = len(df)
    valor_total = df["Valor_Venda"].astype(float).sum()
    cashback_total = df["Valor_Cashback"].astype(float).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Vendas", total_vendas)
    c2.metric("Valor Total Vendido", f"R$ {valor_total:,.2f}")
    c3.metric("Cashback Concedido", f"R$ {cashback_total:,.2f}")

    st.markdown("---")
    st.subheader("🚗 Quantidade de Carros Vendidos")

    if not df.empty:
        carros = df.groupby("Veiculo").size().reset_index(name="Quantidade")
        st.bar_chart(carros.set_index("Veiculo"))
        st.dataframe(carros, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada até o momento.")

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
                ["Onix", "Onix Plus", "Tracker", "Spin", "Montana", "S10", "Blazer"]
            )
            data_venda = st.date_input("Data da Venda", value=date.today())

        with col2:
            valor_venda = st.number_input(
                "Valor da Venda (R$)", min_value=0.0, step=1000.0
            )
            percentual = st.selectbox("Percentual de Cashback", [0, 5, 10, 15, 20])

        valor_cashback = valor_venda * (percentual / 100)

        st.markdown("### 📋 Resumo")
        r1, r2, r3 = st.columns(3)
        r1.metric("Valor da Venda", f"R$ {valor_venda:,.2f}")
        r2.metric("Cashback", f"R$ {valor_cashback:,.2f}")
        r3.metric("Percentual", f"{percentual}%")

        salvar = st.form_submit_button("Salvar Venda")

        if salvar:
            if nome and cpf and valor_venda > 0:
                nova_venda = {
                    "Nome": nome,
                    "CPF": cpf,
                    "Veiculo": veiculo,
                    "Valor_Venda": valor_venda,
                    "Percentual_Cashback": percentual,
                    "Valor_Cashback": valor_cashback,
                    "Data_Venda": data_venda
                }

                # Adiciona nova venda ao DataFrame
                df = pd.concat([df, pd.DataFrame([nova_venda])], ignore_index=True)

                # Salva backup local
                df.to_csv(ARQUIVO_DADOS, index=False)

                st.success("Venda registrada com sucesso!")

                # =============================
                # BACKUP AUTOMÁTICO NO GITHUB
                # =============================
                try:
                    from github import Github
                    import base64

                    # Token do Secrets
                    TOKEN = st.secrets["GITHUB_TOKEN"]
                    REPO = "carlosmuller1990-droid/backup-vendas-auto"  # SEU USUÁRIO + NOME DO REPO
                    ARQUIVO = ARQUIVO_DADOS

                    # Conecta ao GitHub
                    g = Github(TOKEN)
                    repo = g.get_repo(REPO)

                    # Lê CSV local
                    with open(ARQUIVO, "rb") as f:
                        conteudo = f.read()

                    # Converte para base64
                    conteudo_base64 = base64.b64encode(conteudo).decode()

                    # Cria ou atualiza arquivo no GitHub
                    try:
                        arquivo_github = repo.get_contents(ARQUIVO)
                        repo.update_file(ARQUIVO, "Atualizando backup", conteudo_base64, arquivo_github.sha)
                    except:
                        repo.create_file(ARQUIVO, "Criando backup inicial", conteudo_base64)

                    st.info("Backup enviado para o GitHub com sucesso!")

                except Exception as e:
                    st.error(f"Erro ao enviar backup para GitHub: {e}")

            else:
                st.error("Preencha todos os campos obrigatórios (*)")

# =============================
# BUSCAR CLIENTE
# =============================
elif menu == "🔍 Buscar Cliente":
    st.header("🔍 Buscar Cliente")

    busca = st.text_input("Digite o nome ou CPF do cliente")

    if busca:
        resultado = df[
            df["Nome"].str.contains(busca, case=False, na=False) |
            df["CPF"].str.contains(busca, case=False, na=False)
        ]
    else:
        resultado = df

    st.dataframe(resultado, use_container_width=True)

# =============================
# RELATÓRIOS (EXCEL)
# =============================
elif menu == "📄 Relatórios":
    st.header("📄 Relatórios")

    st.subheader("📊 Vendas Organizadas")

    relatorio = df[[
        "Nome",
        "CPF",
        "Veiculo",
        "Valor_Venda",
        "Percentual_Cashback",
        "Valor_Cashback",
        "Data_Venda"
    ]]

    st.dataframe(relatorio, use_container_width=True)

    # Gerar Excel em memória
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        relatorio.to_excel(writer, index=False, sheet_name="Vendas")

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
st.caption(
    "Sistema desenvolvido por Carlos Jr - Supervisor BDC"
)
