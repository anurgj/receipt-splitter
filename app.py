import fitz
import re
import csv
import streamlit as st
import pandas as pd
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP, getcontext
import tempfile

getcontext().prec = 10

st.title("Receipt Splitter v1.3 (PDF Upload)")

people = ["Akhil", "Anuraag", "Daksh", "Tanvin"]

# === PDF Parsing Functions ===
def extract_items_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    items, taxes = [], []
    total, subtotal = None, None
    current_item_lines = []
    in_totals_section = False
    skip_next_line = False

    for idx, line in enumerate(lines):
        if skip_next_line:
            skip_next_line = False
            continue

        if line == "Free delivery from store" or line.startswith("More from this order"):
            continue

        if "Subtotal" in line and idx + 2 < len(lines):
            next_line = lines[idx + 1].strip()
            second_line = lines[idx + 2].strip()
            if re.match(r"^\$\d+\.\d{2}$", next_line) and re.match(r"^\$\d+\.\d{2}$", second_line):
                subtotal = float(second_line.replace("$", ""))
                in_totals_section = True
                skip_next_line = True
                continue

        if in_totals_section:
            if subtotal is not None and re.match(r"^\$\d+\.\d{2}$", line):
                continue
            if idx + 1 < len(lines) and re.match(r"^\$\d+\.\d{2}$", lines[idx + 1]):
                tax_name = line
                tax_amount = float(lines[idx + 1].replace("$", ""))
                taxes.append((tax_name, tax_amount))
                continue
            if "Total" in line and idx + 1 < len(lines):
                next_line = lines[idx + 1]
                if re.match(r"^\$\d+\.\d{2}$", next_line):
                    total = float(next_line.replace("$", ""))
                continue
            continue

        if re.match(r"^\$\d+\.\d{2}$", line):
            if current_item_lines:
                item_name = " ".join(current_item_lines).strip()
                items.append((item_name, float(line.replace("$", ""))))
                current_item_lines = []
        else:
            current_item_lines.append(line)

    return items, taxes, subtotal, total

# === File Upload ===
uploaded_pdf = st.file_uploader("Upload a Walmart Receipt PDF", type=["pdf"])

if uploaded_pdf:
    # Save to a temp file for fitz to read
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(uploaded_pdf.read())
        tmp_path = tmp_pdf.name

    items, taxes, subtotal, total = extract_items_from_pdf(tmp_path)

    # Convert extracted data to a DataFrame
    df = pd.DataFrame(items, columns=["item", "price"])
    for p in people:
        df[p] = ""  # default empty cells

    # Add subtotal, taxes, total
    if subtotal is not None:
        df.loc[len(df)] = ["Subtotal", subtotal] + [""] * len(people)
    for tax_name, tax_amount in taxes:
        df.loc[len(df)] = [tax_name, tax_amount] + [""] * len(people)
    if total is not None:
        df.loc[len(df)] = ["Total", total] + [""] * len(people)

    # Proceed with your original logic using df directly
    # === Prepare DataFrame for Splitting ===
    df_split = df[~df["item"].str.lower().str.contains("total|subtotal")]
    df_split.reset_index(drop=True, inplace=True)

    def fair_split(total_price, weights):
        total = Decimal(str(total_price)).quantize(Decimal("0.02"))
        raw_shares = [total * w / sum(weights) for w in weights]
        rounded = [s.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for s in raw_shares[:-1]]
        remainder = total - sum(rounded)
        rounded.append(remainder.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        return rounded

    selections, percentages, ignored_indices = [], [], []
    st.write("### Select who shares each item (or ignore it):")

    for idx, row in df_split.iterrows():
        top_cols = st.columns([2, 1, 1])
        top_cols[0].markdown(f"**{row['item']}** — ${row['price']:.2f}")
        ignore = top_cols[1].checkbox("Ignore", key=f"{idx}-ignore")
        select_all = top_cols[2].checkbox("Select All", key=f"{idx}-selectall")

        if ignore:
            ignored_indices.append(idx)
            st.markdown(f"~~{row['item']}~~ (Ignored)")
            selections.append([False] * len(people))
            percentages.append([Decimal("0.00")] * len(people))
            continue

        row_selection, row_percentage = [], []
        cols = st.columns(len(people))
        for i, person in enumerate(people):
            with cols[i]:
                checked = st.checkbox(person, value=True if select_all else False, key=f"{idx}-{person}")
                row_selection.append(checked)
                if checked:
                    pct = st.number_input("%", min_value=0, max_value=100, step=1, key=f"{idx}-{person}-pct")
                    row_percentage.append(Decimal(pct))
                else:
                    row_percentage.append(Decimal("0.00"))

        selections.append(row_selection)
        percentages.append(row_percentage)

    # === Calculation ===
    totals = {p: Decimal("0.00") for p in people}
    for i, row in df_split.iterrows():
        if i in ignored_indices:
            continue
        selected_people = [idx for idx, selected in enumerate(selections[i]) if selected]
        num_selected = len(selected_people)
        price = Decimal(str(row["price"]))
        row_percents = percentages[i]
        total_percent_entered = sum(row_percents[idx] for idx in selected_people)

        if num_selected == 0:
            st.error(f"⚠️ No one selected for: {row['item']}")
            continue
        if num_selected == 1:
            totals[people[selected_people[0]]] += price
        elif total_percent_entered == 0:
            shares = fair_split(price, [Decimal("1")] * num_selected)
            for idx, share in zip(selected_people, shares):
                totals[people[idx]] += share
        elif abs(total_percent_entered - Decimal("100.00")) > Decimal("0.1"):
            st.error(f"⚠️ Percentages for '{row['item']}' do not add up to 100% (currently {float(total_percent_entered):.1f}%)")
            continue
        else:
            shares = fair_split(price, [row_percents[idx] for idx in selected_people])
            for idx, share in zip(selected_people, shares):
                totals[people[idx]] += share

    # === Totals per Person ===
    st.write("### 💰 Totals per person:")
    for person in people:
        st.write(f"- **{person}** owes: ${totals[person].quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}")

    calculated_total = sum(totals.values()).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    csv_total = Decimal(str(total)) if total is not None else None
    ignored_total = sum(Decimal(str(df_split.loc[idx, "price"])) for idx in ignored_indices)
    adjusted_csv_total = (csv_total - ignored_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if csv_total is not None else None

    st.write(f"\n📦 **Calculated grand total**: ${calculated_total}")
    if adjusted_csv_total is not None:
        st.write(f"🧾 **Adjusted order total**: ${adjusted_csv_total}")
        if abs(calculated_total - adjusted_csv_total) > Decimal("0.01"):
            st.warning("⚠️ The calculated total does not match the adjusted order total!")
    else:
        st.warning("⚠️ Could not find 'Total' in the receipt.")