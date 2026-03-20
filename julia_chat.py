"""Interface de chat Streamlit com a assistente Júlia.

Acesso restrito com login e senha. Conversa com a Dra. Mônica,
coleta instruções de modificação, e gera a apresentação.
"""

import os
import tempfile
import logging
import hashlib

import streamlit as st

from julia_brain import JuliaBrain
from config import OUTPUT_DIR
from sheets_reader import read_client_data
from data_processor import process_data
from chart_generator import generate_all_charts
from slide_updater import update_presentation
from pdf_converter import convert_to_pdf
from main import _build_chart_data

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credenciais de acesso (hash SHA-256 das senhas)
# ---------------------------------------------------------------------------

AUTHORIZED_USERS = {
    "alexandre@rebechisilva.com.br": {
        "name": "Dr. Alexandre Silva",
        "password_hash": hashlib.sha256("RS@2026adv".encode()).hexdigest(),
    },
    "monica@rebechisilva.com.br": {
        "name": "Dra. Mônica",
        "password_hash": hashlib.sha256("RS@2026adv".encode()).hexdigest(),
    },
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Assistente Júlia | Rebechi & Silva",
    page_icon="⚖️",
    layout="centered",
)

# ---------------------------------------------------------------------------
# CSS — Identidade visual Rebechi & Silva
# ---------------------------------------------------------------------------

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
<style>
    /* ============================================================
       IDENTIDADE VISUAL — Rebechi & Silva Advogados Associados
       Cores e fontes extraídas do template de apresentação
       ============================================================ */

    :root {
        --fundo-escuro: #1B2A4A;
        --fundo-profundo: #0F1B2E;
        --dourado: #FFC824;
        --dourado-hover: #E6B420;
        --vermelho: #F07070;
        --verde: #4CAF50;
        --branco: #FFFFFF;
        --cinza: #888888;
    }

    /* === Fonte Montserrat em tudo === */
    html, body, [class*="css"], .stApp,
    h1, h2, h3, h4, p, span, label, input, textarea, button, a {
        font-family: 'Montserrat', sans-serif !important;
    }

    /* === Fundo gradiente navy === */
    .stApp {
        background: linear-gradient(160deg, var(--fundo-profundo) 0%, var(--fundo-escuro) 40%, #1F3055 100%);
    }

    /* === Texto geral branco === */
    h1, h2, h3, p, span, label, .stMarkdown, .stTextInput label,
    [data-testid="stFormSubmitButton"] p {
        color: var(--branco) !important;
    }

    /* === Chat messages — vidro escuro com borda dourada sutil === */
    [data-testid="stChatMessage"] {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 200, 36, 0.15);
        border-radius: 14px;
        margin-bottom: 0.6rem;
        padding: 1rem 1.2rem !important;
    }
    [data-testid="stChatMessage"] p {
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* === Botões — dourado Rebechi com texto navy === */
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #FFC824, #E6B420) !important;
        color: var(--fundo-escuro) !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem 2rem !important;
        font-size: 1rem !important;
        cursor: pointer !important;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 8px rgba(255, 200, 36, 0.3);
        transition: all 0.2s ease;
    }
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background: linear-gradient(135deg, #E6B420, #D4A41C) !important;
        color: var(--fundo-escuro) !important;
        box-shadow: 0 4px 14px rgba(255, 200, 36, 0.4);
        transform: translateY(-1px);
    }

    /* === Botões de download === */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #FFC824, #E6B420) !important;
        color: var(--fundo-escuro) !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem 2rem !important;
        font-size: 1rem !important;
        min-height: 48px !important;
        box-shadow: 0 2px 8px rgba(255, 200, 36, 0.3);
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #E6B420, #D4A41C) !important;
        box-shadow: 0 4px 14px rgba(255, 200, 36, 0.4);
    }

    /* === Inputs de texto — login === */
    .stTextInput input {
        color: var(--branco) !important;
        background-color: rgba(255, 255, 255, 0.07) !important;
        border: 1px solid rgba(255, 200, 36, 0.25) !important;
        border-radius: 10px !important;
        padding: 0.7rem 1rem !important;
        font-size: 0.95rem !important;
    }
    .stTextInput input:focus {
        border-color: var(--dourado) !important;
        box-shadow: 0 0 0 2px rgba(255, 200, 36, 0.15) !important;
    }
    .stTextInput input::placeholder {
        color: rgba(255,255,255,0.35) !important;
    }

    /* === Header com logo === */
    .julia-header {
        text-align: center;
        padding: 1.5rem 0 1rem;
    }
    .julia-header img {
        max-width: 200px;
        margin-bottom: 0.8rem;
    }
    .julia-header h1 {
        color: var(--dourado) !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 800 !important;
        font-size: 2rem;
        margin-bottom: 0.2rem;
        letter-spacing: 1.5px;
    }
    .julia-header .subtitle {
        color: rgba(255,255,255,0.5) !important;
        font-size: 0.85rem;
        font-weight: 400;
        margin-top: 0;
        letter-spacing: 0.5px;
    }

    /* === Login container — vidro com borda dourada === */
    .login-box {
        max-width: 440px;
        margin: 3rem auto;
        padding: 2.5rem 2rem;
        background: rgba(255,255,255,0.04);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255,200,36,0.2);
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .login-box img {
        max-width: 200px;
        margin-bottom: 1.2rem;
    }
    .login-box h2 {
        color: var(--dourado) !important;
        font-weight: 700 !important;
        font-size: 1.5rem;
        margin-bottom: 0.3rem;
    }
    .login-box .sub {
        color: rgba(255,255,255,0.45) !important;
        font-size: 0.8rem;
        margin-bottom: 1.5rem;
    }

    /* === Sidebar — navy profundo === */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--fundo-profundo), #0A1220) !important;
        border-right: 1px solid rgba(255,200,36,0.1);
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
    }

    /* === Chat input — fundo branco, texto escuro para legibilidade === */
    [data-testid="stChatInput"] {
        background-color: var(--branco) !important;
        border-radius: 14px !important;
        border: 2px solid rgba(255, 200, 36, 0.3) !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    }
    [data-testid="stChatInput"] textarea {
        color: var(--fundo-escuro) !important;
        background-color: var(--branco) !important;
        border: none !important;
        font-size: 0.95rem !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #999 !important;
    }
    /* Botão de enviar no chat input */
    [data-testid="stChatInput"] button {
        background-color: var(--dourado) !important;
        border-radius: 50% !important;
    }
    [data-testid="stChatInput"] button svg {
        fill: var(--fundo-escuro) !important;
    }

    /* === ESCONDER Manage App, footer, toolbar, menu === */
    [data-testid="manage-app-button"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stHeader"],
    [data-testid="stActionButton"],
    [class*="_profileContainer"],
    [class*="profileContainer"],
    [class*="StatusWidget"],
    [class*="stToolbar"],
    [class*="manage-app"],
    .stDeployButton,
    .stAppDeployButton,
    footer,
    .reportview-container .main footer,
    #MainMenu,
    header {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
        position: fixed !important;
        top: -9999px !important;
        left: -9999px !important;
        z-index: -9999 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Força o conteúdo principal a ocupar toda a tela */
    .stApp > header {
        display: none !important;
    }
    .stApp [data-testid="stBottom"] > div {
        /* Garante que apenas o chat input fica no bottom, sem toolbar */
    }

    /* === Spinner dourado === */
    .stSpinner > div {
        border-top-color: var(--dourado) !important;
    }

    /* === Divider na sidebar === */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,200,36,0.15) !important;
    }

    /* === Scrollbar estilizada === */
    ::-webkit-scrollbar {
        width: 6px;
    }
    ::-webkit-scrollbar-track {
        background: var(--fundo-profundo);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255,200,36,0.3);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255,200,36,0.5);
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_logo_base64() -> str:
    """Retorna logo como base64 para usar em HTML."""
    import base64
    logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
    if os.path.isfile(logo_path):
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""


# ---------------------------------------------------------------------------
# Login com email + senha
# ---------------------------------------------------------------------------

def check_login() -> bool:
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.user_name = ""
    return st.session_state.logged_in


def show_login():
    logo_b64 = _get_logo_base64()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" />' if logo_b64 else ""

    st.markdown(f"""
    <div class="login-box">
        {logo_html}
        <h2>Assistente Júlia</h2>
        <p class="sub">Acesso restrito</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="seu.email@rebechisilva.com.br")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            email_clean = email.strip().lower()
            pwd_hash = hashlib.sha256(password.encode()).hexdigest()

            user = AUTHORIZED_USERS.get(email_clean)
            if user and user["password_hash"] == pwd_hash:
                st.session_state.logged_in = True
                st.session_state.user_email = email_clean
                st.session_state.user_name = user["name"]
                st.rerun()
            else:
                st.error("Email ou senha incorretos.")


# ---------------------------------------------------------------------------
# Inicialização
# ---------------------------------------------------------------------------

def init_julia():
    if "julia" not in st.session_state:
        api_key = st.secrets.get("ANTHROPIC_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
        if not api_key:
            st.error("ANTHROPIC_API_KEY nao configurada. Adicione nas secrets.")
            st.stop()
        st.session_state.julia = JuliaBrain(
            api_key=api_key,
            user_name=st.session_state.get("user_name", ""),
            user_email=st.session_state.get("user_email", ""),
        )

    if "messages" not in st.session_state:
        greeting = st.session_state.julia.get_greeting()
        st.session_state.messages = [{"role": "assistant", "content": greeting}]

    if "generating" not in st.session_state:
        st.session_state.generating = False


# ---------------------------------------------------------------------------
# Geração da apresentação
# ---------------------------------------------------------------------------

# Mapeamento: slide visível → (chave no raw_data, campo)
# Campos simples ficam em dados_gerais; cenários usam índice na lista.
_FIELD_TO_DATA = {
    # Slide 1 - Capa
    (1, "nome_cliente"): ("dados_gerais", "nome_cliente"),

    # Slide 3 - Indicadores (slide_updater lê de indicadores_resumo)
    (3, "faturamento_valor"): ("indicadores_resumo", "faturamento_valor"),
    (3, "tributos_valor"): ("indicadores_resumo", "tributos_valor"),
    (3, "aliquota_efetiva"): ("indicadores_resumo", "aliquota_efetiva"),
    (3, "margem_contribuicao_valor"): ("indicadores_resumo", "margem_contribuicao_valor"),
    (3, "margem_contribuicao_pct"): ("indicadores_resumo", "margem_contribuicao_pct"),

    # Slide 5 - Tabela de indicadores (slide_updater lê de indicadores_resumo)
    (5, "receita_valor"): ("indicadores_resumo", "receita_valor"),
    (5, "receita_pct"): ("indicadores_resumo", "receita_pct"),
    (5, "custo_variavel_valor"): ("indicadores_resumo", "custo_variavel_valor"),
    (5, "custo_variavel_pct"): ("indicadores_resumo", "custo_variavel_pct"),
    (5, "custo_fixo_valor"): ("indicadores_resumo", "custo_fixo_valor"),
    (5, "custo_fixo_pct"): ("indicadores_resumo", "custo_fixo_pct"),
    (5, "imposto_lucro_valor"): ("indicadores_resumo", "imposto_lucro_valor"),
    (5, "imposto_lucro_pct"): ("indicadores_resumo", "imposto_lucro_pct"),
    (5, "lucro_valor"): ("indicadores_resumo", "lucro_valor"),
    (5, "lucro_pct"): ("indicadores_resumo", "lucro_pct"),

    # Slides 10, 12, 14 - Cenários comparativos
    # Estes são tratados via _apply_scenario_modification (ver abaixo)
    (10, "lr_pct"): ("__cenario__", 0),
    (10, "lp_pct"): ("__cenario__", 0),
    (10, "diferenca_texto"): ("__cenario__", 0),
    (10, "cenario_nome"): ("__cenario__", 0),
    (12, "lr_pct"): ("__cenario__", 1),
    (12, "lp_pct"): ("__cenario__", 1),
    (12, "diferenca_texto"): ("__cenario__", 1),
    (12, "cenario_nome"): ("__cenario__", 1),
    (14, "lr_pct"): ("__cenario__", 2),
    (14, "lp_pct"): ("__cenario__", 2),
    (14, "diferenca_texto"): ("__cenario__", 2),
    (14, "cenario_nome"): ("__cenario__", 2),

    # Slide 19 - Gestão de Passivos
    (19, "federal"): ("gestao_passivos", "federal"),
    (19, "estadual"): ("gestao_passivos", "estadual"),

    # Slide 24 - Reforma Tributária
    (24, "aliquotas_texto"): ("indicadores_resumo", "aliquotas_texto"),

    # Slide 26 - Síntese
    (26, "paragrafo_1"): ("sintese_diagnostico", "paragrafo_1"),
    (26, "paragrafo_2"): ("sintese_diagnostico", "paragrafo_2"),
    (26, "badge_1"): ("sintese_diagnostico", "badge_1"),
    (26, "badge_2"): ("sintese_diagnostico", "badge_2"),
    (26, "badge_3"): ("sintese_diagnostico", "badge_3"),
    (26, "badge_4"): ("sintese_diagnostico", "badge_4"),
}


def _apply_modifications(raw_data: dict, modifications: list) -> dict:
    """Aplica modificações da Júlia sobre os dados brutos antes de gerar."""
    for mod in modifications:
        slide = mod.get("slide")
        campo = mod.get("campo")
        valor = mod.get("valor")
        if not (slide and campo and valor is not None):
            logger.warning("Modificação ignorada (dados incompletos): %s", mod)
            continue

        logger.info("Aplicando: slide=%s, campo='%s', valor='%s'", slide, campo, valor)

        key = (slide, campo)
        if key in _FIELD_TO_DATA:
            section, field_or_idx = _FIELD_TO_DATA[key]

            if section == "__cenario__":
                # Cenários comparativos: field_or_idx é o índice na lista
                idx = field_or_idx
                if "cenarios_comparativos" not in raw_data:
                    raw_data["cenarios_comparativos"] = []
                # Garante que a lista tem elementos suficientes
                while len(raw_data["cenarios_comparativos"]) <= idx:
                    raw_data["cenarios_comparativos"].append({})
                raw_data["cenarios_comparativos"][idx][campo] = valor
                logger.info("  → cenarios_comparativos[%d]['%s'] = '%s'", idx, campo, valor)
            else:
                if section not in raw_data:
                    raw_data[section] = {}
                raw_data[section][field_or_idx] = valor
                logger.info("  → %s['%s'] = '%s'", section, field_or_idx, valor)
        else:
            # Tenta aplicar diretamente em dados_gerais como fallback
            if "dados_gerais" not in raw_data:
                raw_data["dados_gerais"] = {}
            raw_data["dados_gerais"][campo] = valor
            logger.info("  → dados_gerais['%s'] = '%s' (fallback)", campo, valor)

    return raw_data


def generate_presentation(client_name: str, modifications: list = None) -> tuple:
    """Gera PPTX e PDF. Retorna (pptx_path, pdf_path)."""
    logger.info("=== Gerando apresentação para: '%s' ===", client_name)

    raw_data = read_client_data(client_name)

    # Sobrescreve o nome do cliente com o que a Júlia informou
    if "dados_gerais" not in raw_data:
        raw_data["dados_gerais"] = {}
    raw_data["dados_gerais"]["nome_cliente"] = client_name
    logger.info("nome_cliente definido como: '%s'", client_name)

    # Aplica modificações individuais pedidas pela Júlia
    if modifications:
        logger.info("Aplicando %d modificações", len(modifications))
        raw_data = _apply_modifications(raw_data, modifications)

    chart_data = _build_chart_data(raw_data)

    with tempfile.TemporaryDirectory() as temp_dir:
        charts = generate_all_charts(chart_data, temp_dir)
        processed = process_data(raw_data)

        # Garante que nome_cliente sobrevive ao processamento
        if "dados_gerais" not in processed:
            processed["dados_gerais"] = {}
        processed["dados_gerais"]["nome_cliente"] = client_name
        logger.info("nome_cliente pós-processamento: '%s'",
                     processed.get("dados_gerais", {}).get("nome_cliente", "???"))

        safe_name = client_name.replace(" ", "_").replace("/", "_")
        pptx_path = os.path.join(OUTPUT_DIR, f"Diagnostico_{safe_name}.pptx")
        update_presentation(processed, charts, pptx_path)

    pdf_path = convert_to_pdf(pptx_path, OUTPUT_DIR)
    return pptx_path, pdf_path or ""


def _handle_generation(action: dict, response: str):
    """Executa geração e mostra botões de download."""
    client_name = action.get("client_name") or "Cliente"
    logger.info("_handle_generation: action=%s", action)
    logger.info("_handle_generation: client_name='%s'", client_name)
    clean_response = response.split("```json")[0].strip()
    st.markdown(clean_response)

    modifications = action.get("modifications", [])

    with st.spinner(f"Gerando apresentação para {client_name}..."):
        try:
            pptx_path, pdf_path = generate_presentation(client_name, modifications)

            st.markdown(
                f"\n\nPronto! A apresentação de **{client_name}** "
                f"foi gerada com sucesso!"
            )

            # Botões de download
            col1, col2 = st.columns(2)
            with col1:
                with open(pptx_path, "rb") as f:
                    st.download_button(
                        "Baixar Apresentacao PPTX",
                        f.read(),
                        file_name=os.path.basename(pptx_path),
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        key=f"dl_pptx_{len(st.session_state.messages)}",
                    )
            if pdf_path and os.path.isfile(pdf_path):
                with col2:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "Baixar PDF",
                            f.read(),
                            file_name=os.path.basename(pdf_path),
                            mime="application/pdf",
                            key=f"dl_pdf_{len(st.session_state.messages)}",
                        )

            st.session_state.messages.append({
                "role": "assistant",
                "content": clean_response + f"\n\nApresentação de **{client_name}** gerada!",
                "pptx_path": pptx_path,
                "pdf_path": pdf_path,
            })

        except Exception as e:
            st.error(f"Erro ao gerar: {e}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Desculpe, houve um erro: {e}",
            })


# ---------------------------------------------------------------------------
# Chat principal
# ---------------------------------------------------------------------------

def show_chat():
    # Header com logo
    logo_b64 = _get_logo_base64()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" />' if logo_b64 else ""

    st.markdown(f"""
    <div class="julia-header">
        {logo_html}
        <h1>Assistente Júlia</h1>
        <p class="subtitle">Rebechi & Silva Advogados Associados</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown(f"**{st.session_state.user_name}**")
        st.caption(st.session_state.user_email)
        st.divider()

        if st.button("Nova conversa"):
            st.session_state.julia.reset()
            greeting = st.session_state.julia.get_greeting()
            st.session_state.messages = [{"role": "assistant", "content": greeting}]
            st.session_state.generating = False
            st.rerun()

        if st.button("Sair"):
            for key in ["logged_in", "user_email", "user_name", "julia", "messages", "generating"]:
                st.session_state.pop(key, None)
            st.rerun()

    # Renderizar mensagens anteriores
    for i, msg in enumerate(st.session_state.messages):
        avatar = "👩‍💼" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

            # Botões de download para mensagens que já geraram
            if msg.get("pptx_path") and os.path.isfile(msg["pptx_path"]):
                col1, col2 = st.columns(2)
                with col1:
                    with open(msg["pptx_path"], "rb") as f:
                        st.download_button(
                            "Baixar Apresentacao PPTX",
                            f.read(),
                            file_name=os.path.basename(msg["pptx_path"]),
                            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            key=f"hist_pptx_{i}",
                        )
                if msg.get("pdf_path") and os.path.isfile(msg["pdf_path"]):
                    with col2:
                        with open(msg["pdf_path"], "rb") as f:
                            st.download_button(
                                "Baixar PDF",
                                f.read(),
                                file_name=os.path.basename(msg["pdf_path"]),
                                mime="application/pdf",
                                key=f"hist_pdf_{i}",
                            )

    # Input do chat
    if prompt := st.chat_input("Digite sua mensagem..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="👩‍💼"):
            with st.spinner("Júlia está pensando..."):
                response = st.session_state.julia.chat(prompt)

            action = JuliaBrain.extract_action(response)

            if action and action.get("action") in ("load_from_sheets", "generate"):
                _handle_generation(action, response)
            else:
                st.markdown(response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not check_login():
        show_login()
        return

    init_julia()
    show_chat()


if __name__ == "__main__":
    main()
