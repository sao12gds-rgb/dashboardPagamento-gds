import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# Configuração da página
st.set_page_config(
    page_title="GDS - Controle de Entregadores",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Função para conectar ao Google Sheets
@st.cache_resource
def conectar_sheets():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return None

# Função para carregar dados
@st.cache_data(ttl=300)
def carregar_dados(id_planilha):
    try:
        client = conectar_sheets()
        if client is None:
            return None, None
        
        sheet = client.open_by_key(id_planilha)
        
        # Carregar LANCAMENTOS
        lancamentos = sheet.worksheet("LANCAMENTOS")
        dados_lancamentos = lancamentos.get_all_records()
        df = pd.DataFrame(dados_lancamentos)
        
        # Carregar CADASTRO para CNPJ
        cadastro_sheet = sheet.worksheet("CADASTRO")
        dados_cadastro = cadastro_sheet.get_all_records()
        
        cadastro_dict = {}
        for row in dados_cadastro:
            nome = str(row.get('', '')).strip()
            cnpj = str(row.get('', '')).strip()
            if nome and cnpj:
                cadastro_dict[nome] = cnpj
        
        return df, cadastro_dict
    
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return None, None

# SIDEBAR
st.sidebar.title("GDS")
st.sidebar.markdown("---")

# ID da planilha
ID_PLANILHA = "17LU-Z0xjxPaJ_3gnUd79NvzpF3P3hKTHBTIROZXbv2M"

# Carregar dados
df, cadastro = carregar_dados(ID_PLANILHA)

if df is None:
    st.error("❌ Configure credenciais no Streamlit Cloud")
    st.stop()

# Filtros
st.sidebar.subheader("Filtros")

meses_disponiveis = sorted(df['MES_REFERENCIA'].unique().tolist()) if 'MES_REFERENCIA' in df.columns else []
mes_selecionado = st.sidebar.selectbox("Mês", meses_disponiveis if meses_disponiveis else ["Sem dados"])

quinzenas_disponiveis = ["Todas"] + sorted(df['QUINZENA'].unique().tolist()) if 'QUINZENA' in df.columns else ["Todas"]
quinzena_selecionada = st.sidebar.selectbox("Quinzena", quinzenas_disponiveis)

entregadores_disponiveis = ["Todos"] + sorted(df['NOME_ENTREGADOR'].unique().tolist()) if 'NOME_ENTREGADOR' in df.columns else ["Todos"]
entregador_selecionado = st.sidebar.selectbox("Entregador", entregadores_disponiveis)

st.sidebar.markdown("---")

col_btn1, col_btn2 = st.sidebar.columns([1, 1])
with col_btn1:
    btn_recibos = st.button("📄 Recibos", use_container_width=True)
with col_btn2:
    btn_atualizar = st.button("🔄 Atualizar", use_container_width=True)

if btn_atualizar:
    st.cache_data.clear()
    st.success("✅ Atualizado!")

st.sidebar.markdown("---")
st.sidebar.info("""
**ℹ️ Info:**
- Dashboard ao vivo
- Dados sincronizados
- Atualiza a cada 5 min
""")

# Filtrar dados
df_filtered = df.copy()

if 'MES_REFERENCIA' in df_filtered.columns and mes_selecionado:
    df_filtered = df_filtered[df_filtered['MES_REFERENCIA'] == mes_selecionado]

if quinzena_selecionada != "Todas" and 'QUINZENA' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['QUINZENA'] == quinzena_selecionada]

if entregador_selecionado != "Todos" and 'NOME_ENTREGADOR' in df_filtered.columns:
    df_filtered = df_filtered[df_filtered['NOME_ENTREGADOR'] == entregador_selecionado]

# MAIN CONTENT
st.title("💳 Controle de Entregadores")
st.markdown("Dashboard de pagamentos — GDS Logística")

# Métricas
try:
    total_pagar = (
        df_filtered['VALOR_TOTAL_LINHA'].sum() + 
        df_filtered['VALOR_ADICIONAL'].sum() - 
        df_filtered['VALOR_DESCONTO'].sum()
    )
    total_entregas = df_filtered['QTD_ENTREGAS'].sum()
    total_adicionais = df_filtered['VALOR_ADICIONAL'].sum()
    entregadores_ativos = df_filtered['NOME_ENTREGADOR'].nunique()
except:
    total_pagar = total_entregas = total_adicionais = entregadores_ativos = 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total a Pagar", f"R$ {total_pagar:,.2f}".replace(",", "."))

with col2:
    st.metric("Entregas", f"{int(total_entregas)}")

with col3:
    st.metric("Adicionais", f"R$ {total_adicionais:,.2f}".replace(",", "."))

with col4:
    st.metric("Entregadores", f"{int(entregadores_ativos)}")

st.markdown("---")

# Resumo
st.subheader("📊 Detalhes por Entregador")

try:
    resumo = df_filtered.groupby('NOME_ENTREGADOR').agg({
        'QTD_ENTREGAS': 'sum',
        'VALOR_TOTAL_LINHA': 'sum',
        'VALOR_ADICIONAL': 'sum',
        'CEP': lambda x: ', '.join(x.dropna().astype(str).unique())
    }).reset_index()
    
    resumo['TOTAL'] = resumo['VALOR_TOTAL_LINHA'] + resumo['VALOR_ADICIONAL']
    resumo = resumo.sort_values('TOTAL', ascending=False)
    
    cols = st.columns(3)
    
    for idx, (_, row) in enumerate(resumo.iterrows()):
        with cols[idx % 3]:
            st.markdown(f"""
            <div style="background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 12px;">
                <div style="font-size: 15px; font-weight: 600; margin-bottom: 12px;">{str(row['NOME_ENTREGADOR']).split()[0]}</div>
                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                    <span style="color: #818792;">Entregas</span>
                    <span style="font-weight: 600;">{int(row['QTD_ENTREGAS'])}</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                    <span style="color: #818792;">Valor</span>
                    <span style="font-weight: 600;">R$ {row['VALOR_TOTAL_LINHA']:,.2f}</span>
                </div>
                {f'<div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;"><span style="color: #818792;">Adicionais</span><span style="font-weight: 600; color: #00a86b;">+R$ {row["VALOR_ADICIONAL"]:,.2f}</span></div>' if row['VALOR_ADICIONAL'] > 0 else ''}
                <div style="border-top: 1px solid #e0e0e0; padding-top: 8px; margin-top: 8px; font-size: 14px; font-weight: bold; color: #1f77b4; display: flex; justify-content: space-between;">
                    <span>TOTAL</span>
                    <span>R$ {row['TOTAL']:,.2f}</span>
                </div>
                <div style="font-size: 11px; color: #818792; margin-top: 8px;">CEPs: {row['CEP']}</div>
            </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.warning(f"Erro ao processar: {e}")

st.markdown("---")

# Recibos
if btn_recibos:
    st.subheader("📄 Recibos de Pagamento")
    
    for _, row in resumo.iterrows():
        cnpj = cadastro.get(row['NOME_ENTREGADOR'], 'SEM CNPJ')
        total = row['VALOR_TOTAL_LINHA'] + row['VALOR_ADICIONAL']
        
        st.markdown(f"""
        <div style="border: 1.5px solid #333; padding: 24px; margin-bottom: 30px; font-family: 'Courier New', monospace; font-size: 12px; background: white;">
            <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 12px; margin-bottom: 16px; font-weight: bold; font-size: 13px;">
                RECIBO DE PAGAMENTO<br>
                1ª QUINZENA — {mes_selecionado}
            </div>
            
            <div style="margin-bottom: 12px;">
                <div><b>ENTREGADOR:</b> {row['NOME_ENTREGADOR']} — {cnpj}</div>
                <div><b>PERÍODO:</b> 01/04 a 15/04/2026</div>
            </div>
            
            <div style="border-top: 1px solid #ddd; border-bottom: 2px solid #333; padding: 12px 0; margin: 12px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span>TOTAL POR CEP</span>
                    <span><b>R$ {row['VALOR_TOTAL_LINHA']:,.2f}</b></span>
                </div>
                {f'<div style="display: flex; justify-content: space-between; margin-bottom: 8px;"><span>ADICIONAIS</span><span><b>R$ {row["VALOR_ADICIONAL"]:,.2f}</b></span></div>' if row['VALOR_ADICIONAL'] > 0 else ''}
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; font-weight: bold; color: #1f77b4;">
                    <span>TOTAL A RECEBER</span>
                    <span>R$ {total:,.2f}</span>
                </div>
            </div>
            
            <div style="font-size: 11px; color: #666; margin: 12px 0;">
                <b>Resumo:</b> {row['CEP']}
            </div>
            
            <div style="margin-top: 20px; border-top: 1px solid #ddd; padding-top: 12px;">
                <div style="margin-bottom: 16px;">
                    <b>Assinatura:</b> _________________________________________________
                </div>
                <div>
                    <b>Data:</b> ______ / ______ / ______
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.info("💡 Clique em ⋮ no navegador e selecione 'Imprimir' ou 'Salvar como PDF'")