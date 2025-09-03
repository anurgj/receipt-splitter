# Receipt Splitter v1.3

A simple Streamlit app that parses **Walmart** PDF receipts and helps split item costs among friends (supports both equal and percentage-based splits, per item). It also handles ignoring items and shows parity checks against the receipt total.

## Features

- 📄 **PDF parsing** using PyMuPDF (`fitz`) to extract items, subtotal, taxes, and total  
- 👥 **Flexible splitting**: select people per item, equal share or custom percentages  
- 🙈 **Ignore items** you don’t want included in the split  
- 🧮 **Rounding-aware** fair split (uses `Decimal`)  
- ✅ **Sanity check**: compares calculated total vs. adjusted receipt total

## Demo (TL;DR)

```bash
# 1. Create and activate a virtual environment (recommended)

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py