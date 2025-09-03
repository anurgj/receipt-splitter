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
pip install -r requirements.txt
streamlit run app.py