import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from io import BytesIO
from datetime import datetime
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
        
        # Lê CADASTRO (entregadores com CNPJ)
        df_cadastro = pd.DataFrame(workbook.worksheet("CADASTRO").get_all_records())
        
        # Lê LANCAMENTOS
        df_lancamentos = pd.DataFrame(workbook.worksheet("LANCAMENTOS").get_all_records())
        df_lancamentos['MES_REFERENCIA'] = df_lancamentos['MES_REFERENCIA'].str.split('/').str[0]
        
        # Merge para adicionar CNPJ
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
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, 
                                       rightMargin=0.4*inch, leftMargin=0.4*inch, 
                                       topMargin=0.4*inch, bottomMargin=0.4*inch)
                elements = []
                styles = getSampleStyleSheet()
                
                # Título
                title = Paragraph("<b>RECIBO DE PAGAMENTO</b>", styles['Heading1'])
                elements.append(title)
                elements.append(Spacer(1, 0.1*inch))
                
                # Informações do entregador
                info_data = [
                    ["ENTREGADOR:", entregador_nome],
                    ["CNPJ:", cnpj if pd.notna(cnpj) else "N/A"],
                    ["PERÍODO:", f"{mes_ref} - {quinzena_ref}"],
                ]
                info_table = Table(info_data, colWidths=[1.3*inch, 3.7*inch])
                info_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                elements.append(info_table)
                elements.append(Spacer(1, 0.15*inch))
                
                # Resumo por CEP
                elements.append(Paragraph("<b>RESUMO OPERACIONAL</b>", styles['Heading3']))
                resumo_cep = df[df['TIPO_LANCAMENTO'] == 'ENTREGA'].groupby('CEP').size().reset_index(name='QTD')
                resumo_data = [["CEP", "QTD ENTREGAS"]]
                for _, row in resumo_cep.iterrows():
                    resumo_data.append([str(row['CEP']), str(int(row['QTD']))])
                
                resumo_table = Table(resumo_data, colWidths=[2*inch, 2*inch])
                resumo_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ]))
                elements.append(resumo_table)
                elements.append(Spacer(1, 0.15*inch))
                
                # Resumo financeiro
                total_valor = df['VALOR_TOTAL_LINHA'].sum()
                total_adicionais = df['VALOR_ADICIONAL'].sum() if 'VALOR_ADICIONAL' in df.columns else 0
                total_descontos = df['VALOR_DESCONTO'].sum() if 'VALOR_DESCONTO' in df.columns else 0
                
                elements.append(Paragraph("<b>RESUMO FINANCEIRO</b>", styles['Heading3']))
                financeiro_data = [
                    ["TOTAL POR CEP", f"R$ {total_valor:.2f}"],
                    ["ADICIONAIS", f"R$ {total_adicionais:.2f}"],
                    ["DESCONTOS", f"R$ {total_descontos:.2f}"],
                    ["TOTAL A RECEBER", f"R$ {total_valor:.2f}"],
                ]
                
                financeiro_table = Table(financeiro_data, colWidths=[3*inch, 1.5*inch])
                financeiro_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                    ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                    ('LINEBELOW', (0, -2), (-1, -2), 2, colors.black),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(financeiro_table)
                elements.append(Spacer(1, 0.3*inch))
                
                # Assinatura
                assinatura_data = [
                    ["ASSINATURA", "DATA"],
                    ["_________________________", "_________________________"],
                ]
                assinatura_table = Table(assinatura_data, colWidths=[2.5*inch, 2*inch])
                assinatura_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('TOPPADDING', (0, 1), (-1, -1), 20),
                ]))
                elements.append(assinatura_table)
                
                doc.build(elements)
                buffer.seek(0)
                return buffer
            
            # Botão para gerar e download do PDF
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📄 Gerar Recibo PDF", use_container_width=True):
                    cnpj = df_filtrado['CNPJ'].iloc[0] if 'CNPJ' in df_filtrado.columns else "N/A"
                    pdf_buffer = gerar_recibo_pdf(df_filtrado, entregador, cnpj, mes, quinzena)
                    
                    st.download_button(
                        label="⬇️ Baixar Recibo",
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
    st.error(f"❌ Erro ao conectar: {str(e)}")
    st.info("Verifique se as credenciais estão configuradas corretamente nos Secrets.")
