"""Interface Streamlit para geração de diagnósticos tributários."""
import streamlit as st
import os
import tempfile

from config import OUTPUT_DIR
from sheets_reader import list_clients, read_client_data
from data_processor import process_data
from chart_generator import generate_all_charts
from slide_updater import update_presentation
from pdf_converter import convert_to_pdf
from main import _build_chart_data


st.set_page_config(
    page_title="Gerador de Diagnóstico Tributário",
    page_icon="📊",
    layout="centered",
)

st.markdown("""
<style>
    .stApp { background-color: #1B2A4A; }
    h1, h2, h3 { color: #FFC824 !important; }
    .stSelectbox label, .stButton button { color: white; }
</style>
""", unsafe_allow_html=True)

st.title("Diagnóstico Tributário")
st.markdown("**Rebechi & Silva Advogados Associados**")
st.markdown("---")


@st.cache_data(ttl=60)
def get_clients():
    return list_clients()


try:
    clients = get_clients()
except Exception as e:
    st.error(f"Erro ao conectar com Google Sheets: {e}")
    st.stop()

if not clients:
    st.warning("Nenhum cliente encontrado na planilha.")
    st.stop()

selected = st.selectbox("Selecione o cliente:", clients)

if st.button("Gerar Apresentação", type="primary"):
    with st.spinner("Gerando apresentação..."):
        progress = st.progress(0)

        # 1. Ler dados brutos
        st.text("Lendo dados da planilha...")
        raw_data = read_client_data(selected)
        progress.progress(20)

        # 2. Gerar gráficos (usa dados numéricos brutos)
        st.text("Gerando gráficos...")
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_data = _build_chart_data(raw_data)
            chart_paths = generate_all_charts(chart_data, temp_dir)

            # Mapeia nomes para slide_updater
            charts = {}
            if "donut" in chart_paths:
                charts["donut_chart"] = chart_paths["donut"]
            if "gauge" in chart_paths:
                charts["gauge_chart"] = chart_paths["gauge"]
            if "bar" in chart_paths:
                charts["bar_chart"] = chart_paths["bar"]
            progress.progress(40)

            # 3. Processar dados para slides
            st.text("Processando dados...")
            data = process_data(raw_data)
            progress.progress(60)

            # 4. PPTX
            st.text("Montando apresentação...")
            nome = raw_data.get("dados_gerais", {}).get("nome_cliente", "Cliente")
            safe_name = nome.replace(" ", "_").replace("/", "_")
            output_pptx = os.path.join(OUTPUT_DIR, f"Diagnostico_{safe_name}.pptx")
            update_presentation(data, charts, output_pptx)
            progress.progress(80)

            # 5. PDF
            st.text("Convertendo para PDF...")
            output_pdf = convert_to_pdf(output_pptx, OUTPUT_DIR)
            progress.progress(100)

    st.success(f"Apresentação gerada para **{nome}**!")

    col1, col2 = st.columns(2)

    with col1:
        with open(output_pptx, "rb") as f:
            st.download_button(
                label="Baixar PPTX",
                data=f,
                file_name=os.path.basename(output_pptx),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

    with col2:
        if output_pdf and os.path.exists(output_pdf):
            with open(output_pdf, "rb") as f:
                st.download_button(
                    label="Baixar PDF",
                    data=f,
                    file_name=os.path.basename(output_pdf),
                    mime="application/pdf",
                )
        else:
            st.info("PDF não disponível (LibreOffice não instalado)")
