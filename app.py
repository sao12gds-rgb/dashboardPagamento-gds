import streamlit as st
import pandas as pd
import json

st.set_page_config(page_title="Dashboard GDS Logística", layout="wide")

st.title("📊 Dashboard de Pagamento - GDS Logística")

try:
    # Tentar carregar credenciais do Streamlit Secrets
    import gspread
    from google.oauth2.service_account import Credentials
    
    # Tenta pegar as credenciais (formato JSON direto)
    creds_dict = st.secrets.get("gcp_service_account")
    
    if creds_dict:
        st.success("✅ Conectado ao Google Sheets!")
        
        # Conectar
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # ID da planilha
        ID_PLANILHA = "17LU-Z0xjxPaJ_3gnUd79NvzpF3P3hKTHBTIROZXbv2M"
        
        # Carregar dados
        workbook = client.open_by_key(ID_PLANILHA)
        df_lancamentos = pd.DataFrame(workbook.worksheet("LANCAMENTOS").get_all_records())
        
        # Sidebar - Filtros
        with st.sidebar:
            st.header("🔧 Filtros")
            meses = sorted(df_lancamentos['MES_REFERENCIA'].unique())
            mes = st.selectbox("Mês:", meses)
            
            quinzenas = sorted(df_lancamentos[df_lancamentos['MES_REFERENCIA'] == mes]['QUINZENA'].unique())
            quinzena = st.selectbox("Quinzena:", quinzenas)
        
        # Filtrar
        df_filtrado = df_lancamentos[
            (df_lancamentos['MES_REFERENCIA'] == mes) &
            (df_lancamentos['QUINZENA'] == quinzena)
        ]
        
        # Métricas
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
        
        # Tabela
        st.subheader(f"Dados: {mes} - {quinzena}")
        st.dataframe(df_filtrado[['NOME_ENTREGADOR', 'DATA', 'TIPO_LANCAMENTO', 'VALOR_TOTAL_LINHA']], use_container_width=True, hide_index=True)
        
    else:
        raise Exception("Credenciais não encontradas")
        
except Exception as e:
    st.warning("⚠️ Usando dados de exemplo (Credenciais não configuradas)")
    
    # Dados de exemplo
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
    
    1. **Clique em Settings** ⚙️
    2. **Vá em Secrets**
    3. **Cole isto no campo:**
    
    ```
    gcp_service_account = {"type": "service_account", "project_id": "recibos-whatsapp-492118", "private_key_id": "6c709636b4f99332f711d8e217c3383795999820", "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCw/IXrZtcSU7As\nW58p4uQ/oF2o4yi92FFPbCE/s0KDwqvubT026rDd4i+syGVR7vjC1ZOEKTBT5Vnm\n5ubddqCUSpEpvuoz2YkcZJeCx+9IShHwJhOhxGa3v64bd08c/NRtCckwlgPVf+5Z\nqIqiMrAKmgq+2g0aNtJ7DUPWzCE3mYAt1LXSZgPJeqqs2NwkmCEcv3uxUBFxDOhv\nsahDBxeLjFMUDF4LHsHKfWGUgrR0g/sqeVa9IjemaS/Zgz6dXrxgofZdezEaVJu5\nWnezQm4cn7x65IPaXbI8x0LE9BPwcNkTt/1TsuSh6fCjPHrR/J86OzJau+YgnR8T\nbOn7E9JBAgMBAAECggEABjVlkUNzSf5LkNLJ+5MtBJpgjrshQ7+h4pJdfDmSnMKo\ne12zpwiGmdIEcCA7hatHaLZLTXiQbHEAPVxePuiZa3pOK1O6LYV1DNzuf7T5zORk\nSrNbPvJ/0/RSbD48NT0dSpHsT9sDWWr6doS2EEiM6mJK/DTz/rZrnctyVMemZqfZ\n6keJRvPTpDkcA37SfHszfYnwrFzFNwItg4O1QynYcUkdSR8I1V9PnwGB1p4ShvZP\nezweLWUFwDqncIo3KCWCKSD1N2mO6vBb7SY53uYnGHOazcVUF1C8RwmSbBKoKtOK\nH7DTvad4R8OGiwTF8aBD5P1eXasyPfTmjMR0ZoluEQKBgQDZY4vYsWh+lA42eZgO\nSv1jtewR1OTYbEiiYROfNByrj/6Fj5npcqJQUFC5nfGfZ8LmwHJbMIAXYuGWA5x0\nDY1Cgj7HhQbjrIjEZ8yc9VzpslkeidfAGusIysM15RH1DC1lqIVdSAaiYZ7TIJ8a\nKR4w4OzoWZT3Ugyyiug5B9HlbQKBgQDQa+sndUXVYIt+thxkz4GTyOEymKq9qhTy\nPiPoADSD6Kxcd9Qd6vt/XG3Ql9DCiJi4fMd3NIfxIjCr2mTgWLxla5HNJd6biw0b\n2vJK3C6QtT/oSI7zjs5ZvfmksBqpP9P+BvxZK/EVBBK8kp1FOO+h/PcPbcUQTpqc\nrLUcaBXfpQKBgEVNi/7ICBUaZDGPsB8WXxOToq/InDA2zS0fH59IgL9dB3pS3nFi\n/0X1ZNbX+HimHqdrwMk7fAp4low5mH4S9+61EQiQazLYBT4ADWYYfsdt+SVYMnTm\n3/kMkxEydvgVKr/W6rVjSeIolvad1rsDUsGoYz5rmKcD/FJLIF9WE989AoGBAIwZ\nDr++R8vPktUA6wMkrPA/JolRL+w/6MaQ2Kf5g1Nr0nhxn+bgbl/FLJf7hLtPAIF6\ndsX9TKfdGKRcMFTRsQnnjeE9ZG5fwNcJjLafXLmu7B9irpyvUKvoVGfMbI96NTDb\nV0NFk09SJpoVX5wJUqMrnJMFcWKtw6YvPaqzmIh1AoGACU4/wHCTSMfBBRXNBUJP\nvF0VcTpuKnu6SVteC2/Mb1tKQuAnb3tGL/dgmuietX9N9qwJJs3R7lPvmTXxNLQK\nYrWu1Sy8Ojwkk4X1U2uksCP8nnWThMBuFN1R9hByIUI09bc6Qxqn8uUEQQH6LIAo\nPXlSQlT5558/hcZCRQwg8ro=\n-----END PRIVATE KEY-----\n", "client_email": "dashboard-gds@recibos-whatsapp-492118.iam.gserviceaccount.com", "client_id": "110229877449265412143", "auth_uri": "https://accounts.google.com/o/oauth2/auth", "token_uri": "https://oauth2.googleapis.com/token", "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs", "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dashboard-gds%40recibos-whatsapp-492118.iam.gserviceaccount.com", "universe_domain": "googleapis.com"}
    ```
    
    4. **Clique em Save**
    5. **O dashboard vai carregar os dados reais!**
    """)
