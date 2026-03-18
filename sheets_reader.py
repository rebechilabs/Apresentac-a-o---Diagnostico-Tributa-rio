"""Leitor de dados do Google Sheets para o Diagnóstico Tributário."""

import gspread
from google.oauth2.service_account import Credentials

from config import CREDENTIALS_PATH, SPREADSHEET_ID, SHEET_NAMES

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Tabs que retornam uma única linha (dict de header -> valor)
SINGLE_ROW_TABS = {
    "dados_gerais",
    "indicadores_resumo",
    "gestao_passivos",
    "sintese_diagnostico",
}

# Tabs que retornam múltiplas linhas (lista de dicts)
MULTI_ROW_TABS = {
    "cenarios_comparativos",
    "beneficios_fiscais",
    "resumo_cenarios",
    "teses_tributarias",
    "recuperacao_tributaria",
    "reforma_tributaria",
}


def _get_client() -> gspread.Client:
    """Autentica e retorna o client gspread."""
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)
    return gspread.authorize(creds)


def _parse_value(value: str):
    """Converte strings numéricas para float quando possível.

    Trata formatos brasileiros (1.234,56) e internacionais (1234.56).
    Retorna a string original se a conversão falhar.
    """
    if value is None:
        return ""
    value = str(value).strip()
    if value == "":
        return ""

    # Remove espaços e caracteres de moeda/porcentagem para tentar conversão
    cleaned = value.replace("R$", "").replace("%", "").strip()

    # Tenta detectar formato brasileiro: 1.234,56
    if "," in cleaned and "." in cleaned:
        try:
            numeric = cleaned.replace(".", "").replace(",", ".")
            return float(numeric)
        except ValueError:
            pass
    elif "," in cleaned and "." not in cleaned:
        # Formato com vírgula decimal sem separador de milhar: 12,34
        try:
            numeric = cleaned.replace(",", ".")
            return float(numeric)
        except ValueError:
            pass
    else:
        # Formato internacional ou inteiro
        try:
            return float(cleaned)
        except ValueError:
            pass

    return value


def _read_single_row(worksheet: gspread.Worksheet) -> dict:
    """Lê uma aba de linha única e retorna dict header -> valor."""
    all_values = worksheet.get_all_values()
    if len(all_values) < 2:
        # Só tem cabeçalho ou está vazia
        headers = all_values[0] if all_values else []
        return {h: "" for h in headers}

    headers = all_values[0]
    row = all_values[1]

    result = {}
    for i, header in enumerate(headers):
        if not header.strip():
            continue
        val = row[i] if i < len(row) else ""
        result[header.strip()] = _parse_value(val)
    return result


def _read_multi_row(worksheet: gspread.Worksheet) -> list[dict]:
    """Lê uma aba multi-linhas e retorna lista de dicts."""
    all_values = worksheet.get_all_values()
    if len(all_values) < 2:
        return []

    headers = [h.strip() for h in all_values[0]]
    rows = []

    for row in all_values[1:]:
        # Pula linhas completamente vazias
        if not any(cell.strip() for cell in row):
            continue
        record = {}
        for i, header in enumerate(headers):
            if not header:
                continue
            val = row[i] if i < len(row) else ""
            record[header] = _parse_value(val)
        rows.append(record)

    return rows


def read_client_data(client_name: str = None) -> dict:
    """Lê todos os dados do cliente a partir do Google Sheets.

    Args:
        client_name: Nome do cliente (reservado para uso futuro com
                     múltiplos clientes na mesma planilha). Atualmente
                     lê os dados da planilha configurada em config.py.

    Returns:
        Dict com chaves correspondentes às keys de SHEET_NAMES.
        - Tabs single-row: dict de header -> valor
        - Tabs multi-row: lista de dicts
    """
    gc = _get_client()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    data = {}
    for key, tab_name in SHEET_NAMES.items():
        try:
            worksheet = spreadsheet.worksheet(tab_name)
        except gspread.exceptions.WorksheetNotFound:
            data[key] = {} if key in SINGLE_ROW_TABS else []
            continue

        if key in SINGLE_ROW_TABS:
            data[key] = _read_single_row(worksheet)
        else:
            data[key] = _read_multi_row(worksheet)

    return data


def list_clients() -> list[str]:
    """Retorna lista de nomes de clientes da aba 'Dados Gerais'.

    Lê a coluna A a partir da linha 2.
    """
    gc = _get_client()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)

    try:
        worksheet = spreadsheet.worksheet(SHEET_NAMES["dados_gerais"])
    except gspread.exceptions.WorksheetNotFound:
        return []

    # Coluna A, todas as linhas
    col_values = worksheet.col_values(1)

    # Pula o cabeçalho (linha 1) e filtra vazios
    clients = [name.strip() for name in col_values[1:] if name.strip()]
    return clients
