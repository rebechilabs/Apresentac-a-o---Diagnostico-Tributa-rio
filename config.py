"""Configurações do Gerador de Diagnóstico Tributário."""
import os
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths
TEMPLATE_PATH = os.path.join(BASE_DIR, "Cópia de MODELO DIAGNÓSTICO  2026.pptx")
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# Diretórios de saída — usa /tmp no cloud (sem permissão de escrita no BASE_DIR)
_is_cloud = not os.access(BASE_DIR, os.W_OK) or os.environ.get("STREAMLIT_SERVER_PORT")
if _is_cloud:
    OUTPUT_DIR = os.path.join(tempfile.gettempdir(), "diagnostico_output")
    TEMP_DIR = os.path.join(tempfile.gettempdir(), "diagnostico_temp")
else:
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Google Sheets
SPREADSHEET_ID = "1fo-9fk787Cm4mfLZ7nfZBDm1ni_7J2asqyyRAJ9lD4E"
SHEET_NAMES = {
    "dados_gerais": "Dados Gerais",
    "indicadores_resumo": "Indicadores Resumo",
    "cenarios_comparativos": "Cenarios Comparativos",
    "beneficios_fiscais": "Beneficios Fiscais",
    "resumo_cenarios": "Resumo Cenarios",
    "gestao_passivos": "Gestao Passivos",
    "teses_tributarias": "Teses Tributarias",
    "recuperacao_tributaria": "Recuperacao Tributaria",
    "reforma_tributaria": "Reforma Tributaria",
    "sintese_diagnostico": "Sintese Diagnostico",
}

# Cores do template (hex)
CORES = {
    "fundo_escuro": "#1B2A4A",
    "dourado": "#FFC824",
    "vermelho": "#F07070",
    "verde": "#4CAF50",
    "cinza_escuro": "#888888",
    "cinza_claro": "#C0C0C0",
    "branco": "#FFFFFF",
}

# Fontes
FONTES = {
    "titulo": "Montserrat",
    "titulo_bold": "Montserrat Bold",
    "corpo": "Montserrat",
    "barras": "Poppins",
}

# Slides editáveis (0-indexed)
EDITABLE_SLIDES = [0, 2, 4, 9, 11, 13, 15, 17, 18, 19, 20, 23, 25]

# Mapeamento de shapes por slide (shape_name → campo de dados)
SHAPE_MAP = {
    0: {  # Slide 1 - Capa
        "TextBox 12": "nome_cliente",
    },
    2: {  # Slide 3 - Indicadores
        "TextBox 18": "faturamento_valor",
        "TextBox 26": "tributos_valor",
        "TextBox 34": "aliquota_efetiva",
        "TextBox 47": "margem_contribuicao_valor",
        "Picture 11": "__donut_chart__",
    },
    4: {  # Slide 5 - Indicadores Resumo (tabela)
        "__table__": "indicadores_resumo",
    },
    9: {  # Slide 10 - Cenário 1
        "TextBox 26": "lr_pct",
        "TextBox 43": "lp_pct",
        "TextBox 47": "diferenca_texto",
    },
    11: {  # Slide 12 - Cenário 2
        "TextBox 26": "lr_pct",
        "TextBox 43": "lp_pct",
        "TextBox 47": "diferenca_texto",
    },
    13: {  # Slide 14 - Cenário 3
        "TextBox 26": "lr_pct",
        "TextBox 27": "cenario_nome",
        "TextBox 43": "lp_pct",
        "TextBox 47": "diferenca_texto",
    },
    15: {  # Slide 16 - Benefícios Fiscais
        "__beneficios__": "beneficios_fiscais",
    },
    17: {  # Slide 18 - Resumo Cenários (tabela)
        "__table__": "resumo_cenarios",
    },
    18: {  # Slide 19 - Gestão de Passivos
        "__passivos__": "gestao_passivos",
    },
    19: {  # Slide 20 - Teses Tributárias
        "__teses__": "teses_tributarias",
    },
    20: {  # Slide 21 - Recuperação Tributária (tabela)
        "__table__": "recuperacao_tributaria",
    },
    23: {  # Slide 24 - Reforma Tributária
        "Picture 3": "__bar_chart__",
        "TextBox 13": "aliquotas_texto",
    },
    25: {  # Slide 26 - Síntese do Diagnóstico
        "TextBox 15": "paragrafo_1",
        "TextBox 16": "paragrafo_2",
        "TextBox 20": "badge_1",
        "TextBox 24": "badge_2",
        "TextBox 28": "badge_3",
        "TextBox 32": "badge_4",
    },
}

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
