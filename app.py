import streamlit as st

# Configuração da página
st.set_page_config(page_title="Dashboard GDS Logística", layout="wide")

st.title("📊 Dashboard de Pagamento - GDS Logística")

st.info("""
### 🔑 Configure as Credenciais do Google Cloud

Para usar o dashboard, você precisa adicionar suas credenciais:

1. Clique na **engrenagem ⚙️** (Settings) no canto superior direito
2. Selecione **"Secrets"**
3. Cole seu arquivo JSON das credenciais do Google Cloud
4. O app vai recarregar automaticamente!

---

### 📋 Passos para gerar as credenciais:

1. Acesse: https://console.cloud.google.com
2. Crie um novo projeto
3. Ative a **Google Sheets API**
4. Crie uma **Service Account**
5. Gere uma **chave JSON**
6. Cole aqui em Secrets

---

**Depois que configurar, seu dashboard estará pronto!** 🎉
""")

try:
    import pandas as pd
    import gspread
    from google.oauth2.service_account import Credentials
    
    # Tentar conectar
    creds_dict = st.secrets.get("gcp_service_account")
    
    if creds_dict:
        st.success("✅ Credenciais detectadas! Carregando dashboard...")
        
        # Conectar ao Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # ID da planilha
        ID_PLANILHA = "17LU-Z0xjxPaJ_3gnUd79NvzpF3P3hKTHBTIROZXbv2M"
        
        # Carregar dados
        workbook = client.open_by_key(ID_PLANILHA)
        df_lancamentos = pd.DataFrame(workbook.worksheet("LANCAMENTOS").get_all_records())
        df_cadastro = pd.DataFrame(workbook.worksheet("CADASTRO").get_all_records())
        
        st.success("✅ Dados carregados com sucesso!")
        
        # ============= SIDEBAR - FILTROS =============
        with st.sidebar:
            st.header("🔧 Filtros")
            
            meses_unicos = sorted(df_lancamentos['MES_REFERENCIA'].unique())
            mes_selecionado = st.selectbox("Mês:", meses_unicos, index=len(meses_unicos)-1)
            
            quinzenas_unicos = sorted(df_lancamentos['QUINZENA'].unique())
            quinzena_selecionada = st.selectbox("Quinzena:", quinzenas_unicos)
            
            if st.button("🔄 Atualizar Dados", use_container_width=True):
                st.rerun()
        
        # Filtrar dados
        df_filtrado = df_lancamentos[
            (df_lancamentos['MES_REFERENCIA'] == mes_selecionado) &
            (df_lancamentos['QUINZENA'] == quinzena_selecionada)
        ]
        
        # ============= METRICS =============
        col1, col2, col3, col4 = st.columns(4)
        
        total_pagar = df_filtrado['VALOR_TOTAL_LINHA'].sum()
        total_entregas = len(df_filtrado[df_filtrado['TIPO_LANCAMENTO'] == 'ENTREGA'])
        total_adicionais = df_filtrado[df_filtrado['TIPO_LANCAMENTO'].isin(['ADICIONAL', 'ROTA MALA'])]['VALOR_TOTAL_LINHA'].sum()
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
            
            entregadores_filtrados = sorted(df_filtrado['NOME_ENTREGADOR'].unique())
            
            cols = st.columns(3)
            for idx, entregador in enumerate(entregadores_filtrados):
                df_entregador = df_filtrado[df_filtrado['NOME_ENTREGADOR'] == entregador]
                total = df_entregador['VALOR_TOTAL_LINHA'].sum()
                qtd_lanc = len(df_entregador)
                
                with cols[idx % 3]:
                    st.write(f"### {entregador}")
                    st.write(f"**Total:** R$ {total:.2f}")
                    st.write(f"**Lançamentos:** {qtd_lanc}")
                    
                    with st.expander("Ver detalhes"):
                        st.dataframe(
                            df_entregador[['DATA', 'TIPO_LANCAMENTO', 'VALOR_TOTAL_LINHA']],
                            use_container_width=True,
                            hide_index=True
                        )
        
        with tab2:
            st.subheader("🧾 Gerar Recibos")
            
            entregadores_filtrados = sorted(df_filtrado['NOME_ENTREGADOR'].unique())
            entregador_recibo = st.selectbox(
                "Selecione o entregador:",
                entregadores_filtrados,
                key="select_recibo"
            )
            
            if entregador_recibo:
                df_recibo = df_filtrado[df_filtrado['NOME_ENTREGADOR'] == entregador_recibo]
                total = df_recibo['VALOR_TOTAL_LINHA'].sum()
                
                st.write(f"### {entregador_recibo}")
                st.write(f"**Total a Pagar:** R$ {total:.2f}")
                
                st.dataframe(df_recibo[['DATA', 'TIPO_LANCAMENTO', 'VALOR_TOTAL_LINHA']], use_container_width=True)

except Exception as e:
    st.warning(f"⚠️ Aguardando configuração das credenciais...")
    st.info("""
    As credenciais do Google Cloud não foram detectadas.
    
    **Próximos passos:**
    1. Clique em **Settings** ⚙️
    2. Vá em **Secrets**
    3. Cole seu JSON das credenciais do Google Cloud
    4. Clique em **Save**
    5. O app vai recarregar!
    """)
