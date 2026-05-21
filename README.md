# Dashboard Pagamento GDS Logística

Dashboard em Streamlit para visualizar e gerenciar pagamentos de entregadores.

## 🚀 Funcionalidades

- 📊 Visualização de pagamentos por entregador
- 🔍 Filtros por mês, quinzena e entregador
- 🧾 Geração de recibos em HTML (printável)
- 📈 Métricas em tempo real
- 🔄 Atualização automática de dados

## 📋 Requisitos

- Python 3.8+
- Conta Google com acesso a Google Sheets

## 💻 Instalação Local

1. Clone o repositório:
```bash
git clone https://github.com/SEU-USUARIO/dashboardPagamento-gds.git
cd dashboardPagamento-gds
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as credenciais Google:
   - Crie um arquivo `.streamlit/secrets.toml`
   - Adicione suas credenciais Google Cloud

5. Execute o app:
```bash
streamlit run app.py
```

## 🌐 Deploy no Streamlit Cloud

1. **Push no GitHub:**
```bash
git add .
git commit -m "Dashboard inicial"
git push
```

2. **Acesse** https://share.streamlit.io
3. **Conecte** seu repositório GitHub
4. **Selecione** `app.py` como arquivo principal
5. **Deploy!**

6. **Adicione as credenciais:**
   - Vá em Settings → Secrets
   - Cole suas credenciais Google Cloud JSON

## 🔑 Configuração Google Cloud

### Passo 1: Criar Projeto
- Acesse [Google Cloud Console](https://console.cloud.google.com)
- Clique em "Novo Projeto"
- Dê um nome

### Passo 2: Ativar API
- Procure por "Google Sheets API"
- Clique em "Ativar"

### Passo 3: Criar Service Account
- Vá em "Credenciais"
- Clique em "Criar Credencial" → "Conta de Serviço"
- Preencha os dados
- Clique em "Criar e Continuar"
- Pule os passos extras
- Clique em "Concluído"

### Passo 4: Gerar Chave JSON
- Clique na conta de serviço criada
- Vá em "Chaves"
- Clique em "Adicionar Chave" → "Nova Chave" → "JSON"
- Salve o arquivo JSON

### Passo 5: Compartilhar Planilha
- Abra a planilha no Google Sheets
- Clique em "Compartilhar"
- Copie o email da conta de serviço (do arquivo JSON)
- Compartilhe a planilha com esse email

## 📝 Estrutura de Dados

A planilha deve ter as abas:

### LANCAMENTOS
- ID_LANCAMENTO
- DATA
- MES_REFERENCIA
- QUINZENA
- NOME_ENTREGADOR
- MODAL
- TIPO_LANCAMENTO
- CEP
- QTD_ENTREGAS
- KG_EXCEDENTE
- TIPO_ADICIONAL
- DESCRICAO
- VALOR_UNITARIO
- VALOR_EXCEDENTE
- VALOR_ADICIONAL
- VALOR_DESCONTO
- VALOR_TOTAL_LINHA

### CADASTRO
- NOME
- CNPJ
- (outros campos)

## 🐛 Troubleshooting

### Erro de Credenciais
- Verifique se o arquivo `secrets.toml` está preenchido corretamente
- Confirme que a planilha foi compartilhada com o email da conta de serviço

### Dados não atualizam
- Clique no botão "Atualizar Dados" na sidebar
- O cache é resetado a cada 5 minutos

### Erro ao conectar
- Verifique se as APIs estão ativadas no Google Cloud
- Confirme que a chave JSON é válida

## 📞 Suporte

Para problemas, verifique:
1. Se as credenciais estão corretas
2. Se a planilha está compartilhada
3. Se as colunas da planilha coincidem com o código

---

**Desenvolvido para GDS Logística**