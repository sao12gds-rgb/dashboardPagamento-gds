import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard GDS Logística", layout="wide")

st.title("📊 Dashboard de Pagamento - GDS Logística")

st.success("✅ App carregado com sucesso!")

# Dados de exemplo
dados_exemplo = {
    'Entregador': ['João Silva', 'Maria Santos', 'Pedro Costa', 'João Silva', 'Maria Santos'],
    'Data': ['2026-05-15', '2026-05-16', '2026-05-17', '2026-05-18', '2026-05-19'],
    'Tipo': ['ENTREGA', 'ENTREGA', 'ROTA MALA', 'ADICIONAL', 'ENTREGA'],
    'Valor': [150.00, 200.00, 100.00, 50.00, 180.00]
}

df = pd.DataFrame(dados_exemplo)

# Sidebar
with st.sidebar:
    st.header("🔧 Filtros")
    entregador_selecionado = st.selectbox("Entregador:", df['Entregador'].unique())
    
df_filtrado = df[df['Entregador'] == entregador_selecionado]

# Métricas
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("💰 Total", f"R$ {df_filtrado['Valor'].sum():.2f}")
with col2:
    st.metric("📦 Entregas", len(df_filtrado[df_filtrado['Tipo'] == 'ENTREGA']))
with col3:
    st.metric("📋 Lançamentos", len(df_filtrado))

# Tabela
st.subheader(f"Lançamentos de {entregador_selecionado}")
st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

st.info("""
### 🔑 Próximas Etapas:

1. **Clique em Settings** ⚙️
2. **Vá em Secrets**
3. **Cole suas credenciais do Google Cloud**
4. **O dashboard vai conectar automaticamente!**

Credenciais salvas em: https://drive.google.com/file/d/1Hi5GeEegIeWsQbLel5Wh2_FyP1XQL1UW/view
""")
