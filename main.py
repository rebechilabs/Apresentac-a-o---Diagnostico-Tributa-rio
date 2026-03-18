"""Orquestrador principal — gera apresentação de diagnóstico tributário."""
import os
import sys
from datetime import datetime

from config import TEMPLATE_PATH, OUTPUT_DIR, TEMP_DIR
from sheets_reader import read_client_data, list_clients
from data_processor import process_data
from chart_generator import generate_all_charts
from slide_updater import update_presentation
from pdf_converter import convert_to_pdf


def _build_chart_data(raw_data: dict) -> dict:
    """Transforma dados brutos da planilha no formato esperado pelo chart_generator.

    Usa dados NUMÉRICOS (antes da formatação BRL) para que os gráficos
    possam calcular proporções e posicionar labels corretamente.
    """
    chart_data = {}

    # Donut chart — dados de indicadores
    ind = raw_data.get("indicadores_resumo", {})
    if ind:
        def _float(key):
            try:
                return float(ind.get(key, 0))
            except (ValueError, TypeError):
                return 0.0

        chart_data["donut"] = {
            "cmv_pct": _float("cmv_pct"),
            "impostos_pct": _float("impostos_pct"),
            "folha_pct": _float("folha_pct"),
            "despesas_pct": _float("despesas_pct"),
            "lucro_pct": _float("lucro_pct"),
            "cmv_valor": _float("faturamento") * _float("cmv_pct") / 100 if _float("cmv_pct") else 0,
            "tributos_valor": _float("tributos"),
            "folha_valor": _float("faturamento") * _float("folha_pct") / 100 if _float("folha_pct") else 0,
            "despesas_valor": _float("faturamento") * _float("despesas_pct") / 100 if _float("despesas_pct") else 0,
            "lucro_valor": _float("faturamento") * _float("lucro_pct") / 100 if _float("lucro_pct") else 0,
        }

    # Gauge chart — cenários comparativos (primeiro cenário)
    cenarios = raw_data.get("cenarios_comparativos", [])
    if cenarios:
        first = cenarios[0]
        try:
            lr = float(first.get("lr_pct", 0))
        except (ValueError, TypeError):
            lr = 0.0
        try:
            lp = float(first.get("lp_pct", 0))
        except (ValueError, TypeError):
            lp = 0.0
        chart_data["gauge"] = {"lr_pct": lr, "lp_pct": lp}

    # Bar chart — reforma tributária
    reforma = raw_data.get("reforma_tributaria", [])
    if reforma:
        bars = []
        for item in reforma:
            try:
                ano = int(item.get("ano", 0))
            except (ValueError, TypeError):
                continue
            try:
                valor = float(item.get("valor", 0))
            except (ValueError, TypeError):
                valor = 0.0
            if ano:
                bars.append({"ano": ano, "valor": valor})
        if bars:
            chart_data["bars"] = bars

    return chart_data


def generate_presentation(client_name=None):
    """Gera a apresentação completa para um cliente.

    Returns:
        tuple: (caminho_pptx, caminho_pdf_ou_None)
    """
    print(f"{'='*50}")
    print(f"  GERADOR DE DIAGNÓSTICO TRIBUTÁRIO")
    print(f"  Rebechi & Silva Advogados Associados")
    print(f"{'='*50}\n")

    # 1. Ler dados da planilha
    print("1/5 Lendo dados da Google Sheets...")
    raw_data = read_client_data(client_name)
    nome = raw_data.get("dados_gerais", {}).get("nome_cliente", "Cliente")
    print(f"    Cliente: {nome}")

    # 2. Gerar gráficos (usa dados brutos/numéricos)
    print("2/5 Gerando gráficos...")
    chart_data = _build_chart_data(raw_data)
    chart_paths = generate_all_charts(chart_data, os.path.join(TEMP_DIR, "charts"))

    # Mapeia nomes de saída do chart_generator para o que slide_updater espera
    charts = {}
    if "donut" in chart_paths:
        charts["donut_chart"] = chart_paths["donut"]
    if "gauge" in chart_paths:
        charts["gauge_chart"] = chart_paths["gauge"]
    if "bar" in chart_paths:
        charts["bar_chart"] = chart_paths["bar"]

    for chart_name, path in charts.items():
        print(f"    {chart_name}: {os.path.basename(path)}")

    # 3. Processar dados (formata valores para exibição nos slides)
    print("3/5 Processando e formatando dados...")
    data = process_data(raw_data)

    # 4. Gerar apresentação
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = nome.replace(" ", "_").replace("/", "_")
    output_pptx = os.path.join(OUTPUT_DIR, f"Diagnostico_{safe_name}_{timestamp}.pptx")

    print("4/5 Gerando apresentação PPTX...")
    update_presentation(data, charts, output_pptx)
    print(f"    PPTX: {output_pptx}")

    # 5. Converter para PDF
    print("5/5 Convertendo para PDF...")
    output_pdf = convert_to_pdf(output_pptx, OUTPUT_DIR)
    if output_pdf:
        print(f"    PDF: {output_pdf}")

    print(f"\n{'='*50}")
    print(f"  Apresentação gerada com sucesso!")
    print(f"{'='*50}")

    return output_pptx, output_pdf


def main():
    if len(sys.argv) > 1:
        client_name = " ".join(sys.argv[1:])
    else:
        clients = list_clients()
        if not clients:
            print("Nenhum cliente encontrado na planilha.")
            return

        print("Clientes disponíveis:")
        for i, name in enumerate(clients, 1):
            print(f"  {i}. {name}")
        print()

        choice = input("Selecione o número do cliente (ou Enter para o primeiro): ").strip()
        if choice:
            idx = int(choice) - 1
            client_name = clients[idx]
        else:
            client_name = clients[0]

    pptx, pdf = generate_presentation(client_name)


if __name__ == "__main__":
    main()
