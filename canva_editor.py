"""Wrapper para a Canva Connect API.

Gerencia edição de designs via REST API: duplicar template, editar texto,
commitar alterações e exportar para PDF/PPTX.
"""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CANVA_API_BASE = "https://api.canva.com/rest/v1"
TEMPLATE_DESIGN_ID = "DAHEH3eEwxw"


class CanvaEditor:
    """Cliente para a Canva Connect API."""

    def __init__(self, api_token: str):
        self.token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    # ------------------------------------------------------------------
    # Design operations
    # ------------------------------------------------------------------

    def get_design(self, design_id: str) -> dict:
        """Retorna metadata de um design."""
        resp = self.session.get(f"{CANVA_API_BASE}/designs/{design_id}")
        resp.raise_for_status()
        return resp.json()

    def duplicate_design(self, design_id: str, title: str) -> str:
        """Duplica um design e retorna o ID da cópia."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/designs",
            json={
                "design_type": "presentation",
                "title": title,
                "source_design_id": design_id,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        new_id = data.get("design", {}).get("id", "")
        logger.info("Design duplicado: %s → %s", design_id, new_id)
        return new_id

    # ------------------------------------------------------------------
    # Editing transactions
    # ------------------------------------------------------------------

    def start_transaction(self, design_id: str) -> tuple[str, list]:
        """Inicia transação de edição. Retorna (transaction_id, elements)."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/designs/{design_id}/editing_transactions",
        )
        resp.raise_for_status()
        data = resp.json()
        tx_id = data.get("transaction_id", "")
        elements = data.get("elements", [])
        logger.info("Transação iniciada: %s (%d elementos)", tx_id, len(elements))
        return tx_id, elements

    def find_and_replace(
        self,
        tx_id: str,
        element_id: str,
        find_text: str,
        replace_text: str,
    ) -> dict:
        """Substitui texto dentro de um elemento."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/editing_transactions/{tx_id}/operations",
            json={
                "operations": [{
                    "type": "find_and_replace_text",
                    "element_id": element_id,
                    "find_text": find_text,
                    "replace_text": replace_text,
                }],
            },
        )
        resp.raise_for_status()
        return resp.json()

    def replace_text(self, tx_id: str, element_id: str, text: str) -> dict:
        """Substitui todo o texto de um elemento."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/editing_transactions/{tx_id}/operations",
            json={
                "operations": [{
                    "type": "replace_text",
                    "element_id": element_id,
                    "text": text,
                }],
            },
        )
        resp.raise_for_status()
        return resp.json()

    def batch_operations(self, tx_id: str, operations: list) -> dict:
        """Executa múltiplas operações em batch."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/editing_transactions/{tx_id}/operations",
            json={"operations": operations},
        )
        resp.raise_for_status()
        return resp.json()

    def commit(self, tx_id: str) -> dict:
        """Salva as alterações da transação."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/editing_transactions/{tx_id}/commit",
        )
        resp.raise_for_status()
        logger.info("Transação %s commitada.", tx_id)
        return resp.json()

    def cancel(self, tx_id: str) -> dict:
        """Cancela a transação sem salvar."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/editing_transactions/{tx_id}/cancel",
        )
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_design(
        self,
        design_id: str,
        format_type: str = "pdf",
    ) -> Optional[str]:
        """Exporta design e retorna URL de download."""
        resp = self.session.post(
            f"{CANVA_API_BASE}/designs/{design_id}/exports",
            json={"format": {"type": format_type}},
        )
        resp.raise_for_status()
        data = resp.json()

        # Export pode ser assíncrono — poll até completar
        export_id = data.get("export", {}).get("id", "")
        if not export_id:
            return data.get("export", {}).get("url")

        for _ in range(30):
            time.sleep(2)
            check = self.session.get(
                f"{CANVA_API_BASE}/exports/{export_id}",
            )
            check.raise_for_status()
            status = check.json().get("export", {})
            if status.get("status") == "completed":
                return status.get("url")
            if status.get("status") == "failed":
                logger.error("Export falhou: %s", status)
                return None

        logger.error("Export timeout para design %s", design_id)
        return None

    # ------------------------------------------------------------------
    # High-level: editar template para um cliente
    # ------------------------------------------------------------------

    def edit_template_for_client(
        self,
        client_name: str,
        modifications: list[dict],
    ) -> dict:
        """Fluxo completo: duplica template → edita → commita.

        Args:
            client_name: Nome do cliente (usado no título da cópia).
            modifications: Lista de dicts com keys:
                - find_text: texto a encontrar
                - replace_text: texto substituto

        Returns:
            Dict com design_id, edit_url, e view_url do design editado.
        """
        # 1. Duplicar template
        title = f"Diagnóstico Tributário - {client_name}"
        new_design_id = self.duplicate_design(TEMPLATE_DESIGN_ID, title)

        # 2. Iniciar transação
        tx_id, elements = self.start_transaction(new_design_id)

        # 3. Aplicar modificações via find-and-replace
        operations = []
        for mod in modifications:
            # Procura o elemento que contém o texto
            for elem in elements:
                elem_text = elem.get("text", "")
                if mod["find_text"] in elem_text:
                    operations.append({
                        "type": "find_and_replace_text",
                        "element_id": elem["id"],
                        "find_text": mod["find_text"],
                        "replace_text": mod["replace_text"],
                    })
                    break

        if operations:
            self.batch_operations(tx_id, operations)

        # 4. Commitar
        self.commit(tx_id)

        # 5. Retornar URLs
        design_info = self.get_design(new_design_id)
        design = design_info.get("design", {})
        return {
            "design_id": new_design_id,
            "edit_url": design.get("edit_url", ""),
            "view_url": design.get("view_url", ""),
            "title": title,
        }
