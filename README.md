# Diagnóstico Tributário - Gerador de Apresentações

Gerador automático de apresentações de diagnóstico tributário para **Rebechi & Silva Advogados Associados**.

Lê dados de clientes do Google Sheets, gera gráficos profissionais e preenche um template PPTX personalizado.

## Instalação Local

```bash
pip install -r requirements.txt
```

### Fontes (opcional para máxima fidelidade visual)
Instale **Montserrat Bold** e **Poppins Bold** em `~/Library/Fonts/` (macOS) ou o app usará as fontes incluídas na pasta `fonts/`.

### LibreOffice (opcional para exportar PDF)
```bash
brew install --cask libreoffice
```

## Uso

### Interface Web (Streamlit)
```bash
streamlit run app.py
```

### Linha de Comando
```bash
python main.py                        # seleção interativa
python main.py "NOME DO CLIENTE"      # cliente específico
```

## Deploy no Streamlit Cloud

1. Faça fork/push do repositório para o GitHub
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte com sua conta GitHub
3. Selecione o repositório, branch `main`, main file `app.py`
4. Em **Advanced settings > Secrets**, cole o conteúdo do seu `credentials.json` no formato TOML:

```toml
[google_credentials]
type = "service_account"
project_id = "seu-projeto"
private_key_id = "sua-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "seu-email@projeto.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/seu-email-encoded"
universe_domain = "googleapis.com"
```

5. Clique **Deploy**

> **Nota:** A conversão para PDF não está disponível no Streamlit Cloud (requer LibreOffice). O download PPTX funciona normalmente.

## Configuração do Google Sheets

A planilha deve conter as seguintes abas:
- Dados Gerais
- Indicadores Resumo
- Cenarios Comparativos
- Beneficios Fiscais
- Resumo Cenarios
- Gestao Passivos
- Teses Tributarias
- Recuperacao Tributaria
- Reforma Tributaria
- Sintese Diagnostico

O email da service account deve ter acesso de leitura à planilha.
