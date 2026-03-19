# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tax diagnostic presentation generator for **Rebechi & Silva Advogados Associados**. Reads client financial data from Google Sheets, generates charts (matplotlib), populates a branded PPTX template (python-pptx), and optionally converts to PDF (LibreOffice). Has both a CLI (`main.py`) and a Streamlit web interface (`app.py`).

## Commands

```bash
# Run Streamlit web app
streamlit run app.py

# Run CLI (interactive client selection)
python main.py

# Run CLI for specific client
python main.py "EMPRESA XYZ LTDA"

# Generate sample charts only
python chart_generator.py

# Convert PPTX to PDF standalone
python pdf_converter.py output/Diagnostico_EMPRESA.pptx

# Install dependencies
pip install -r requirements.txt
```

## Architecture

The pipeline flows in 5 stages, orchestrated by `main.py` (CLI) or `app.py` (Streamlit):

1. **`sheets_reader.py`** — Authenticates via Google service account (`credentials.json`), reads 10 named tabs from a single Google Sheets spreadsheet. Tabs are either single-row (returns dict) or multi-row (returns list of dicts). Handles Brazilian number format parsing (1.234,56).

2. **`data_processor.py`** — Formats raw numeric values into BRL currency (`R$ 1.234,56`) and percentage strings (`11,44%`). Auto-detects monetary vs percentage fields by key name heuristics (`_is_monetary_key`, `_is_percentage_key`). Also builds scenario difference text and calculates recuperacao total.

3. **`chart_generator.py`** — Generates 3 chart types as transparent PNGs using matplotlib: donut (expense breakdown), gauge pair (Lucro Real vs Lucro Presumido rates), and bar chart (tax reform projections). Uses Montserrat Bold and Poppins Bold fonts from `~/Library/Fonts`. Operates on **raw numeric data** (before BRL formatting).

4. **`slide_updater.py`** — Opens the PPTX template, updates only slides listed in `EDITABLE_SLIDES` (config.py). Each editable slide has a dedicated updater function dispatched via `_SLIDE_UPDATERS` dict. Matches shapes by `shape.name` (e.g., "TextBox 12") as defined in `SHAPE_MAP`. Preserves original formatting when replacing text.

5. **`pdf_converter.py`** — Converts PPTX to PDF via LibreOffice headless mode. Optional; gracefully skips if LibreOffice is not installed.

## Key Configuration (config.py)

- `SPREADSHEET_ID` — The Google Sheets document ID (hardcoded)
- `SHEET_NAMES` — Maps internal keys to actual tab names in the spreadsheet
- `EDITABLE_SLIDES` — 0-indexed list of slides that get updated (13 out of ~26 slides)
- `SHAPE_MAP` — Maps `{slide_index: {shape_name: data_field}}` for text/image replacement
- `CORES` / `FONTES` — Brand colors and font names used across charts and slides
- Template file: `Cópia de MODELO DIAGNÓSTICO  2026.pptx`

## Important Patterns

- **Chart data uses raw numbers; slide data uses formatted strings.** `_build_chart_data()` in main.py extracts numeric values for matplotlib. `process_data()` in data_processor.py formats those same values as BRL/pct strings for slide text.
- **Shape identification is by name, not position.** Adding/removing shapes in the PPTX template will break the mapping unless `SHAPE_MAP` in config.py is updated.
- **Special field prefixes in SHAPE_MAP:** `__donut_chart__`, `__bar_chart__` trigger image replacement; `__table__`, `__beneficios__`, `__passivos__`, `__teses__`, `__sintese__` trigger specialized updater logic.
- Streamlit secrets (for deployment) go in `.streamlit/secrets.toml` — already gitignored.

## External Dependencies

- Google Sheets API via `gspread` + service account credentials
- LibreOffice for PDF conversion (optional, macOS path: `/Applications/LibreOffice.app/Contents/MacOS/soffice`)
- Custom fonts: Montserrat Bold, Poppins Bold must be in `~/Library/Fonts/`
