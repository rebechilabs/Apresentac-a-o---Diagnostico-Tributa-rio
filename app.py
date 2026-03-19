"""Interface Streamlit para geração de diagnósticos tributários."""
import streamlit as st
import os
import base64
import tempfile

from config import OUTPUT_DIR
from sheets_reader import list_clients, read_client_data
from data_processor import process_data
from chart_generator import generate_all_charts
from slide_updater import update_presentation
from pdf_converter import convert_to_pdf
from main import _build_chart_data


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Diagnóstico Tributário | Rebechi & Silva",
    page_icon="⚖️",
    layout="centered",
)


# ---------------------------------------------------------------------------
# Custom CSS - Identidade Visual Rebechi & Silva
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    /* === Cores da identidade === */
    :root {
        --fundo-escuro: #1B2A4A;
        --dourado: #FFC824;
        --dourado-hover: #E6B420;
        --branco: #FFFFFF;
        --cinza-claro: #C0C0C0;
    }

    /* === Fundo geral === */
    .stApp {
        background: linear-gradient(135deg, #0F1B2E 0%, #1B2A4A 50%, #1F3055 100%);
    }

    /* === Header === */
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    .main-header img {
        max-width: 220px;
        margin-bottom: 0.5rem;
    }
    .main-title {
        font-family: 'Georgia', 'Times New Roman', serif;
        font-size: 2.2rem;
        font-weight: 700;
        color: var(--dourado);
        letter-spacing: 2px;
        margin: 0.5rem 0 0.2rem 0;
    }
    .main-subtitle {
        font-size: 0.95rem;
        color: var(--cinza-claro);
        letter-spacing: 1px;
        margin-bottom: 1rem;
    }

    /* === Separador dourado === */
    .gold-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--dourado), transparent);
        margin: 1.5rem 0;
        border: none;
    }

    /* === Labels === */
    .stSelectbox label, .stTextInput label {
        color: var(--branco) !important;
        font-weight: 600;
        font-size: 1rem;
        letter-spacing: 0.5px;
    }

    /* === Selectbox === */
    .stSelectbox > div > div {
        background-color: #0F1B2E;
        border: 1px solid var(--dourado);
        color: var(--branco);
        border-radius: 8px;
    }

    /* === Botão principal === */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--dourado) 0%, var(--dourado-hover) 100%) !important;
        color: #1B2A4A !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.7rem 2rem !important;
        letter-spacing: 1px !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 15px rgba(255, 200, 36, 0.4) !important;
    }

    /* === Botão download === */
    .stDownloadButton > button {
        background: transparent !important;
        border: 2px solid var(--dourado) !important;
        color: var(--dourado) !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.3s ease !important;
        width: 100%;
    }
    .stDownloadButton > button:hover {
        background: var(--dourado) !important;
        color: #1B2A4A !important;
    }

    /* === Progress bar === */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--dourado), var(--dourado-hover)) !important;
    }

    /* === Alertas === */
    .stSuccess {
        background-color: rgba(255, 200, 36, 0.1) !important;
        border: 1px solid var(--dourado) !important;
        color: var(--dourado) !important;
        border-radius: 8px;
    }

    /* === Spinner === */
    .stSpinner > div {
        border-top-color: var(--dourado) !important;
    }

    /* === Status text === */
    .status-text {
        color: var(--cinza-claro);
        font-size: 0.9rem;
        padding: 0.3rem 0;
    }

    /* === Footer === */
    .footer {
        text-align: center;
        padding: 2rem 0 1rem 0;
        color: #666;
        font-size: 0.8rem;
    }
    .footer a {
        color: var(--dourado);
        text-decoration: none;
    }

    /* === Esconde elementos padrão do Streamlit === */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* === Info box === */
    .stInfo {
        background-color: rgba(255, 200, 36, 0.05) !important;
        border: 1px solid rgba(255, 200, 36, 0.3) !important;
        color: var(--cinza-claro) !important;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Logo e Header
# ---------------------------------------------------------------------------

def _get_logo_base64():
    """Retorna o logo em base64 para exibição inline."""
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.isfile(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


logo_b64 = _get_logo_base64()

header_html = '<div class="main-header">'
if logo_b64:
    header_html += f'<img src="data:image/png;base64,{logo_b64}" alt="Rebechi & Silva">'
header_html += """
    <div class="main-title">DIAGNÓSTICO TRIBUTÁRIO</div>
    <div class="main-subtitle">Rebechi & Silva Advogados Associados</div>
</div>
<div class="gold-divider"></div>
"""
st.markdown(header_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cliente selection
# ---------------------------------------------------------------------------

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

st.markdown("<br>", unsafe_allow_html=True)

if st.button("⚖️  Gerar Apresentação", type="primary"):
    with st.spinner("Gerando apresentação..."):
        progress = st.progress(0)

        # 1. Ler dados brutos
        st.markdown('<p class="status-text">📋 Lendo dados da planilha...</p>', unsafe_allow_html=True)
        raw_data = read_client_data(selected)
        progress.progress(20)

        # 2. Gerar gráficos (usa dados numéricos brutos)
        st.markdown('<p class="status-text">📊 Gerando gráficos...</p>', unsafe_allow_html=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            chart_data = _build_chart_data(raw_data)
            chart_paths = generate_all_charts(chart_data, temp_dir)

            charts = {}
            if "donut" in chart_paths:
                charts["donut_chart"] = chart_paths["donut"]
            if "gauge" in chart_paths:
                charts["gauge_chart"] = chart_paths["gauge"]
            if "bar" in chart_paths:
                charts["bar_chart"] = chart_paths["bar"]
            progress.progress(40)

            # 3. Processar dados para slides
            st.markdown('<p class="status-text">⚙️ Processando dados...</p>', unsafe_allow_html=True)
            data = process_data(raw_data)
            progress.progress(60)

            # 4. PPTX
            st.markdown('<p class="status-text">📑 Montando apresentação...</p>', unsafe_allow_html=True)
            nome = raw_data.get("dados_gerais", {}).get("nome_cliente", "Cliente")
            safe_name = nome.replace(" ", "_").replace("/", "_")
            output_pptx = os.path.join(OUTPUT_DIR, f"Diagnostico_{safe_name}.pptx")
            update_presentation(data, charts, output_pptx)
            progress.progress(80)

            # 5. PDF
            st.markdown('<p class="status-text">📄 Convertendo para PDF...</p>', unsafe_allow_html=True)
            output_pdf = convert_to_pdf(output_pptx, OUTPUT_DIR)
            progress.progress(100)

    st.success(f"✅ Apresentação gerada para **{nome}**!")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        with open(output_pptx, "rb") as f:
            st.download_button(
                label="📥 Baixar PPTX",
                data=f,
                file_name=os.path.basename(output_pptx),
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )

    with col2:
        if output_pdf and os.path.exists(output_pdf):
            with open(output_pdf, "rb") as f:
                st.download_button(
                    label="📥 Baixar PDF",
                    data=f,
                    file_name=os.path.basename(output_pdf),
                    mime="application/pdf",
                )
        else:
            st.info("PDF não disponível (LibreOffice não instalado)")

# Footer
st.markdown("""
<div class="gold-divider"></div>
<div class="footer">
    © 2026 Rebechi & Silva Advogados Associados
</div>
""", unsafe_allow_html=True)
