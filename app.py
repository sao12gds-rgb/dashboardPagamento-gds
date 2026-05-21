import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import json

# Configuração da página
st.set_page_config(page_title="Dashboard GDS Logística", layout="wide")

# ============= CONEXÃO COM GOOGLE SHEETS =============
@st.cache_resource
def conectar_sheets():
    """Conecta ao Google Sheets usando credenciais do Streamlit Secrets"""
    try:
        # Pega as credenciais do arquivo secrets.toml
        creds_dict = st.secrets.get("gcp_service_account")
        
        if not creds_dict:
            st.error("❌ Credenciais não configuradas. Vá em Settings → Secrets no painel Streamlit Cloud")
            return None
        
        # Criar credenciais a partir do dicionário
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Erro ao conectar com Google Sheets: {str(e)}")
        return None

# ============= CARREGAR DADOS =============
@st.cache_data(ttl=300)
def carregar_dados(id_planilha):
    """Carrega dados das abas LANCAMENTOS e CADASTRO"""
    try:
        client = conectar_sheets()
        if not client:
            return None, None
        
        workbook = client.open_by_key(id_planilha)
        
        # Aba LANCAMENTOS
        df_lancamentos = pd.DataFrame(workbook.worksheet("LANCAMENTOS").get_all_records())
        
        # Aba CADASTRO
        df_cadastro = pd.DataFrame(workbook.worksheet("CADASTRO").get_all_records())
        
        return df_lancamentos, df_cadastro
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        return None, None

# ============= GERAR RECIBO EM HTML =============
def gerar_recibo_html(entregador, df_entregador, cnpj=""):
    """Gera um recibo em HTML para impressão"""
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    # Monta a tabela de lançamentos
    linhas_html = ""
    for _, row in df_entregador.iterrows():
        valor = row.get('VALOR_TOTAL_LINHA', 0)
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.')) if ',' in str(valor) else float(valor)
        linhas_html += f"""
        <tr>
            <td>{row.get('DATA', '')}</td>
            <td>{row.get('TIPO_LANCAMENTO', '')}</td>
            <td style="text-align: right;">R$ {valor:.2f}</td>
        </tr>
        """
    
    total = 0
    for _, row in df_entregador.iterrows():
        valor = row.get('VALOR_TOTAL_LINHA', 0)
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.')) if ',' in str(valor) else float(valor)
        total += valor
    
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; border: 1px solid #333; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .header h2 {{ margin: 5px 0; }}
            .info-row {{ display: flex; justify-content: space-between; margin: 5px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f0f0f0; }}
            .total {{ font-weight: bold; font-size: 18px; text-align: right; margin: 20px 0; }}
            .signature {{ margin-top: 40px; text-align: center; }}
            .line {{ border-top: 1px solid #333; width: 300px; margin: 50px auto 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>GDS LOGÍSTICA</h2>
                <p>RECIBO DE PAGAMENTO</p>
            </div>
            
            <div class="info-row">
                <span><strong>Entregador:</strong> {entregador}</span>
                <span><strong>Data:</strong> {data_hora}</span>
            </div>
            <div class="info-row">
                <span><strong>CNPJ:</strong> {cnpj}</span>
            </div>
            
            <table>
                <tr>
                    <th>Data</th>
                    <th>Tipo</th>
                    <th style="text-align: right;">Valor</th>
                </tr>
                {linhas_html}
            </table>
            
            <div class="total">
                TOTAL A PAGAR: R$ {total:.2f}
            </div>
            
            <div class="signature">
                <div class="line"></div>
                <p>Assinatura do Entregador</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

# ============= MAIN =============
def main():
    # ID da planilha (use a planilha de teste)
    ID_PLANILHA = "17LU-Z0xjxPaJ_3gnUd79NvzpF3P3hKTHBTIROZXbv2M"
    
    st.title("📊 Dashboard de Pagamento - GDS Logística")
    
    # Carregar dados
    df_lancamentos, df_cadastro = carregar_dados(ID_PLANILHA)
    
    if df_lancamentos is None or df_cadastro is None:
        st.warning("⚠️ Aguardando configuração das credenciais Google Cloud...")
        st.info("""
        ### 🔑 Como configurar as credenciais:
        
        1. Vá em **Settings** (engrenagem 🔧)
        2. Clique em **"Secrets"**
        3. Cole o JSON das suas credenciais do Google Cloud
        4. Clique em **"Save"**
        5. O app vai recarregar automaticamente!
        """)
        return
    
    # ============= SIDEBAR - FILTROS =============
    with st.sidebar:
        st.header("🔧 Filtros")
        
        # Filtro Mês
        try:
            meses_unicos = sorted(df_lancamentos['MES_REFERENCIA'].unique())
            mes_selecionado = st.selectbox("Mês:", meses_unicos, index=len(meses_unicos)-1)
        except Exception as e:
            st.error(f"Erro ao filtrar mês: {e}")
            return
        
        # Filtro Quinzena
        try:
            quinzenas_unicos = sorted(df_lancamentos['QUINZENA'].unique())
            quinzena_selecionada = st.selectbox("Quinzena:", quinzenas_unicos)
        except Exception as e:
            st.error(f"Erro ao filtrar quinzena: {e}")
            return
        
        # Botão Atualizar
        if st.button("🔄 Atualizar Dados", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
    
    # Filtrar dados
    df_filtrado = df_lancamentos[
        (df_lancamentos['MES_REFERENCIA'] == mes_selecionado) &
        (df_lancamentos['QUINZENA'] == quinzena_selecionada)
    ]
    
    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return
    
    # ============= METRICS =============
    col1, col2, col3, col4 = st.columns(4)
    
    total_pagar = 0
    for _, row in df_filtrado.iterrows():
        valor = row.get('VALOR_TOTAL_LINHA', 0)
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.')) if ',' in str(valor) else float(valor)
        total_pagar += valor
    
    total_entregas = len(df_filtrado[df_filtrado['TIPO_LANCAMENTO'] == 'ENTREGA'])
    
    total_adicionais = 0
    for _, row in df_filtrado[df_filtrado['TIPO_LANCAMENTO'].isin(['ADICIONAL', 'ROTA MALA'])].iterrows():
        valor = row.get('VALOR_TOTAL_LINHA', 0)
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.')) if ',' in str(valor) else float(valor)
        total_adicionais += valor
    
    entregadores_ativos = df_filtrado['NOME_ENTREGADOR'].nunique()
    
    with col1:
        st.metric("💰 Total a Pagar", f"R$ {total_pagar:.2f}")
    with col2:
        st.metric("📦 Entregas", total_entregas)
    with col3:
        st.metric("➕ Adicionais", f"R$ {total_adicionais:.2f}")
    with col4:
        st.metric("👥 Entregadores", entregadores_ativos)
    
    # ============= ABAS =============
    tab1, tab2 = st.tabs(["📋 Resumo por Entregador", "🧾 Recibos"])
    
    with tab1:
        st.subheader(f"Resumo - {mes_selecionado} ({quinzena_selecionada})")
        
        # Cards por entregador
        entregadores_filtrados = sorted(df_filtrado['NOME_ENTREGADOR'].unique())
        
        cols = st.columns(3)
        for idx, entregador in enumerate(entregadores_filtrados):
            df_entregador = df_filtrado[df_filtrado['NOME_ENTREGADOR'] == entregador]
            
            total = 0
            for _, row in df_entregador.iterrows():
                valor = row.get('VALOR_TOTAL_LINHA', 0)
                if isinstance(valor, str):
                    valor = float(valor.replace(',', '.')) if ',' in str(valor) else float(valor)
                total += valor
            
            qtd_lanc = len(df_entregador)
            
            with cols[idx % 3]:
                st.write(f"### {entregador}")
                st.write(f"**Total:** R$ {total:.2f}")
                st.write(f"**Lançamentos:** {qtd_lanc}")
                
                # Detalhes
                with st.expander("Ver detalhes"):
                    st.dataframe(
                        df_entregador[['DATA', 'TIPO_LANCAMENTO', 'VALOR_TOTAL_LINHA']],
                        use_container_width=True,
                        hide_index=True
                    )
    
    with tab2:
        st.subheader("🧾 Gerar Recibos")
        
        # Seletor de entregador para recibo
        entregadores_filtrados = sorted(df_filtrado['NOME_ENTREGADOR'].unique())
        entregador_recibo = st.selectbox(
            "Selecione o entregador:",
            entregadores_filtrados,
            key="select_recibo"
        )
        
        if entregador_recibo:
            df_recibo = df_filtrado[df_filtrado['NOME_ENTREGADOR'] == entregador_recibo]
            
            # Pega CNPJ do cadastro
            cnpj = ""
            if not df_cadastro.empty:
                # Tenta diferentes nomes de coluna
                nome_col = None
                for col in df_cadastro.columns:
                    if 'NOME' in col.upper():
                        nome_col = col
                        break
                
                if nome_col:
                    cadastro_entregador = df_cadastro[df_cadastro[nome_col] == entregador_recibo]
                    if not cadastro_entregador.empty:
                        for col in cadastro_entregador.columns:
                            if 'CNPJ' in col.upper():
                                cnpj = cadastro_entregador.iloc[0][col]
                                break
            
            # Gera recibo
            html_recibo = gerar_recibo_html(entregador_recibo, df_recibo, cnpj)
            
            st.components.v1.html(html_recibo, height=800)

if __name__ == "__main__":
    main()
