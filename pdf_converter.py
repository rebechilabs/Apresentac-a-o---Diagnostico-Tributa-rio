"""Converte .pptx para PDF usando LibreOffice CLI."""
import subprocess
import os
import shutil


def convert_to_pdf(pptx_path: str, output_dir: str = None) -> str:
    """Converte um arquivo .pptx para PDF.

    Retorna o caminho do PDF gerado, ou None se LibreOffice não estiver disponível.
    """
    if output_dir is None:
        output_dir = os.path.dirname(pptx_path)

    soffice = _find_soffice()
    if not soffice:
        print("⚠ LibreOffice não encontrado. Pulando conversão para PDF.")
        print("  Instale com: brew install --cask libreoffice")
        return None

    try:
        result = subprocess.run(
            [soffice, "--headless", "--convert-to", "pdf", pptx_path, "--outdir", output_dir],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"Erro na conversão PDF: {result.stderr}")
            return None

        base_name = os.path.splitext(os.path.basename(pptx_path))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        if os.path.exists(pdf_path):
            return pdf_path
        else:
            print("PDF não foi gerado.")
            return None

    except subprocess.TimeoutExpired:
        print("Timeout na conversão PDF.")
        return None
    except Exception as e:
        print(f"Erro: {e}")
        return None


def _find_soffice() -> str:
    """Encontra o executável do LibreOffice."""
    paths = [
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        shutil.which("soffice"),
        shutil.which("libreoffice"),
    ]
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pdf = convert_to_pdf(sys.argv[1])
        if pdf:
            print(f"PDF gerado: {pdf}")
    else:
        print("Uso: python pdf_converter.py arquivo.pptx")
