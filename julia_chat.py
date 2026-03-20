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
from sheets_reader import list_clients, read_client_data
from data_processor import process_data
from chart_generator import generate_all_charts
from slide_updater import update_presentation
from pdf_converter import convert_to_pdf
from main import _build_chart_data

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
<style>
    /* === Cores === */
    :root {
        --fundo: #1B2A4A;
        --dourado: #FFC824;
        --dourado-hover: #E6B420;
        --branco: #FFFFFF;
    }

    /* === Fundo === */
    .stApp {
        background: linear-gradient(135deg, #0F1B2E 0%, #1B2A4A 50%, #1F3055 100%);
    }

    /* === Texto geral branco === */
    h1, h2, h3, p, span, label, .stMarkdown, .stTextInput label,
    [data-testid="stFormSubmitButton"] p {
        color: var(--branco) !important;
    }

    /* === Chat messages === */
    [data-testid="stChatMessage"] {
        background-color: rgba(255, 255, 255, 0.06) !important;
        border: 1px solid rgba(255, 200, 36, 0.2);
        border-radius: 12px;
        margin-bottom: 0.5rem;
    }

    /* === Todos os botões legíveis === */
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button {
        background-color: #FFC824 !important;
        color: #1B2A4A !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        font-size: 1rem !important;
        cursor: pointer !important;
    }
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #E6B420 !important;
        color: #1B2A4A !important;
    }

    /* === Botões de download === */
    .stDownloadButton > button {
        background-color: #FFC824 !important;
        color: #1B2A4A !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 2rem !important;
        font-size: 1rem !important;
        min-height: 45px !important;
    }
    .stDownloadButton > button:hover {
        background-color: #E6B420 !important;
    }

    /* === Inputs de texto === */
    .stTextInput input {
        color: white !important;
        background-color: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 200, 36, 0.3) !important;
        border-radius: 8px !important;
    }

    /* === Header com logo === */
    .julia-header {
        text-align: center;
        padding: 1rem 0;
    }
    .julia-header img {
        max-width: 180px;
        margin-bottom: 0.5rem;
    }
    .julia-header h1 {
        color: #FFC824 !important;
        font-size: 1.8rem;
        margin-bottom: 0.2rem;
        letter-spacing: 1px;
    }
    .julia-header .subtitle {
        color: rgba(255,255,255,0.6) !important;
        font-size: 0.85rem;
        margin-top: 0;
    }

    /* === Login container === */
    .login-box {
        max-width: 420px;
        margin: 3rem auto;
        padding: 2.5rem;
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,200,36,0.25);
        border-radius: 16px;
        text-align: center;
    }
    .login-box img {
        max-width: 200px;
        margin-bottom: 1rem;
    }
    .login-box h2 {
        color: #FFC824 !important;
        font-size: 1.4rem;
        margin-bottom: 0.3rem;
    }
    .login-box .sub {
        color: rgba(255,255,255,0.5) !important;
        font-size: 0.8rem;
        margin-bottom: 1.5rem;
    }

    /* === Sidebar === */
    [data-testid="stSidebar"] {
        background-color: #0F1B2E !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
    }

    /* === Chat input — fundo claro e texto escuro para legibilidade === */
    [data-testid="stChatInput"] {
        background-color: #FFFFFF !important;
        border-radius: 12px !important;
    }
    [data-testid="stChatInput"] textarea {
        color: #1B2A4A !important;
        background-color: #FFFFFF !important;
        border: none !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #888 !important;
    }

    /* === Esconder Manage App e footer === */
    [data-testid="manage-app-button"],
    footer, .reportview-container .main footer,
    #MainMenu {
        display: none !important;
        visibility: hidden !important;
    }

    /* === Spinner === */
    .stSpinner > div {
        border-top-color: #FFC824 !important;
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

def generate_presentation(client_name: str) -> tuple:
    """Gera PPTX e PDF. Retorna (pptx_path, pdf_path)."""
    raw_data = read_client_data(client_name)

    # Sobrescreve o nome do cliente com o que a Júlia informou
    if "dados_gerais" not in raw_data:
        raw_data["dados_gerais"] = {}
    raw_data["dados_gerais"]["nome_cliente"] = client_name

    chart_data = _build_chart_data(raw_data)

    with tempfile.TemporaryDirectory() as temp_dir:
        charts = generate_all_charts(chart_data, temp_dir)
        processed = process_data(raw_data)
        safe_name = client_name.replace(" ", "_").replace("/", "_")
        pptx_path = os.path.join(OUTPUT_DIR, f"Diagnostico_{safe_name}.pptx")
        update_presentation(processed, charts, pptx_path)

    pdf_path = convert_to_pdf(pptx_path, OUTPUT_DIR)
    return pptx_path, pdf_path or ""


def _handle_generation(action: dict, response: str):
    """Executa geração e mostra botões de download."""
    client_name = action.get("client_name", "Cliente")
    clean_response = response.split("```json")[0].strip()
    st.markdown(clean_response)

    with st.spinner(f"Gerando apresentação para {client_name}..."):
        try:
            pptx_path, pdf_path = generate_presentation(client_name)

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
