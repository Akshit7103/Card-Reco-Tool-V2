import os
import sys
import io
import tempfile
import shutil
import importlib.util
from contextlib import redirect_stdout
from typing import Optional, Dict

from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)

# Use the local rate_tool_app.py file in the same directory
RATE_APP_FILE = os.path.join(BASE_DIR, 'rate_tool_app.py')

if not os.path.exists(RATE_APP_FILE):
    raise FileNotFoundError(f"Could not locate rate calculator app.py at: {RATE_APP_FILE}")

module_name = 'rate_tool_app'
spec = importlib.util.spec_from_file_location(module_name, RATE_APP_FILE)
rate_tool_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rate_tool_app)

analyze_excel_structure = rate_tool_app.analyze_excel_structure
extract_card_issuance_data = rate_tool_app.extract_card_issuance_data
process_specific_transaction_file = rate_tool_app.process_specific_transaction_file
calculate_fee_amount = rate_tool_app.calculate_fee_amount

ALLOWED_EXTENSIONS = {"xls", "xlsx"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file_storage, base_dir: str) -> Optional[str]:
    if not file_storage or file_storage.filename == "":
        return None

    if not allowed_file(file_storage.filename):
        raise ValueError("Only Excel files (.xls, .xlsx) are supported.")

    filename = secure_filename(file_storage.filename)
    file_path = os.path.join(base_dir, filename)
    file_storage.save(file_path)
    return file_path


def format_currency(amount, currency_symbol):
    if amount is None or amount == 0:
        return "N/A"
    if currency_symbol == "Rs":
        return f"INR {amount:,.2f}"
    return f"USD {amount:,.2f}"


def extract_invoice_data_dynamically(file_paths):
    """
    Dynamically extract invoice data from any available invoice file
    """
    invoice_data = {}

    # Check multiple possible invoice sources
    possible_invoice_paths = [
        file_paths.get('invoice'),  # Dedicated invoice file (if provided)
        file_paths.get('summary'),  # Could contain invoice sheet
        file_paths.get('card'),     # Could contain invoice data
        file_paths.get('international'),  # Could contain invoice data
        file_paths.get('domestic'),      # Could contain invoice data
        file_paths.get('dispute')        # Could contain invoice data
    ]

    for file_path in possible_invoice_paths:
        if not file_path:
            continue

        try:
            import pandas as pd
            excel_file = pd.ExcelFile(file_path)

            # Look for invoice-related sheets
            for sheet_name in excel_file.sheet_names:
                sheet_name_lower = sheet_name.lower()
                if 'invoice' in sheet_name_lower or 'bill' in sheet_name_lower:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    invoice_data.update(extract_invoice_from_sheet(df, sheet_name))

            # Also check if main sheet has invoice-like data
            if not invoice_data:
                df = pd.read_excel(file_path, sheet_name=excel_file.sheet_names[0])
                potential_invoice = extract_invoice_from_sheet(df, excel_file.sheet_names[0])
                if potential_invoice:
                    invoice_data.update(potential_invoice)

        except Exception:
            continue

    return invoice_data

def extract_invoice_from_sheet(df, sheet_name):
    """
    Extract invoice data from any sheet dynamically
    """
    import pandas as pd

    invoice_items = {}

    # Look for patterns that indicate invoice data
    invoice_keywords = ['particulars', 'fee', 'charge', 'amount', 'total', 'description']
    amount_keywords = ['amount', 'value', 'cost', 'price', 'total']

    # Find columns that might contain fee descriptions and amounts
    fee_col = None
    amount_col = None

    for col in df.columns:
        col_str = str(col).lower().strip()

        # Check for fee/particulars column
        if any(keyword in col_str for keyword in invoice_keywords) and not any(keyword in col_str for keyword in amount_keywords):
            fee_col = col

        # Check for amount column (prefer final amount)
        if any(keyword in col_str for keyword in amount_keywords):
            amount_col = col

    # If no clear columns found, try positional approach
    if not fee_col or not amount_col:
        for idx, row in df.iterrows():
            row_values = [str(val).strip() for val in row if pd.notna(val)]

            # Look for header row
            if any(keyword in ' '.join(row_values).lower() for keyword in invoice_keywords):
                # Found potential header, extract data from subsequent rows
                for data_idx in range(idx + 1, len(df)):
                    data_row = df.iloc[data_idx]
                    row_data = [str(val).strip() for val in data_row if pd.notna(val) and str(val).strip()]

                    if len(row_data) >= 2:
                        # First non-empty value is likely fee name, last is likely amount
                        fee_name = row_data[0]
                        amount_value = row_data[-1]

                        # Skip header-like rows
                        if fee_name.lower() in ['particulars', 'fee type', 's.no', 'sno']:
                            continue

                        # Try to parse amount
                        try:
                            if amount_value.replace(',', '').replace('.', '').isdigit():
                                amount = float(amount_value.replace(',', ''))
                                invoice_items[fee_name] = amount
                        except:
                            continue
                break

    # Extract using identified columns
    if fee_col is not None and amount_col is not None:
        for idx, row in df.iterrows():
            fee_name = row[fee_col]
            amount_value = row[amount_col]

            if pd.notna(fee_name) and pd.notna(amount_value):
                fee_name_str = str(fee_name).strip()

                # Skip header rows
                if fee_name_str.lower() in ['particulars', 'fee type', 's.no', 'sno', 'description', 'amount']:
                    continue

                # Try to parse amount
                try:
                    amount_str = str(amount_value).replace(',', '')
                    if amount_str.replace('.', '').isdigit():
                        amount = float(amount_str)
                        invoice_items[fee_name_str] = amount
                except:
                    continue

    # If no items found using column approach, try fallback method with content-based detection
    if not invoice_items:
        # Look for header row with "Particulars" to identify structure
        particulars_col = None
        final_amount_col = None
        header_row_idx = None

        # Find header row and columns by scanning content
        for idx, row in df.iterrows():
            row_values = [str(val).strip().lower() if pd.notna(val) else "" for val in row]

            # Check if this row contains "Particulars" (header row)
            for col_idx, val in enumerate(row_values):
                if val == 'particulars':
                    particulars_col = df.columns[col_idx]
                    header_row_idx = idx

                    # Look for the last "Amount" column in the same row (final amount after exchange rate)
                    for end_col_idx in range(len(row_values) - 1, -1, -1):
                        if row_values[end_col_idx] == 'amount':
                            final_amount_col = df.columns[end_col_idx]
                            break
                    break

            if particulars_col and final_amount_col:
                break

        # Extract data if we found the structure
        if particulars_col and final_amount_col and header_row_idx is not None:
            # Process rows after the header
            for idx in range(header_row_idx + 1, len(df)):
                row = df.iloc[idx]
                fee_name = row[particulars_col]
                amount_value = row[final_amount_col]

                if pd.notna(fee_name) and pd.notna(amount_value):
                    fee_name_str = str(fee_name).strip()

                    # Skip empty rows and total rows
                    if fee_name_str == '' or amount_value == '' or pd.isna(amount_value):
                        continue

                    # Try to parse amount
                    try:
                        if isinstance(amount_value, (int, float)):
                            amount = float(amount_value)
                            invoice_items[fee_name_str] = amount
                        else:
                            amount_str = str(amount_value).replace(',', '')
                            if amount_str.replace('.', '').isdigit():
                                amount = float(amount_str)
                                invoice_items[fee_name_str] = amount
                    except:
                        continue

    return invoice_items

def fuzzy_match_fee_types(calculated_fees, invoice_fees):
    """
    Match fee types between calculated and invoice data using fuzzy matching
    """
    import re

    matches = {}

    def normalize_fee_name(name):
        # Remove common words and normalize
        name = re.sub(r'\b(fee|charge|cost|amount|total|value)\b', '', name.lower())
        name = re.sub(r'[^\w\s]', '', name)  # Remove special characters
        name = re.sub(r'\s+', ' ', name).strip()  # Normalize whitespace
        return name

    # Try exact matches first
    for calc_fee in calculated_fees:
        for invoice_fee in invoice_fees:
            if normalize_fee_name(calc_fee) == normalize_fee_name(invoice_fee):
                matches[calc_fee] = invoice_fee
                break

    # Try partial matches for unmatched items
    unmatched_calc = [f for f in calculated_fees if f not in matches]
    unmatched_invoice = [f for f in invoice_fees if f not in matches.values()]

    for calc_fee in unmatched_calc:
        calc_normalized = normalize_fee_name(calc_fee)
        best_match = None
        best_score = 0

        for invoice_fee in unmatched_invoice:
            invoice_normalized = normalize_fee_name(invoice_fee)

            # Calculate similarity
            calc_words = set(calc_normalized.split())
            invoice_words = set(invoice_normalized.split())

            if calc_words and invoice_words:
                intersection = len(calc_words.intersection(invoice_words))
                union = len(calc_words.union(invoice_words))
                score = intersection / union if union > 0 else 0

                if score > best_score and score > 0.3:  # Threshold for match
                    best_match = invoice_fee
                    best_score = score

        if best_match:
            matches[calc_fee] = best_match

    return matches

def build_result_context(analysis_results, card_data, transaction_data, warnings, invoice_data=None):
    context = {
        "has_data": bool(analysis_results and analysis_results.get("mappings")),
        "summary": {
            "sheet_count": 0,
            "total_mappings": 0,
            "total_final_amount_inr": 0.0,
            "total_final_amount_display": "N/A"
        },
        "card": None,
        "transactions": None,
        "sheets": [],
        "warnings": warnings
    }

    if not analysis_results or not analysis_results.get("mappings"):
        return context

    sheet_count = len(analysis_results["mappings"])
    total_final_amount_inr = 0.0
    total_mappings = 0

    sheets_presentations = []

    for sheet_name, sheet_data in analysis_results["mappings"].items():
        rows = []
        mappings = sheet_data.get("mappings", {})
        if not mappings:
            continue

        # Build calculated fees
        calculated_fees = {}
        for fee_type, rate_chart in mappings.items():
            card_count = card_data["total_cards"] if card_data else 0
            transaction_count = 0
            transaction_amount = 0

            if transaction_data:
                fee_type_lower = fee_type.lower()
                if "international" in fee_type_lower:
                    trans_bucket = transaction_data.get("international", {})
                elif "domestic" in fee_type_lower:
                    trans_bucket = transaction_data.get("domestic", {})
                elif "dispute" in fee_type_lower:
                    trans_bucket = transaction_data.get("disputes", {})
                else:
                    trans_bucket = transaction_data.get("all_transactions", {})

                transaction_count = trans_bucket.get("total_volume", 0)
                transaction_amount = trans_bucket.get("total_amount", 0)

            calc_result = calculate_fee_amount(
                rate_chart,
                card_count,
                transaction_count=transaction_count,
                transaction_amount=transaction_amount
            )

            calculated_amount = calc_result.get("calculated_amount", 0)
            calculation_method = calc_result.get("calculation_method", "N/A")
            currency_symbol = calc_result.get("currency", "$") or "$"
            exchange_rate = 78 if currency_symbol == "$" else 1

            if calculated_amount and calculated_amount > 0:
                formatted_amount = format_currency(calculated_amount, "Rs" if currency_symbol == "Rs" else "$")
                final_amount = calculated_amount * exchange_rate
                final_amount_display = f"INR {final_amount:,.2f}"
                total_final_amount_inr += final_amount
            else:
                formatted_amount = "N/A"
                final_amount = None
                final_amount_display = "N/A"

            calculated_fees[fee_type] = {
                "rate_chart": rate_chart,
                "calculation_method": calculation_method,
                "calculated_amount": calculated_amount,
                "calculated_amount_display": formatted_amount,
                "exchange_rate": exchange_rate if calculated_amount else None,
                "final_amount": final_amount,
                "final_amount_display": final_amount_display,
                "currency_symbol": currency_symbol
            }

        # Merge calculated fees with invoice data
        if calculated_fees or invoice_data:
            # Get the union of all fee types
            all_fee_types = set(calculated_fees.keys() if calculated_fees else [])
            if invoice_data:
                all_fee_types.update(invoice_data.keys())

            # Match calculated and invoice fees using fuzzy matching
            if calculated_fees and invoice_data:
                fee_matches = fuzzy_match_fee_types(list(calculated_fees.keys()), list(invoice_data.keys()))
            else:
                fee_matches = {}

            # Build unified rows
            unified_rows = []
            processed_invoice_items = set()

            # Process calculated fees first
            for fee_type in calculated_fees.keys():
                calc_data = calculated_fees[fee_type]

                # Find matching invoice item
                matched_invoice_fee = fee_matches.get(fee_type)
                if matched_invoice_fee:
                    visa_amount = invoice_data.get(matched_invoice_fee, 0)
                    visa_amount_display = f"INR {visa_amount:,.2f}" if visa_amount else "N/A"
                    processed_invoice_items.add(matched_invoice_fee)
                else:
                    visa_amount = None
                    visa_amount_display = "N/A"

                # Calculate percentage difference
                percentage_diff = None
                percentage_diff_display = "N/A"
                diff_status = "no_visa"  # Default status

                if (calc_data["final_amount"] is not None and
                    visa_amount is not None and
                    visa_amount != 0):

                    calculated_inr = calc_data["final_amount"]
                    percentage_diff = ((calculated_inr - visa_amount) / visa_amount) * 100

                    # Format percentage difference with appropriate styling info
                    if abs(percentage_diff) < 0.01:  # Less than 0.01%
                        percentage_diff_display = "0.00%"
                        diff_status = "exact"
                    elif percentage_diff > 0:
                        percentage_diff_display = f"+{percentage_diff:.2f}%"
                        diff_status = "higher"
                    else:
                        percentage_diff_display = f"{percentage_diff:.2f}%"
                        diff_status = "lower"
                elif calc_data["final_amount"] is None or calc_data["final_amount_display"] == "Missing":
                    percentage_diff_display = "Missing"
                    diff_status = "missing"
                elif visa_amount is None:
                    percentage_diff_display = "N/A"
                    diff_status = "no_visa"

                unified_rows.append({
                    "fee_type": fee_type,
                    "rate_chart": calc_data["rate_chart"],
                    "calculation_method": calc_data["calculation_method"],
                    "calculated_amount": calc_data["calculated_amount"],
                    "calculated_amount_display": calc_data["calculated_amount_display"],
                    "exchange_rate": calc_data["exchange_rate"],
                    "final_amount": calc_data["final_amount"],
                    "final_amount_display": calc_data["final_amount_display"],
                    "currency_symbol": calc_data["currency_symbol"],
                    "visa_amount": visa_amount,
                    "visa_amount_display": visa_amount_display,
                    "percentage_diff": percentage_diff,
                    "percentage_diff_display": percentage_diff_display,
                    "diff_status": diff_status
                })

            # Process unmatched invoice items
            if invoice_data:
                for invoice_fee, invoice_amount in invoice_data.items():
                    if invoice_fee not in processed_invoice_items:
                        unified_rows.append({
                            "fee_type": invoice_fee,
                            "rate_chart": "N/A",
                            "calculation_method": "N/A",
                            "calculated_amount": 0,
                            "calculated_amount_display": "N/A",
                            "exchange_rate": None,
                            "final_amount": None,
                            "final_amount_display": "Missing",
                            "currency_symbol": "INR",
                            "visa_amount": invoice_amount,
                            "visa_amount_display": f"INR {invoice_amount:,.2f}",
                            "percentage_diff": None,
                            "percentage_diff_display": "Missing",
                            "diff_status": "missing"
                        })

            if unified_rows:
                sheets_presentations.append({
                    "name": sheet_name,
                    "rows": unified_rows,
                    "calculated_fees": calculated_fees
                })
                total_mappings += len(unified_rows)

    # Calculate fee reconciliation percentage based on unique VISA items
    total_visa_items = len(invoice_data) if invoice_data else 0
    total_calculated_items = sum(len(sheet.get("calculated_fees", {})) for sheet in sheets_presentations)

    # Count unique VISA items that have been successfully matched with calculated values
    unique_matched_visa_items = set()
    unique_exact_match_items = set()

    for sheet in sheets_presentations:
        for row in sheet.get("rows", []):
            if (row.get("final_amount_display") != "Missing" and
                row.get("final_amount_display") != "N/A" and
                row.get("visa_amount_display") != "N/A" and
                row.get("visa_amount") is not None):

                # Use fee_type as the unique identifier for VISA items
                fee_type = row.get("fee_type")
                unique_matched_visa_items.add(fee_type)

                # Check if amounts match exactly (diff_status is 'exact')
                if row.get("diff_status") == "exact":
                    unique_exact_match_items.add(fee_type)

    matched_items = len(unique_matched_visa_items)
    exact_match_items = len(unique_exact_match_items)

    # Calculate reconciliation percentage
    if total_visa_items > 0:
        fee_reconciled_percentage = (matched_items / total_visa_items) * 100
        fee_reconciled_display = f"{fee_reconciled_percentage:.1f}%"
    else:
        fee_reconciled_percentage = 0
        fee_reconciled_display = "N/A"

    # Calculate amount match percentage (for successfully reconciled items)
    if matched_items > 0:
        amount_match_percentage = (exact_match_items / matched_items) * 100
        amount_match_display = f"{amount_match_percentage:.1f}%"
    else:
        amount_match_percentage = 0
        amount_match_display = "N/A"

    # Calculate VISA total amount
    total_visa_amount_inr = sum(invoice_data.values()) if invoice_data else 0.0

    # Calculate amount reconciled percentage (Smaller / Larger) - never exceeds 100%
    if total_final_amount_inr > 0 and total_visa_amount_inr > 0:
        # Always use smaller/larger to ensure percentage doesn't exceed 100%
        smaller_amount = min(total_visa_amount_inr, total_final_amount_inr)
        larger_amount = max(total_visa_amount_inr, total_final_amount_inr)
        amount_reconciled_percentage = (smaller_amount / larger_amount) * 100

        # Don't round off - show up to 4 decimal places, but remove trailing zeros
        formatted_num = f"{amount_reconciled_percentage:.4f}".rstrip('0').rstrip('.')
        amount_reconciled_display = f"{formatted_num}%"
    else:
        amount_reconciled_percentage = 0
        amount_reconciled_display = "N/A"

    context["sheets"] = sheets_presentations
    context["summary"] = {
        "sheet_count": sheet_count,
        "total_mappings": total_mappings,
        "total_final_amount_inr": total_final_amount_inr,
        "total_final_amount_display": f"INR {total_final_amount_inr:,.2f}" if total_final_amount_inr else "N/A",
        "total_visa_amount_inr": total_visa_amount_inr,
        "total_visa_amount_display": f"INR {total_visa_amount_inr:,.2f}" if total_visa_amount_inr else "N/A",
        "total_visa_items": total_visa_items,
        "total_calculated_items": total_calculated_items,
        "matched_items": matched_items,
        "exact_match_items": exact_match_items,
        "fee_reconciled_percentage": fee_reconciled_percentage,
        "fee_reconciled_display": fee_reconciled_display,
        "amount_match_percentage": amount_match_percentage,
        "amount_match_display": amount_match_display,
        "amount_reconciled_percentage": amount_reconciled_percentage,
        "amount_reconciled_display": amount_reconciled_display
    }

    if card_data:
        context["card"] = {
            "total_cards": card_data.get("total_cards", 0),
            "monthly_data": card_data.get("monthly_data", [])
        }

    if transaction_data:
        transaction_cards = []
        for key, label in (
            ("international", "International"),
            ("domestic", "Domestic"),
            ("disputes", "Disputes"),
            ("all_transactions", "All Transactions")
        ):
            bucket = transaction_data.get(key)
            if not bucket:
                continue
            if bucket.get("total_volume", 0) == 0 and bucket.get("total_amount", 0) == 0 and key != "all_transactions":
                continue
            transaction_cards.append({
                "label": label,
                "amount": bucket.get("total_amount", 0),
                "amount_display": f"USD {bucket.get('total_amount', 0):,.2f}" if bucket.get("total_amount", 0) else "N/A",
                "volume": bucket.get("total_volume", 0)
            })

        if transaction_cards:
            context["transactions"] = {
                "entries": transaction_cards
            }

    return context


def run_rate_analysis(file_paths: Dict[str, Optional[str]]):
    warnings = []

    with redirect_stdout(io.StringIO()):
        analysis_results = analyze_excel_structure(file_paths.get('summary'))

        card_data = None
        if file_paths.get('card'):
            card_data = extract_card_issuance_data(file_paths['card'])
            if not card_data or card_data.get("total_cards", 0) == 0:
                warnings.append("No card issuance data found or total cards is 0. Proceeding with fee rate mapping only.")
                card_data = None

        transaction_data = {
            "international": {"total_amount": 0, "total_volume": 0, "transactions": []},
            "domestic": {"total_amount": 0, "total_volume": 0, "transactions": []},
            "disputes": {"total_amount": 0, "total_volume": 0, "transactions": []},
            "all_transactions": {"total_amount": 0, "total_volume": 0}
        }

        if file_paths.get('international'):
            transaction_data["international"] = process_specific_transaction_file(
                file_paths['international'], "international"
            )

        if file_paths.get('domestic'):
            transaction_data["domestic"] = process_specific_transaction_file(
                file_paths['domestic'], "domestic"
            )

        if file_paths.get('dispute'):
            transaction_data["disputes"] = process_specific_transaction_file(
                file_paths['dispute'], "disputes"
            )

        transaction_data["all_transactions"]["total_amount"] = (
            transaction_data["international"]["total_amount"] +
            transaction_data["domestic"]["total_amount"] +
            transaction_data["disputes"]["total_amount"]
        )
        transaction_data["all_transactions"]["total_volume"] = (
            transaction_data["international"]["total_volume"] +
            transaction_data["domestic"]["total_volume"] +
            transaction_data["disputes"]["total_volume"]
        )

        if transaction_data["all_transactions"]["total_volume"] == 0:
            warnings.append("No transaction data found.")
            transaction_data = None

        # Extract invoice data dynamically
        invoice_data = extract_invoice_data_dynamically(file_paths)
        if not invoice_data:
            if not file_paths.get('invoice'):
                warnings.append("No invoice file uploaded. VISA Amount column will show 'N/A' for all items.")
            else:
                warnings.append("No invoice data found in uploaded files. Please check the invoice file format.")

    report_context = build_result_context(analysis_results, card_data, transaction_data, warnings, invoice_data)

    # Generate root cause analysis if amount reconciled < 95%
    try:
        from root_cause_analysis import generate_root_cause_analysis
        # Get OpenAI API key from environment
        api_key = os.environ.get("OPENAI_API_KEY")
        root_cause_analysis = generate_root_cause_analysis(report_context, api_key=api_key)
        report_context['root_cause_analysis'] = root_cause_analysis
    except Exception as e:
        print(f"Error generating root cause analysis: {str(e)}")
        report_context['root_cause_analysis'] = None

    return report_context

