import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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
        df_lancamentos['MES_REFERENCIA'] = df_lancamentos['MES_REFERENCIA'].str.split('/').str[0].str.strip()
        
        # Encontra a coluna de nome no CADASTRO
        col_nome_cadastro = None
        for col in df_cadastro.columns:
            if 'NOME' in col.upper() or 'ENTREGADOR' in col.upper():
                col_nome_cadastro = col
                break
        if col_nome_cadastro is None:
            col_nome_cadastro = df_cadastro.columns[0]
        
        df_cadastro = df_cadastro.rename(columns={col_nome_cadastro: 'NOME_ENTREGADOR'})
        
        # Merge CNPJ
        df_lancamentos = df_lancamentos.merge(
            df_cadastro[['NOME_ENTREGADOR', 'CNPJ']], 
            on='NOME_ENTREGADOR', 
            how='left'
        )
        
        # Converter valores para float (remove espaços e converte)
        for col in ['VALOR_TOTAL_LINHA', 'VALOR_ADICIONAL', 'VALOR_DESCONTO']:
            if col in df_lancamentos.columns:
                df_lancamentos[col] = pd.to_numeric(
                    df_lancamentos[col].astype(str).str.replace(',', '.'), 
                    errors='coerce'
                ).fillna(0)
        
        # Filtros
        with st.sidebar:
            st.header("🔧 Filtros")
            meses = sorted(df_lancamentos['MES_REFERENCIA'].dropna().unique())
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
        ].copy()
        
        if len(df_filtrado) > 0:
            # Cálculos
            total = float(df_filtrado['VALOR_TOTAL_LINHA'].sum())
            entregas = len(df_filtrado[df_filtrado['TIPO_LANCAMENTO'] == 'ENTREGA'])
            adicionais = float(df_filtrado['VALOR_ADICIONAL'].sum())
            descontos = float(df_filtrado['VALOR_DESCONTO'].sum())
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
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
            
            # Função para gerar HTML do recibo
            def gerar_recibo_html(df, entregador_nome, cnpj, mes_ref, quinzena_ref):
                total_valor = float(df['VALOR_TOTAL_LINHA'].sum())
                total_adicionais = float(df['VALOR_ADICIONAL'].sum())
                total_descontos = float(df['VALOR_DESCONTO'].sum())
                
                resumo = df[df['TIPO_LANCAMENTO'] == 'ENTREGA'].groupby('CEP').size().reset_index(name='QTD')
                
                linhas_resumo = ""
                for _, row in resumo.iterrows():
                    linhas_resumo += f"<tr><td style='border: 1px solid #000; padding: 10px;'>{row['CEP']}</td><td style='border: 1px solid #000; padding: 10px; text-align: center;'>{int(row['QTD'])}</td></tr>"
                
                cnpj_str = str(cnpj) if pd.notna(cnpj) else "N/A"
                
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Recibo de Pagamento</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .container {{ max-width: 900px; margin: 0 auto; padding: 30px; border: 2px solid #000; }}
                        .header {{ text-align: center; margin-bottom: 30px; }}
                        h1 {{ font-size: 24px; font-weight: bold; margin: 0; }}
                        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                        td {{ padding: 10px; }}
                        th {{ padding: 10px; text-align: left; font-weight: bold; }}
                        .label {{ font-weight: bold; width: 150px; }}
                        .border-table {{ border: 1px solid #000; }}
                        .section-title {{ font-weight: bold; font-size: 14px; margin-top: 20px; margin-bottom: 10px; border-bottom: 2px solid #000; padding-bottom: 5px; }}
                        .valor {{ text-align: right; }}
                        .total-row {{ border-top: 2px solid #000; border-bottom: 2px solid #000; background-color: #f9f9f9; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <div class='container'>
                        <div class='header'>
                            <h1>RECIBO DE PAGAMENTO</h1>
                        </div>
                        
                        <table>
                            <tr>
                                <td class='label'>ENTREGADOR:</td>
                                <td>{entregador_nome}</td>
                            </tr>
                            <tr>
                                <td class='label'>CNPJ:</td>
                                <td>{cnpj_str}</td>
                            </tr>
                            <tr>
                                <td class='label'>PERÍODO:</td>
                                <td>{mes_ref} - {quinzena_ref}</td>
                            </tr>
                        </table>
                        
                        <div class='section-title'>RESUMO OPERACIONAL</div>
                        <table class='border-table'>
                            <tr>
                                <th>CEP</th>
                                <th>QTD ENTREGAS</th>
                            </tr>
                            {linhas_resumo}
                        </table>
                        
                        <div class='section-title'>RESUMO FINANCEIRO</div>
                        <table>
                            <tr>
                                <td class='label'>TOTAL POR CEP</td>
                                <td class='valor'>R$ {total_valor:.2f}</td>
                            </tr>
                            <tr>
                                <td class='label'>ADICIONAIS</td>
                                <td class='valor'>R$ {total_adicionais:.2f}</td>
                            </tr>
                            <tr>
                                <td class='label'>DESCONTOS</td>
                                <td class='valor'>R$ {total_descontos:.2f}</td>
                            </tr>
                            <tr class='total-row'>
                                <td class='label'>TOTAL A RECEBER</td>
                                <td class='valor'>R$ {total_valor:.2f}</td>
                            </tr>
                        </table>
                        
                        <div style='margin-top: 50px; display: flex; justify-content: space-around;'>
                            <div style='text-align: center; width: 200px;'>
                                <div style='border-bottom: 1px solid #000; height: 50px; margin-bottom: 10px;'></div>
                                <div style='font-size: 12px; font-weight: bold;'>ASSINATURA DO ENTREGADOR</div>
                            </div>
                            <div style='text-align: center; width: 200px;'>
                                <div style='border-bottom: 1px solid #000; height: 50px; margin-bottom: 10px;'></div>
                                <div style='font-size: 12px; font-weight: bold;'>DATA</div>
                            </div>
                        </div>
                        
                        <div style='text-align: center; margin-top: 30px; font-size: 11px; color: #666;'>
                            <p>Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} | GDS Logística</p>
                        </div>
                    </div>
                </body>
                </html>
                """
                return html
            
            # Botões
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            with col_btn1:
                if st.button("📄 Gerar Recibo", use_container_width=True, key="gerar_recibo"):
                    st.session_state.show_recibo = True
            
            with col_btn2:
                if st.button("⬇️ Baixar HTML", use_container_width=True, key="baixar_html"):
                    cnpj = df_filtrado['CNPJ'].iloc[0] if 'CNPJ' in df_filtrado.columns else "N/A"
                    html_recibo = gerar_recibo_html(df_filtrado, entregador, cnpj, mes, quinzena)
                    st.download_button(
                        label="Clique aqui para confirmar download",
                        data=html_recibo,
                        file_name=f"Recibo_{entregador.replace(' ', '_')}_{mes}_{quinzena}.html",
                        mime="text/html",
                        key="download_btn"
                    )
            
            with col_btn3:
                if st.button("🖨️ Imprimir", use_container_width=True, key="imprimir"):
                    st.session_state.show_recibo = True
            
            # Mostra recibo
            if st.session_state.get("show_recibo"):
                st.divider()
                cnpj = df_filtrado['CNPJ'].iloc[0] if 'CNPJ' in df_filtrado.columns else "N/A"
                html_recibo = gerar_recibo_html(df_filtrado, entregador, cnpj, mes, quinzena)
                components.html(html_recibo, height=1200, scrolling=True)
                st.info("💡 **Para imprimir como PDF:** Use Ctrl+P → Salvar como PDF")
        else:
            st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
    else:
        raise Exception("Credenciais não encontradas")
        
except Exception as e:
    st.error(f"❌ Erro: {str(e)}")
