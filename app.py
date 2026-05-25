import streamlit as st
import pandas as pd
st.set_page_config(page_title="Dashboard GDS Logística", layout="wide")
st.title("📊 Dashboard de Pagamento - GDS Logística")
try:
    import gspread
    from google.oauth2.service_account import Credentials
    
    # Tenta pegar as credenciais do Streamlit Secrets
    creds_dict = st.secrets.get("gcp_service_account")
    
    if creds_dict:
        st.success("✅ Conectado ao Google Sheets!")
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        ID_PLANILHA = "17LU-Z0xjxPaJ_3gnUd79NvzpF3P3hKTHBTIROZXbv2M"
        
        workbook = client.open_by_key(ID_PLANILHA)
        df_lancamentos = pd.DataFrame(workbook.worksheet("LANCAMENTOS").get_all_records())
        
        # 🔧 AQUI: Extrai apenas o mês (antes do "/")
        df_lancamentos['MES_REFERENCIA'] = df_lancamentos['MES_REFERENCIA'].str.split('/').str[0]
        
        with st.sidebar:
            st.header("🔧 Filtros")
            meses = sorted(df_lancamentos['MES_REFERENCIA'].unique())
            mes = st.selectbox("Mês:", meses)
            
            quinzenas = sorted(df_lancamentos[df_lancamentos['MES_REFERENCIA'] == mes]['QUINZENA'].unique())
            quinzena = st.selectbox("Quinzena:", quinzenas)
        
        df_filtrado = df_lancamentos[
            (df_lancamentos['MES_REFERENCIA'] == mes) &
            (df_lancamentos['QUINZENA'] == quinzena)
        ]
        
        col1, col2, col3, col4 = st.columns(4)
        
        total = float(df_filtrado['VALOR_TOTAL_LINHA'].sum()) if len(df_filtrado) > 0 else 0
        entregas = len(df_filtrado[df_filtrado['TIPO_LANCAMENTO'] == 'ENTREGA'])
        entregadores = df_filtrado['NOME_ENTREGADOR'].nunique()
        lancamentos = len(df_filtrado)
        
        with col1:
            st.metric("💰 Total", f"R$ {total:.2f}")
        with col2:
            st.metric("📦 Entregas", entregas)
        with col3:
            st.metric("👥 Entregadores", entregadores)
        with col4:
            st.metric("📋 Lançamentos", lancamentos)
        
        st.subheader(f"Dados: {mes} - {quinzena}")
        st.dataframe(df_filtrado[['NOME_ENTREGADOR', 'DATA', 'TIPO_LANCAMENTO', 'VALOR_TOTAL_LINHA']], use_container_width=True, hide_index=True)
        
    else:
        raise Exception("Credenciais não encontradas")
        
except Exception as e:
    st.warning("⚠️ Usando dados de exemplo (Credenciais não configuradas)")
    
    dados_exemplo = {
        'Entregador': ['João Silva', 'Maria Santos', 'Pedro Costa', 'João Silva', 'Maria Santos'],
        'Data': ['2026-05-15', '2026-05-16', '2026-05-17', '2026-05-18', '2026-05-19'],
        'Tipo': ['ENTREGA', 'ENTREGA', 'ROTA MALA', 'ADICIONAL', 'ENTREGA'],
        'Valor': [150.00, 200.00, 100.00, 50.00, 180.00]
    }
    
    df = pd.DataFrame(dados_exemplo)
    
    with st.sidebar:
        st.header("🔧 Filtros")
        entregador_selecionado = st.selectbox("Entregador:", df['Entregador'].unique())
    
    df_filtrado = df[df['Entregador'] == entregador_selecionado]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total", f"R$ {df_filtrado['Valor'].sum():.2f}")
    with col2:
        st.metric("📦 Entregas", len(df_filtrado[df_filtrado['Tipo'] == 'ENTREGA']))
    with col3:
        st.metric("📋 Lançamentos", len(df_filtrado))
    
    st.subheader(f"Lançamentos de {entregador_selecionado}")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    
    st.info("""
    ### 🔑 Para conectar com Google Sheets:
    
    1. Clique em **Settings** ⚙️
    2. Vá em **Secrets**
    3. Cole sua credencial JSON do Google Cloud
    4. Clique em **Save**
    5. O dashboard vai carregar!
    """)
