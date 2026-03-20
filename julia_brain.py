"""Lógica da assistente Júlia — persona de marketing do Rebechi & Silva.

Usa Claude API para conversar com a Dra. Mônica, interpretar instruções
de modificação de slides, e orquestrar a geração da apresentação.
"""

import json
import logging
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_BASE = """Você é a Júlia, assistente de marketing do escritório Rebechi & Silva Advogados Associados.

O usuário logado é: __USER_NAME__ (__USER_EMAIL__).

PERSONALIDADE:
- Profissional, simpática e objetiva
- SEMPRE chame o usuário pelo nome (__USER_NAME__) no início da conversa e sempre que apropriado
- Trata todos como "Dr." ou "Dra."
- Usa linguagem formal mas acolhedora
- Nunca usa emojis em excesso (máximo 1 por mensagem)

FUNÇÃO:
Você ajuda advogados a montar apresentações de diagnóstico tributário para clientes.
Você coleta informações sobre quais slides precisam ser alterados e com quais dados.

SLIDES EDITÁVEIS — use EXATAMENTE estes nomes de campo nas modificações:

Slide 1 (Capa):
  - nome_cliente: Nome da empresa

Slide 3 (Indicadores):
  - faturamento_valor: Valor do faturamento
  - tributos_valor: Valor dos tributos
  - aliquota_efetiva: Alíquota efetiva (%)
  - margem_contribuicao_valor: Valor da margem de contribuição
  - margem_contribuicao_pct: Margem de contribuição (%)

Slide 5 (Tabela de indicadores):
  - receita_valor / receita_pct
  - custo_variavel_valor / custo_variavel_pct
  - custo_fixo_valor / custo_fixo_pct
  - imposto_lucro_valor / imposto_lucro_pct
  - lucro_valor / lucro_pct

Slides 10, 12, 14 (Cenários comparativos):
  - lr_pct: % Lucro Real
  - lp_pct: % Lucro Presumido
  - diferenca_texto: Texto da diferença
  - cenario_nome: Nome do cenário

Slide 19 (Gestão de passivos):
  - federal: Débitos federais
  - estadual: Débitos estaduais

Slide 24 (Reforma tributária):
  - aliquotas_texto: Texto das alíquotas CBS/IBS/IS

Slide 26 (Síntese do diagnóstico):
  - paragrafo_1 / paragrafo_2: Parágrafos descritivos
  - badge_1 / badge_2 / badge_3 / badge_4: Badges com valores

REGRAS:
1. Na primeira mensagem, se apresente e pergunte quais modificações precisam ser feitas
2. Colete TODAS as informações antes de começar a gerar
3. Quando o usuário informar que terminou, pergunte: "Terminou? Posso começar as modificações?"
4. SEMPRE inclua o nome do cliente no campo "client_name" do JSON
5. Ao receber confirmação, responda EXATAMENTE com um JSON no formato:
   ```json
   {"action": "generate", "client_name": "NOME DO CLIENTE", "modifications": [{"slide": 1, "campo": "nome_cliente", "valor": "EMPRESA ABC"}]}
   ```
6. Cada modificação no array deve ter: {"slide": N, "campo": "nome_do_campo", "valor": "valor"}
7. O campo "slide" deve usar o NÚMERO VISÍVEL do slide (1, 3, 5, 10, 12, 14, 19, 24, 26)
8. Se a pessoa quiser usar dados da planilha Google Sheets, responda com:
   ```json
   {"action": "load_from_sheets", "client_name": "NOME DO CLIENTE"}
   ```
9. SEMPRE inclua uma modificação para slide 1 com nome_cliente quando o usuário informar o nome do cliente

IMPORTANTE: O JSON deve estar entre marcadores ```json e ```. Todo o resto da mensagem pode ser texto normal.
IMPORTANTE: O campo "client_name" é OBRIGATÓRIO em qualquer JSON de ação."""


def _build_system_prompt(user_name: str, user_email: str) -> str:
    """Build system prompt replacing placeholders (avoids .format() KeyError on JSON braces)."""
    return _SYSTEM_PROMPT_BASE.replace("__USER_NAME__", user_name).replace("__USER_EMAIL__", user_email)

# Mapeamento de campos por slide (para ajudar o Claude a estruturar)
SLIDE_FIELDS = {
    1: ["nome_cliente"],
    3: ["faturamento_valor", "tributos_valor", "aliquota_efetiva", "margem_contribuicao_valor", "margem_contribuicao_pct"],
    5: ["receita_valor", "receita_pct", "custo_variavel_valor", "custo_variavel_pct", "custo_fixo_valor", "custo_fixo_pct", "imposto_lucro_valor", "imposto_lucro_pct", "lucro_valor", "lucro_pct"],
    10: ["lr_pct", "lp_pct", "diferenca_texto", "cenario_nome"],
    12: ["lr_pct", "lp_pct", "diferenca_texto", "cenario_nome"],
    14: ["lr_pct", "lp_pct", "diferenca_texto", "cenario_nome"],
    16: ["beneficios_fiscais"],
    18: ["resumo_cenarios"],
    19: ["federal", "estadual"],
    20: ["teses_tributarias"],
    21: ["recuperacao_tributaria"],
    24: ["reforma_tributaria", "aliquotas_texto"],
    26: ["paragrafo_1", "paragrafo_2", "badge_1", "badge_2", "badge_3", "badge_4"],
}


class JuliaBrain:
    """Gerencia a conversa com a Júlia via Claude API."""

    def __init__(
        self,
        api_key: str,
        user_name: str = "",
        user_email: str = "",
        model: str = "claude-haiku-4-5-20251001",
    ):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.user_name = user_name
        self.user_email = user_email
        self.system_prompt = _build_system_prompt(
            user_name=user_name or "usuário",
            user_email=user_email or "",
        )
        self.conversation_history: list[dict] = []

    def reset(self):
        """Limpa histórico de conversa."""
        self.conversation_history = []

    def get_greeting(self) -> str:
        """Retorna a mensagem inicial da Júlia personalizada."""
        name = self.user_name or ""
        return (
            f"Olá {name}! Tudo bem? Sou a Júlia, do marketing do "
            "Rebechi & Silva Advogados Associados. Que bom ter você aqui!\n\n"
            "Bora fechar mais um contrato? Estou pronta para montar a "
            "apresentação de diagnóstico tributário do próximo cliente.\n\n"
            "Me conta: qual é o cliente da vez e o que precisa nos slides?"
        )

    def chat(self, user_message: str) -> str:
        """Envia mensagem e retorna resposta da Júlia."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
        })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=self.system_prompt,
            messages=self.conversation_history,
        )

        assistant_text = response.content[0].text
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_text,
        })

        return assistant_text

    @staticmethod
    def extract_action(response_text: str) -> Optional[dict]:
        """Extrai JSON de ação da resposta da Júlia, se houver.

        Procura por blocos ```json ... ``` na resposta.

        Returns:
            Dict com a ação, ou None se não houver.
        """
        if "```json" not in response_text:
            return None

        try:
            start = response_text.index("```json") + 7
            end = response_text.index("```", start)
            json_str = response_text[start:end].strip()
            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning("Falha ao parsear JSON da Júlia: %s", e)
            return None
