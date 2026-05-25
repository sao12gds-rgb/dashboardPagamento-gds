import streamlit as st
import pandas as pd
from fpdf import FPDF
from io import BytesIO
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Dashboard GDS Logística", layout="wide")
st.title("📊 Dashboard de Pagamento - GDS Logística")

try:
    creds_dict = st.secrets.get("gcp_service_account")
    
    if creds_dict:
        st.success("✅ Conectado ao Google Sheets!")
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        ID_PLANILHA = "17LU-Z0xjxPaJ_3gnUd79NvzpF3P3hKTHBTIROZXbv2M"
        workbook = client.open_by_key(ID_PLANILHA)
        
        # Lê CADASTRO
        df_cadastro = pd.DataFrame(workbook.worksheet("CADASTRO").get_all_records())
        
        # Lê LANCAMENTOS
        df_lancamentos = pd.DataFrame(workbook.worksheet("LANCAMENTOS").get_all_records())
        df_lancamentos['MES_REFERENCIA'] = df_lancamentos['MES_REFERENCIA'].str.split('/').str[0]
        
        # Merge CNPJ
        df_lancamentos = df_lancamentos.merge(
            df_cadastro[['NOME_ENTREGADOR', 'CNPJ']], 
            on='NOME_ENTREGADOR', 
            how='left'
        )
        
        # Filtros
        with st.sidebar:
            st.header("🔧 Filtros")
            meses = sorted(df_lancamentos['MES_REFERENCIA'].unique())
            mes = st.selectbox("Mês:", meses)
            
            quinzenas = sorted(df_lancamentos[df_lancamentos['MES_REFERENCIA'] == mes]['QUINZENA'].unique())
            quinzena = st.selectbox("Quinzena:", quinzenas)
            
            entregadores = sorted(df_lancamentos[
                (df_lancamentos['MES_REFERENCIA'] == mes) &
                (df_lancamentos['QUINZENA'] == quinzena)
            ]['NOME_ENTREGADOR'].unique())
            entregador = st.selectbox("Entregador:", entregadores)
        
        df_filtrado = df_lancamentos[
            (df_lancamentos['MES_REFERENCIA'] == mes) &
            (df_lancamentos['QUINZENA'] == quinzena) &
            (df_lancamentos['NOME_ENTREGADOR'] == entregador)
        ]
        
        if len(df_filtrado) > 0:
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            
            total = float(df_filtrado['VALOR_TOTAL_LINHA'].sum())
            entregas = len(df_filtrado[df_filtrado['TIPO_LANCAMENTO'] == 'ENTREGA'])
            adicionais = float(df_filtrado['VALOR_ADICIONAL'].sum()) if 'VALOR_ADICIONAL' in df_filtrado.columns else 0
            descontos = float(df_filtrado['VALOR_DESCONTO'].sum()) if 'VALOR_DESCONTO' in df_filtrado.columns else 0
            
            with col1:
                st.metric("💰 Total", f"R$ {total:.2f}")
            with col2:
                st.metric("📦 Entregas", entregas)
            with col3:
                st.metric("➕ Adicionais", f"R$ {adicionais:.2f}")
            with col4:
                st.metric("➖ Descontos", f"R$ {descontos:.2f}")
            
            # Tabela de lançamentos
            st.subheader(f"Lançamentos de {entregador}")
            colunas_exibir = ['DATA', 'CEP', 'TIPO_LANCAMENTO', 'VALOR_ADICIONAL', 'VALOR_DESCONTO', 'VALOR_TOTAL_LINHA']
            colunas_disponiveis = [col for col in colunas_exibir if col in df_filtrado.columns]
            st.dataframe(df_filtrado[colunas_disponiveis], use_container_width=True, hide_index=True)
            
            # Resumo por CEP
            st.subheader("📍 Resumo por CEP")
            resumo_cep = df_filtrado[df_filtrado['TIPO_LANCAMENTO'] == 'ENTREGA'].groupby('CEP').size().reset_index(name='QTD_ENTREGAS')
            st.dataframe(resumo_cep, use_container_width=True, hide_index=True)
            
            # Função para gerar PDF
            def gerar_recibo_pdf(df, entregador_nome, cnpj, mes_ref, quinzena_ref):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 16)
                
                # Título
                pdf.cell(0, 10, "RECIBO DE PAGAMENTO", ln=True, align="C")
                pdf.ln(5)
                
                # Informações
                pdf.set_font("Arial", "B", 10)
                pdf.cell(40, 8, "ENTREGADOR:", 0)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, entregador_nome, ln=True)
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(40, 8, "CNPJ:", 0)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, str(cnpj) if pd.notna(cnpj) else "N/A", ln=True)
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(40, 8, "PERÍODO:", 0)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 8, f"{mes_ref} - {quinzena_ref}", ln=True)
                
                pdf.ln(3)
                
                # Resumo por CEP
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, "RESUMO OPERACIONAL", ln=True)
                
                resumo = df[df['TIPO_LANCAMENTO'] == 'ENTREGA'].groupby('CEP').size().reset_index(name='QTD')
                pdf.set_font("Arial", "B", 9)
                pdf.cell(80, 7, "CEP", 1)
                pdf.cell(40, 7, "QTD ENTREGAS", 1, ln=True)
                
                pdf.set_font("Arial", "", 9)
                for _, row in resumo.iterrows():
                    pdf.cell(80, 7, str(row['CEP']), 1)
                    pdf.cell(40, 7, str(int(row['QTD'])), 1, ln=True)
                
                pdf.ln(3)
                
                # Resumo Financeiro
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, "RESUMO FINANCEIRO", ln=True)
                
                total_valor = df['VALOR_TOTAL_LINHA'].sum()
                total_adicionais = df['VALOR_ADICIONAL'].sum() if 'VALOR_ADICIONAL' in df.columns else 0
                total_descontos = df['VALOR_DESCONTO'].sum() if 'VALOR_DESCONTO' in df.columns else 0
                
                pdf.set_font("Arial", "", 10)
                pdf.cell(120, 8, "TOTAL POR CEP:", 0)
                pdf.cell(0, 8, f"R$ {total_valor:.2f}", ln=True, align="R")
                
                pdf.cell(120, 8, "ADICIONAIS:", 0)
                pdf.cell(0, 8, f"R$ {total_adicionais:.2f}", ln=True, align="R")
                
                pdf.cell(120, 8, "DESCONTOS:", 0)
                pdf.cell(0, 8, f"R$ {total_descontos:.2f}", ln=True, align="R")
                
                pdf.set_font("Arial", "B", 10)
                pdf.cell(120, 8, "TOTAL A RECEBER:", 0)
                pdf.cell(0, 8, f"R$ {total_valor:.2f}", ln=True, align="R")
                
                pdf.ln(5)
                
                # Assinatura
                pdf.set_font("Arial", "", 9)
                pdf.cell(90, 8, "ASSINATURA", 0, align="C")
                pdf.cell(0, 8, "DATA", ln=True, align="C")
                
                pdf.cell(90, 20, "_________________", 0, align="C")
                pdf.cell(0, 20, "_________________", ln=True, align="C")
                
                pdf_bytes = pdf.output()
                return BytesIO(pdf_bytes)
            
            # Botão para gerar PDF
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📄 Gerar Recibo PDF", use_container_width=True):
                    cnpj = df_filtrado['CNPJ'].iloc[0] if 'CNPJ' in df_filtrado.columns else "N/A"
                    pdf_buffer = gerar_recibo_pdf(df_filtrado, entregador, cnpj, mes, quinzena)
                    
                    st.download_button(
                        label="⬇️ Baixar Recibo em PDF",
                        data=pdf_buffer,
                        file_name=f"Recibo_{entregador.replace(' ', '_')}_{mes}_{quinzena}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
        else:
            st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
    else:
        raise Exception("Credenciais não encontradas")
        
except Exception as e:
    st.error(f"❌ Erro: {str(e)}")
