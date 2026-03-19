"""Processador e formatador de dados para o Diagnóstico Tributário."""

import math


def format_brl(value) -> str:
    """Converte um valor numérico para formato BRL: R$ 1.234.567,89.

    Args:
        value: float, int ou string numérica.

    Returns:
        String formatada ou o valor original como string se não for numérico.
    """
    if value is None or value == "":
        return "R$ 0,00"

    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    if math.isnan(num) or math.isinf(num):
        return "R$ 0,00"

    negative = num < 0
    num = abs(num)

    # Separa parte inteira e decimal
    int_part = int(num)
    dec_part = round((num - int_part) * 100)

    # Ajusta arredondamento
    if dec_part >= 100:
        int_part += 1
        dec_part = 0

    # Formata parte inteira com separador de milhar (ponto)
    int_str = f"{int_part:,}".replace(",", ".")

    # Monta resultado
    formatted = f"R$ {int_str},{dec_part:02d}"
    if negative:
        formatted = f"-{formatted}"

    return formatted


def format_pct(value) -> str:
    """Converte um valor numérico para formato percentual: 11,44%.

    O valor de entrada deve já estar em forma percentual (ex: 11.44 para 11,44%).

    Args:
        value: float, int ou string numérica.

    Returns:
        String formatada ou o valor original como string se não for numérico.
    """
    if value is None or value == "":
        return "0,00%"

    try:
        num = float(value)
    except (ValueError, TypeError):
        return str(value)

    if math.isnan(num) or math.isinf(num):
        return "0,00%"

    formatted = f"{num:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    # Remove separador de milhar para porcentagens (raramente > 999%)
    # mas mantemos a lógica consistente
    return f"{formatted}%"


def _is_monetary_key(key: str) -> bool:
    """Verifica se uma chave representa um valor monetário."""
    monetary_keywords = [
        "valor", "faturamento", "tributo", "credito", "débito", "debito",
        "total", "imposto", "contribuição", "contribuicao", "margem",
        "receita", "despesa", "lucro", "custo", "saldo", "montante",
        "economia", "diferença", "diferenca", "recolhimento",
    ]
    key_lower = key.lower()
    # Exclui chaves que são porcentagens
    if any(p in key_lower for p in ["pct", "percentual", "aliquota", "alíquota", "%"]):
        return False
    return any(kw in key_lower for kw in monetary_keywords)


def _is_percentage_key(key: str) -> bool:
    """Verifica se uma chave representa um percentual."""
    pct_keywords = [
        "pct", "percentual", "aliquota", "alíquota", "aliq", "%", "taxa", "margem_pct",
    ]
    key_lower = key.lower()
    return any(kw in key_lower for kw in pct_keywords)


def _format_dict_values(data: dict) -> dict:
    """Formata valores monetários e percentuais em um dict."""
    result = {}
    for key, value in data.items():
        if isinstance(value, (int, float)):
            if _is_percentage_key(key):
                result[key] = format_pct(value)
            elif _is_monetary_key(key):
                result[key] = format_brl(value)
            else:
                result[key] = value
        else:
            result[key] = value
    return result


def _calculate_recuperacao_total(recuperacao_data: list[dict]) -> float:
    """Calcula o VALOR TOTAL da recuperação tributária (soma de valor_credito)."""
    total = 0.0
    for row in recuperacao_data:
        for key, value in row.items():
            if "valor" in key.lower() and "credito" in key.lower():
                try:
                    total += float(value)
                except (ValueError, TypeError):
                    pass
                break
        else:
            # Tenta coluna genérica de valor/crédito
            for key, value in row.items():
                if "credito" in key.lower() or "crédito" in key.lower():
                    try:
                        total += float(value)
                    except (ValueError, TypeError):
                        pass
                    break
    return total


def _build_diferenca_texto(cenarios: list[dict]) -> list[dict]:
    """Adiciona texto de diferença para cenários comparativos.

    Formato: 'DIFERENÇA ENTRE OS CENÁRIOS DE {pct}% R$ {valor}'
    """
    result = []
    for row in cenarios:
        row_copy = dict(row)

        # Procura campos de diferença percentual e valor
        diff_pct = None
        diff_valor = None
        for key, value in row.items():
            key_lower = key.lower()
            if "diferenca" in key_lower or "diferença" in key_lower:
                if "pct" in key_lower or "%" in key_lower or "percentual" in key_lower:
                    try:
                        diff_pct = float(value)
                    except (ValueError, TypeError):
                        pass
                elif "valor" in key_lower or "r$" in key_lower:
                    try:
                        diff_valor = float(value)
                    except (ValueError, TypeError):
                        pass

        if diff_pct is not None and diff_valor is not None:
            pct_str = format_pct(diff_pct).rstrip("%")
            valor_str = format_brl(diff_valor)
            row_copy["diferenca_texto"] = (
                f"DIFERENÇA ENTRE OS CENÁRIOS DE {pct_str}% {valor_str}"
            )

        result.append(row_copy)
    return result


def _handle_empty_difal(data: dict) -> dict:
    """Substitui campos DIFAL vazios por ' - '."""
    result = {}
    for key, value in data.items():
        if "difal" in key.lower() and (value == "" or value is None):
            result[key] = " - "
        else:
            result[key] = value
    return result


def _handle_empty_difal_list(data: list[dict]) -> list[dict]:
    """Substitui campos DIFAL vazios por ' - ' em lista de dicts."""
    return [_handle_empty_difal(row) for row in data]


def process_data(raw_data: dict) -> dict:
    """Processa os dados brutos do Google Sheets para uso na apresentação.

    Args:
        raw_data: Dict retornado por sheets_reader.read_client_data().

    Returns:
        Dict processado com valores formatados e campos calculados.
    """
    processed = {}

    # Tabs de linha única
    single_row_keys = {
        "dados_gerais", "indicadores_resumo", "gestao_passivos", "sintese_diagnostico",
    }
    for key in single_row_keys:
        if key in raw_data and isinstance(raw_data[key], dict):
            data = _handle_empty_difal(raw_data[key])
            processed[key] = _format_dict_values(data)
        else:
            processed[key] = raw_data.get(key, {})

    # Tabs multi-linhas
    multi_row_keys = {
        "beneficios_fiscais", "resumo_cenarios", "teses_tributarias",
        "recuperacao_tributaria", "reforma_tributaria",
    }
    for key in multi_row_keys:
        if key in raw_data and isinstance(raw_data[key], list):
            rows = _handle_empty_difal_list(raw_data[key])
            processed[key] = [_format_dict_values(row) for row in rows]
        else:
            processed[key] = raw_data.get(key, [])

    # Cenários comparativos - tratamento especial com texto de diferença
    if "cenarios_comparativos" in raw_data and isinstance(raw_data["cenarios_comparativos"], list):
        cenarios = _handle_empty_difal_list(raw_data["cenarios_comparativos"])
        cenarios = _build_diferenca_texto(cenarios)
        processed["cenarios_comparativos"] = [_format_dict_values(row) for row in cenarios]
    else:
        processed["cenarios_comparativos"] = raw_data.get("cenarios_comparativos", [])

    # VALOR TOTAL da recuperação tributária
    if "recuperacao_tributaria" in raw_data and isinstance(raw_data["recuperacao_tributaria"], list):
        total = _calculate_recuperacao_total(raw_data["recuperacao_tributaria"])
        processed["recuperacao_tributaria_total"] = format_brl(total)
    else:
        processed["recuperacao_tributaria_total"] = format_brl(0)

    return processed
