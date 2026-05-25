import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from io import BytesIO

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
        
        # LIMPEZA DE NOMES
        def limpar_nome(nome):
            if pd.isna(nome):
                return ""
            nome = str(nome).strip()
            if "FORMULA" in nome.upper():
                return ""
            return nome.strip()
        
        df_lancamentos['NOME_ENTREGADOR'] = df_lancamentos['NOME_ENTREGADOR'].apply(limpar_nome)
        
        col_nome_cadastro = None
        for col in df_cadastro.columns:
            if 'NOME' in col.upper() or 'ENTREGADOR' in col.upper():
                col_nome_cadastro = col
                break
        if col_nome_cadastro is None:
            col_nome_cadastro = df_cadastro.columns[0]
        
        df_cadastro = df_cadastro.rename(columns={col_nome_cadastro: 'NOME_ENTREGADOR'})
        df_cadastro['NOME_ENTREGADOR'] = df_cadastro['NOME_ENTREGADOR'].apply(limpar_nome)
        
        # Remove linhas vazias
        df_lancamentos = df_lancamentos[df_lancamentos['NOME_ENTREGADOR'] != '']
        df_cadastro = df_cadastro[df_cadastro['NOME_ENTREGADOR'] != '']
        
        # Converter DATA
        df_lancamentos['DATA'] = pd.to_datetime(df_lancamentos['DATA'], errors='coerce')
        df_lancamentos['MES_ANO'] = df_lancamentos['DATA'].dt.strftime('%m/%Y')
        df_lancamentos['MES_REFERENCIA'] = df_lancamentos['MES_ANO']
        
        # Merge CNPJ
        df_lancamentos = df_lancamentos.merge(
            df_cadastro[['NOME_ENTREGADOR', 'CNPJ']], 
            on='NOME_ENTREGADOR', 
            how='left'
        )
        
        # CONVERSÃO DE VALORES NUMÉRICOS
        colunas_numericas = ['QTD_ENTREGAS', 'VALOR_UNITARIO', 'VALOR_EXCEDENTE', 'VALOR_ADICIONAL', 'VALOR_DESCONTO', 'VALOR_TOTAL_LINHA']
        
        for col in colunas_numericas:
            if col in df_lancamentos.columns:
                df_lancamentos[col] = df_lancamentos[col].astype(str).str.replace('R$', '', regex=False).str.replace(',', '.', regex=False).str.strip()
                df_lancamentos[col] = pd.to_numeric(df_lancamentos[col], errors='coerce').fillna(0)
        
        # FILTROS (SÓ MÊS E QUINZENA)
        with st.sidebar:
            st.header("🔧 Filtros")
            
            # Formata meses para exibição (SETEMBRO/2026)
            meses_unicos = sorted(df_lancamentos['MES_REFERENCIA'].dropna().unique())
            meses_display = {mes: f"SETEMBRO/{mes.split('/')[1]}" if "09" in mes else f"JULHO/{mes.split('/')[1]}" if "07" in mes else mes for mes in meses_unicos}
            
            mes = st.selectbox(
                "Mês:",
                meses_unicos,
                format_func=lambda x: meses_display.get(x, x)
            )
            
            df_mes = df_lancamentos[df_lancamentos['MES_REFERENCIA'] == mes]
            quinzenas = sorted(df_mes['QUINZENA'].unique())
            quinzena = st.selectbox("Quinzena:", quinzenas)
        
        # Filtra por QUINZENA INTEIRA
        df_quinzena = df_lancamentos[
            (df_lancamentos['MES_REFERENCIA'] == mes) &
            (df_lancamentos['QUINZENA'] == quinzena)
        ].copy()
        
        if len(df_quinzena) > 0:
            # ===== RELATÓRIO DETALHADO (PRIMEIRO) =====
            st.subheader(f"📊 Relatório Detalhado - {quinzena} ({mes})")
            
            colunas_exibir = ['DATA', 'NOME_ENTREGADOR', 'CEP', 'TIPO_LANCAMENTO', 'QTD_ENTREGAS', 'VALOR_UNITARIO', 'VALOR_ADICIONAL', 'VALOR_DESCONTO', 'VALOR_TOTAL_LINHA']
            colunas_disponiveis = [col for col in colunas_exibir if col in df_quinzena.columns]
            
            st.dataframe(df_quinzena[colunas_disponiveis], use_container_width=True, hide_index=True)
            
            # ===== OPÇÃO DE GERAR RECIBO INDIVIDUAL =====
            st.divider()
            st.subheader("📄 Gerar Recibo Individual")
            
            col_sel1, col_sel2 = st.columns(2)
            with col_sel1:
                entregador_recibo = st.selectbox(
                    "Selecione o entregador para gerar recibo:",
                    sorted(df_quinzena['NOME_ENTREGADOR'].unique()),
                    key="select_recibo"
                )
            
            if entregador_recibo:
                df_entregador = df_quinzena[df_quinzena['NOME_ENTREGADOR'] == entregador_recibo].copy()
                
                # CALCULAR VALORES
                mapa_cep_entrega = {}
                mapa_cep_coleta = {}
                mapa_cep_valor = {}
                total_cep = 0
                adicionais = 0
                descontos = 0
                rota_fechada = 0
                rotas_fechadas_lista = []
                
                for idx, row in df_entregador.iterrows():
                    tipo_lanc = str(row.get('TIPO_LANCAMENTO', '')).upper().strip()
                    cep = str(row.get('CEP', '')).strip()
                    qtd = float(row.get('QTD_ENTREGAS', 0) or 0)
                    v_unit = float(row.get('VALOR_UNITARIO', 0) or 0)
                    v_exc = float(row.get('VALOR_EXCEDENTE', 0) or 0)
                    v_adic = float(row.get('VALOR_ADICIONAL', 0) or 0)
                    v_desc = float(row.get('VALOR_DESCONTO', 0) or 0)
                    valor_total = float(row.get('VALOR_TOTAL_LINHA', 0) or 0)
                    
                    adicionais += v_adic
                    descontos += v_desc
                    
                    if tipo_lanc == "ENTREGA":
                        valor_base = (qtd * v_unit) + v_exc
                        total_cep += valor_base
                        if cep:
                            mapa_cep_entrega[cep] = mapa_cep_entrega.get(cep, 0) + int(qtd)
                            mapa_cep_valor[cep] = mapa_cep_valor.get(cep, 0) + valor_base
                    
                    elif tipo_lanc == "COLETA":
                        valor_base = (qtd * v_unit) + v_exc
                        total_cep += valor_base
                        if cep:
                            mapa_cep_coleta[cep] = mapa_cep_coleta.get(cep, 0) + int(qtd)
                            mapa_cep_valor[cep] = mapa_cep_valor.get(cep, 0) + valor_base
                    
                    elif tipo_lanc == "ROTA FECHADA":
                        rota_fechada += valor_total
                        rotas_fechadas_lista.append({'cep': cep if cep else '', 'valor': valor_total})
                    
                    elif tipo_lanc == "DESCONTO":
                        if v_desc == 0 and valor_total < 0:
                            descontos += abs(valor_total)
                    else:
                        if v_adic == 0 and valor_total > 0:
                            adicionais += valor_total
                
                total_pagar = total_cep + adicionais + rota_fechada - descontos
                cnpj = df_entregador['CNPJ'].iloc[0] if 'CNPJ' in df_entregador.columns else ""
                cnpj_str = str(cnpj).strip() if pd.notna(cnpj) else "N/A"
                
                periodo_inicio = df_entregador['DATA'].min().strftime('%d/%m')
                periodo_fim = df_entregador['DATA'].max().strftime('%d/%m')
                
                # FUNÇÃO RECIBO
                def gerar_recibo_html():
                    badges_cep_html = ""
                    todos_ceps = sorted(set(list(mapa_cep_entrega.keys()) + list(mapa_cep_coleta.keys())))
                    
                    for cep in todos_ceps:
                        qtd_ent = mapa_cep_entrega.get(cep, 0)
                        qtd_col = mapa_cep_coleta.get(cep, 0)
                        valor_cep = mapa_cep_valor.get(cep, 0)
                        
                        partes = []
                        if qtd_ent > 0:
                            partes.append(f"{int(qtd_ent)} entregas")
                        if qtd_col > 0:
                            partes.append(f"{int(qtd_col)} coletas")
                        
                        partes_texto = " + ".join(partes)
                        badges_cep_html += f'<span class="badge">CEP {cep} — {partes_texto} — R$ {valor_cep:.2f}</span>'
                    
                    badges_rota_html = ""
                    for rota in rotas_fechadas_lista:
                        lbl = f"ROTA FECHADA CEP {rota['cep']}" if rota['cep'] else "ROTA FECHADA"
                        badges_rota_html += f'<span class="badge-blue">{lbl} — R$ {rota["valor"]:.2f}</span>'
                    
                    badge_adicional = f'<span class="badge-green">Adicional R$ {adicionais:.2f}</span>' if adicionais > 0 else ""
                    badge_desconto = f'<span class="badge-red">Desconto R$ {descontos:.2f}</span>' if descontos > 0 else ""
                    
                    linha_rota = f'<div class="row"><span>ROTA FECHADA</span><span>R$ {rota_fechada:.2f}</span></div>' if rota_fechada > 0 else ""
                    linha_desconto = f'<div class="row red"><span>DESCONTOS</span><span>— R$ {descontos:.2f}</span></div>' if descontos > 0 else '<div class="row"><span>DESCONTOS</span><span>R$ 0.00</span></div>'
                    
                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="UTF-8">
                        <title>Recibo de Pagamento</title>
                        <style>
                            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                            body {{ font-family: Arial, sans-serif; font-size: 12px; background: #f5f5f5; }}
                            .page {{ width: 210mm; padding: 10mm; margin: 10px auto; background: white; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                            .recibo {{ border: 2px solid #333; padding: 15px; }}
                            .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #333; padding: 10px 0; margin-bottom: 15px; }}
                            .header span {{ font-weight: bold; font-size: 13px; }}
                            .row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #ddd; }}
                            .row.red {{ color: #cc0000; }}
                            .row.total {{ border-top: 2px solid #333; border-bottom: 0; margin-top: 8px; padding-top: 8px; font-weight: bold; font-size: 14px; }}
                            .label {{ font-weight: bold; color: #666; font-size: 10px; text-transform: uppercase; margin-bottom: 3px; }}
                            .value {{ font-weight: bold; font-size: 12px; }}
                            .badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; margin-bottom: 10px; }}
                            .badge, .badge-red, .badge-green, .badge-blue {{ border-radius: 20px; padding: 4px 10px; font-size: 10px; font-weight: bold; border: 1px solid; }}
                            .badge {{ border-color: #999; color: #333; }}
                            .badge-red {{ border-color: #cc0000; color: #cc0000; }}
                            .badge-green {{ border-color: #008000; color: #008000; }}
                            .badge-blue {{ border-color: #0044cc; color: #0044cc; }}
                            .info-block {{ display: flex; gap: 30px; padding: 10px 0; border-bottom: 1px solid #ddd; margin-bottom: 10px; }}
                            .info-item {{ flex: 1; }}
                            .assinatura {{ display: flex; gap: 40px; margin-top: 30px; }}
                            .ass-item {{ flex: 1; }}
                            .ass-line {{ border-bottom: 1px solid #333; height: 50px; margin-bottom: 5px; }}
                            .ass-label {{ font-size: 10px; font-weight: bold; text-align: center; }}
                        </style>
                    </head>
                    <body>
                        <div class="page">
                            <div class="recibo">
                                <div class="header">
                                    <span>RECIBO DE PAGAMENTO</span>
                                    <span>{mes}</span>
                                </div>
                                
                                <div class="info-block">
                                    <div class="info-item">
                                        <div class="label">ENTREGADOR</div>
                                        <div class="value">{entregador_recibo}</div>
                                    </div>
                                    <div class="info-item">
                                        <div class="label">CNPJ</div>
                                        <div class="value">{cnpj_str}</div>
                                    </div>
                                    <div class="info-item">
                                        <div class="label">PERÍODO</div>
                                        <div class="value">{periodo_inicio} a {periodo_fim}</div>
                                    </div>
                                </div>
                                
                                <div style="margin: 15px 0;">
                                    <div style="font-weight: bold; margin-bottom: 8px;">VALORES</div>
                                    <div class="row"><span>TOTAL POR CEP</span><span>R$ {total_cep:.2f}</span></div>
                                    {linha_rota}
                                    <div class="row"><span>ADICIONAIS</span><span>R$ {adicionais:.2f}</span></div>
                                    {linha_desconto}
                                    <div class="row total"><span>TOTAL A RECEBER</span><span>R$ {total_pagar:.2f}</span></div>
                                </div>
                                
                                <div style="margin-top: 15px;">
                                    <div class="label">RESUMO OPERACIONAL</div>
                                    <div class="badges">
                                        {badges_cep_html}
                                        {badges_rota_html}
                                        {badge_adicional}
                                        {badge_desconto}
                                    </div>
                                </div>
                                
                                <div class="assinatura">
                                    <div class="ass-item">
                                        <div class="ass-line"></div>
                                        <div class="ass-label">ASSINATURA DO ENTREGADOR</div>
                                    </div>
                                    <div class="ass-item">
                                        <div class="ass-line"></div>
                                        <div class="ass-label">DATA</div>
                                    </div>
                                </div>
                                
                                <div style="text-align: center; margin-top: 20px; font-size: 10px; color: #888;">
                                    Gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}
                                </div>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                    return html
                
                # Botões
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("📄 Gerar Recibo", use_container_width=True, key="gerar_recibo"):
                        st.session_state.show_recibo = True
                
                with col_btn2:
                    if st.button("⬇️ Baixar HTML", use_container_width=True, key="baixar_html"):
                        html_recibo = gerar_recibo_html()
                        st.download_button(
                            label="Clique aqui para confirmar download",
                            data=html_recibo,
                            file_name=f"Recibo_{entregador_recibo.replace(' ', '_')}.html",
                            mime="text/html",
                            key="download_btn"
                        )
                
                # Mostra recibo
                if st.session_state.get("show_recibo"):
                    st.divider()
                    html_recibo = gerar_recibo_html()
                    components.html(html_recibo, height=900, scrolling=True)
                    st.info("💡 **Para imprimir como PDF:** Use Ctrl+P → Salvar como PDF")
            
            # ===== RESUMO POR ENTREGADOR (FINAL - COM BOTÃO) =====
            st.divider()
            st.subheader("📋 Gerar Resumo de Entregadores")
            
            if st.button("🔍 Gerar Resumo da Quinzena", use_container_width=True, key="gerar_resumo"):
                st.session_state.show_resumo = True
            
            if st.session_state.get("show_resumo"):
                resumo_entregadores = []
                
                for entregador in sorted(df_quinzena['NOME_ENTREGADOR'].unique()):
                    df_ent = df_quinzena[df_quinzena['NOME_ENTREGADOR'] == entregador]
                    
                    mapa_cep_entrega = {}
                    mapa_cep_coleta = {}
                    total_cep = 0
                    adicionais = 0
                    descontos = 0
                    rota_fechada = 0
                    
                    for idx, row in df_ent.iterrows():
                        tipo_lanc = str(row.get('TIPO_LANCAMENTO', '')).upper().strip()
                        cep = str(row.get('CEP', '')).strip()
                        qtd = float(row.get('QTD_ENTREGAS', 0) or 0)
                        v_unit = float(row.get('VALOR_UNITARIO', 0) or 0)
                        v_exc = float(row.get('VALOR_EXCEDENTE', 0) or 0)
                        v_adic = float(row.get('VALOR_ADICIONAL', 0) or 0)
                        v_desc = float(row.get('VALOR_DESCONTO', 0) or 0)
                        valor_total = float(row.get('VALOR_TOTAL_LINHA', 0) or 0)
                        
                        adicionais += v_adic
                        descontos += v_desc
                        
                        if tipo_lanc == "ENTREGA":
                            valor_base = (qtd * v_unit) + v_exc
                            total_cep += valor_base
                            if cep:
                                mapa_cep_entrega[cep] = mapa_cep_entrega.get(cep, 0) + int(qtd)
                        
                        elif tipo_lanc == "COLETA":
                            valor_base = (qtd * v_unit) + v_exc
                            total_cep += valor_base
                            if cep:
                                mapa_cep_coleta[cep] = mapa_cep_coleta.get(cep, 0) + int(qtd)
                        
                        elif tipo_lanc == "ROTA FECHADA":
                            rota_fechada += valor_total
                        
                        elif tipo_lanc == "DESCONTO":
                            if v_desc == 0 and valor_total < 0:
                                descontos += abs(valor_total)
                        else:
                            if v_adic == 0 and valor_total > 0:
                                adicionais += valor_total
                    
                    total_pagar = total_cep + adicionais + rota_fechada - descontos
                    cnpj = df_ent['CNPJ'].iloc[0] if 'CNPJ' in df_ent.columns else ""
                    
                    resumo_entregadores.append({
                        'ENTREGADOR': entregador,
                        'CNPJ': str(cnpj).strip() if pd.notna(cnpj) else "N/A",
                        'ENTREGAS': int(sum(mapa_cep_entrega.values())),
                        'COLETAS': int(sum(mapa_cep_coleta.values())),
                        'TOTAL CEP': f"R$ {total_cep:.2f}",
                        'ADICIONAIS': f"R$ {adicionais:.2f}",
                        'DESCONTOS': f"R$ {descontos:.2f}",
                        'ROTA FECHADA': f"R$ {rota_fechada:.2f}",
                        'TOTAL A RECEBER': f"R$ {total_pagar:.2f}"
                    })
                
                # EXIBIR CARDS
                st.markdown(f"### Resumo de Entregadores - {quinzena} ({mes})")
                
                for i in range(0, len(resumo_entregadores), 2):
                    cols = st.columns(2)
                    
                    for col_idx, resumo in enumerate(resumo_entregadores[i:i+2]):
                        with cols[col_idx]:
                            st.markdown(f"""
                            <div style="border: 2px solid #1565c0; border-radius: 8px; padding: 15px; background: #e3f2fd; margin-bottom: 10px;">
                                <div style="font-weight: bold; color: #1565c0; font-size: 14px; margin-bottom: 5px;">{resumo['ENTREGADOR']}</div>
                                <div style="font-size: 11px; color: #666; margin-bottom: 10px;">CNPJ: {resumo['CNPJ']}</div>
                                <div style="background: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 12px;">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                        <span>Entregas:</span>
                                        <span style="font-weight: bold;">{resumo['ENTREGAS']}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                        <span>Coletas:</span>
                                        <span style="font-weight: bold;">{resumo['COLETAS']}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                        <span>Total CEP:</span>
                                        <span style="font-weight: bold;">{resumo['TOTAL CEP']}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between;">
                                        <span>Adicionais:</span>
                                        <span style="font-weight: bold;">{resumo['ADICIONAIS']}</span>
                                    </div>
                                </div>
                                <div style="background: #fff59d; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; color: #333; font-size: 16px;">
                                    {resumo['TOTAL A RECEBER']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                
                # BOTÃO PARA BAIXAR EM EXCEL
                df_resumo = pd.DataFrame(resumo_entregadores)
                
                # Converter para Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_resumo.to_excel(writer, sheet_name='Resumo', index=False)
                
                output.seek(0)
                
                st.download_button(
                    label="⬇️ Baixar Resumo em Excel",
                    data=output.getvalue(),
                    file_name=f"Resumo_Entregadores_{quinzena}_{mes}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        else:
            st.warning("⚠️ Nenhum dado encontrado para os filtros selecionados.")
    else:
        raise Exception("Credenciais não encontradas")
        
except Exception as e:
    st.error(f"❌ Erro: {str(e)}")
    st.info("Verifique se:\n- Credenciais estão nos Secrets\n- Service account tem permissão 'Editor'\n- Google Sheet está compartilhado com a service account")
