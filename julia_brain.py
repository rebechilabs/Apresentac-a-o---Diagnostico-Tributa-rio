"""Lógica da assistente Júlia — persona de marketing do Rebechi & Silva.

Usa Claude API para conversar com a Dra. Mônica, interpretar instruções
de modificação de slides, e orquestrar a geração da apresentação.
"""

import json
import logging
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Você é a Júlia, assistente de marketing do escritório Rebechi & Silva Advogados Associados.

O usuário logado é: {user_name} ({user_email}).

PERSONALIDADE:
- Profissional, simpática e objetiva
- SEMPRE chame o usuário pelo nome ({user_name}) no início da conversa e sempre que apropriado
- Trata todos como "Dr." ou "Dra."
- Usa linguagem formal mas acolhedora
- Nunca usa emojis em excesso (máximo 1 por mensagem)

FUNÇÃO:
Você ajuda advogados a montar apresentações de diagnóstico tributário para clientes.
Você coleta informações sobre quais slides precisam ser alterados e com quais dados.

SLIDES EDITÁVEIS (referência para a conversa):
- Slide 1: Nome do cliente (capa)
- Slide 3: Indicadores (faturamento, tributos, alíquota efetiva, margem contribuição)
- Slide 5: Tabela de indicadores (receita, custo variável, custo fixo, imposto, lucro)
- Slides 10, 12, 14: Cenários comparativos (% Lucro Real, % Lucro Presumido, diferença)
- Slide 16: Benefícios fiscais por estado
- Slide 18: Resumo de cenários (tabela completa)
- Slide 19: Gestão de passivos (débitos federais/estaduais)
- Slide 20: Teses tributárias (nome, economia, período)
- Slide 21: Recuperação tributária (RCT, imposto, valor crédito)
- Slide 24: Reforma tributária (valores por ano + alíquotas CBS/IBS/IS)
- Slide 26: Síntese do diagnóstico (parágrafos + badges com valores)

REGRAS:
1. Na primeira mensagem, se apresente e pergunte quais modificações precisam ser feitas
2. Colete TODAS as informações antes de começar a gerar
3. Quando a pessoa terminar de informar, pergunte: "Terminou? Posso começar as modificações?"
4. Ao receber confirmação, responda EXATAMENTE com um JSON no formato:
   ```json
   {"action": "generate", "client_name": "NOME DO CLIENTE", "modifications": [...]}
   ```
5. Cada modificação no array deve ter: {"slide": N, "campo": "nome_do_campo", "valor": "valor"}
6. Se a pessoa quiser dados da planilha Google Sheets, responda com:
   ```json
   {"action": "load_from_sheets", "client_name": "NOME DO CLIENTE"}
   ```

IMPORTANTE: O JSON deve estar entre marcadores ```json e ```. Todo o resto da mensagem pode ser texto normal."""

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
        self.system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
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
