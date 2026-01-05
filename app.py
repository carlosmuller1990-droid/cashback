import streamlit as st
import pandas as pd
import os
import requests
import base64
from datetime import date

# =============================
# CONFIGURAÇÕES
# =============================
st.set_page_config(page_title="Cashback - Auto Nunes", layout="wide")

GITHUB_REPO = "SEU_USUARIO/SEU_REPOSITORIO"
CAMINHO_GIT = "backups/backup_vendas.xlsx"
ARQUIVO_LOCAL = "backup_vendas.xlsx"

# =============================
# FUNÇÕES GITHUB
# =============================
def baixar_backup_github():
    if os.path.exists(ARQUIVO_LOCAL):
        return

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CAMINHO_GIT}"
    headers = {
        "Authorization": f"token {st.secrets['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github.v3.raw"
    }

    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        with open(ARQUIVO_LOCAL, "wb") as f:
            f.write(r.content)

def salvar_backup_github():
    with open(ARQUIVO_LOCAL, "rb") as f:
        conteudo = base64.b64encode(f.read()).decode()

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{CAMINHO_GIT}"
    headers = {"Authorization": f"token {st.secrets['GITHUB_TOKEN']}"}

    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": "Backup automático de vendas",
        "content": conteudo,
        "sha": sha
    }

    requests.put(url, json=payload, headers=headers)

# =============================
# INICIALIZAÇÃO
# =============================
baixar_backup_github()

if os.path.exists(ARQUIVO_LOCAL):
    df = pd.read_excel(ARQUIVO_LOCAL)
else:
    df = pd.DataFrame(columns=[
        "Cliente", "Modelo", "Valor_Venda", "Cashback",
        "Data_Venda"
    ])

# =============================
# TÍTULO
# =============================
st.title("💰 Controle de Cashback – Auto Nunes")

# =============================
# CADASTRO
# =============================
with st.form("cadastro"):
    st.subheader("➕ Registrar Venda")

    col1, col2, col3 = st.columns(3)

    cliente = col1.text_input("Cliente")
    modelo = col2.selectbox("Modelo", ["Onix", "Onix Plus", "Tracker", "Montana"])
    valor = col3.number_input("Valor da Venda", min_value=0.0, step=100.0)

    cashback = st.number_input("Cashback (R$)", min_value=0.0, step=50.0)
    data_venda = st.date_input("Data da Venda", value=date.today())

    salvar = st.form_submit_button("Salvar Venda")

    if salvar and cliente:
        novo = pd.DataFrame([{
            "Cliente": cliente,
            "Modelo": modelo,
            "Valor_Venda": valor,
            "Cashback": cashback,
            "Data_Venda": data_venda
        }])

        df = pd.concat([df, novo], ignore_index=True)
        df.to_excel(ARQUIVO_LOCAL, index=False)
        salvar_backup_github()
        st.success("Venda registrada com sucesso!")

# =============================
# PESQUISA DE CLIENTE
# =============================
st.subheader("🔎 Pesquisar Cliente")

busca = st.text_input("Digite o nome do cliente")

if busca:
    resultado = df[df["Cliente"].str.contains(busca, case=False, na=False)]
else:
    resultado = df

st.dataframe(resultado, use_container_width=True)

# =============================
# RELATÓRIO DE CARROS
# =============================
st.subheader("🚗 Quantidade de Carros Vendidos")

relatorio_carros = df.groupby("Modelo").size().reset_index(name="Quantidade")
st.table(relatorio_carros)

# =============================
# EXPORTAR EXCEL
# =============================
st.subheader("📥 Exportar Relatório")

def gerar_excel(dados):
    caminho = "relatorio_vendas.xlsx"
    dados.to_excel(caminho, index=False)
    return caminho

if st.button("Gerar Excel"):
    arquivo = gerar_excel(df)
    with open(arquivo, "rb") as f:
        st.download_button(
            "⬇ Baixar Excel",
            f,
            file_name="relatorio_vendas.xlsx"
        )
