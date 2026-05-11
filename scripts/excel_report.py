"""
Excel Investigation Report Generator
=====================================
Professional Excel export using openpyxl (Claude Excel skill patterns).
Generates a multi-sheet workbook with:
  1. Executive Summary — verdict counts, entity breakdown, key metrics
  2. User Investigation — core columns with conditional formatting
  3. Detailed Metrics — full data for technical deep-dive
  4. Action Plan — remediation actions per user

Usage:
    from excel_report import generate_excel_report
    generate_excel_report(summary_df, output_path)
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Border, Side, Alignment, NamedStyle
)
from openpyxl.utils import get_column_letter


# ============================================================
# COLOR PALETTE (Professional dark theme, muted tones)
# ============================================================
COLORS = {
    # Header
    "header_bg": "1B2A4A",       # Dark navy
    "header_font": "FFFFFF",     # White
    # Verdict fills
    "confirmed_bg": "FADBD8",    # Soft red
    "confirmed_font": "922B21",  # Dark red
    "likely_bg": "FDEBD0",       # Soft orange
    "likely_font": "7E5109",     # Dark orange
    "suspicious_bg": "FEF9E7",   # Soft yellow
    "suspicious_font": "7D6608", # Dark yellow
    "safe_bg": "D5F5E3",         # Soft green
    "safe_font": "1E8449",       # Dark green
    # Misc
    "title_bg": "0D1B2A",       # Very dark navy
    "title_font": "E0E1DD",     # Off-white
    "subtitle_font": "778DA9",  # Steel blue
    "border": "D5D8DC",         # Light gray
    "alt_row": "F8F9F9",        # Very light gray
    "metric_label": "2C3E50",   # Dark slate
    "accent": "2980B9",         # Blue accent
}

THIN_BORDER = Border(
    left=Side(style="thin", color=COLORS["border"]),
    right=Side(style="thin", color=COLORS["border"]),
    top=Side(style="thin", color=COLORS["border"]),
    bottom=Side(style="thin", color=COLORS["border"]),
)

NO_BORDER = Border()


# ============================================================
# HELPER: Parse JSON array string to readable text
# ============================================================
def parse_json_list(val):
    """Convert JSON array string to comma-separated text."""
    if pd.isna(val) or val == "" or val == "[]":
        return "—"
    try:
        items = json.loads(val)
        if not items:
            return "—"
        return ", ".join(str(i) for i in items)
    except (json.JSONDecodeError, TypeError):
        return str(val)


def has_risk(row_data):
    """Check if user has any MS risk sign-ins."""
    risk = row_data.get("RiskSignIns", 0)
    if pd.isna(risk):
        return False
    return int(risk) > 0



# ============================================================
# STYLES
# ============================================================
def create_styles(wb):
    """Register NamedStyles in the workbook."""
    # Header style
    hdr = NamedStyle(name="hdr")
    hdr.font = Font(name="Calibri", size=10, bold=True, color=COLORS["header_font"])
    hdr.fill = PatternFill(start_color=COLORS["header_bg"], end_color=COLORS["header_bg"], fill_type="solid")
    hdr.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    hdr.border = Border(bottom=Side(style="medium", color=COLORS["header_bg"]))
    wb.add_named_style(hdr)

    # Data style
    data = NamedStyle(name="data")
    data.font = Font(name="Calibri", size=10, color="2C3E50")
    data.alignment = Alignment(vertical="center", wrap_text=False)
    data.border = THIN_BORDER
    wb.add_named_style(data)

    # Number style (right-aligned)
    num = NamedStyle(name="num")
    num.font = Font(name="Calibri", size=10, color="2C3E50")
    num.alignment = Alignment(horizontal="right", vertical="center")
    num.border = THIN_BORDER
    num.number_format = '#,##0'
    wb.add_named_style(num)

    # Score style (bold number)
    score = NamedStyle(name="score")
    score.font = Font(name="Calibri", size=10, color="2C3E50", bold=True)
    score.alignment = Alignment(horizontal="right", vertical="center")
    score.border = THIN_BORDER
    score.number_format = '#,##0.0'
    wb.add_named_style(score)

    # Title style
    title = NamedStyle(name="title")
    title.font = Font(name="Calibri", size=16, bold=True, color=COLORS["title_font"])
    title.fill = PatternFill(start_color=COLORS["title_bg"], end_color=COLORS["title_bg"], fill_type="solid")
    title.alignment = Alignment(horizontal="left", vertical="center")
    wb.add_named_style(title)

    # Subtitle
    sub = NamedStyle(name="sub")
    sub.font = Font(name="Calibri", size=11, color=COLORS["subtitle_font"])
    sub.alignment = Alignment(horizontal="left", vertical="center")
    wb.add_named_style(sub)

    # Metric label (left column in summary)
    mlabel = NamedStyle(name="mlabel")
    mlabel.font = Font(name="Calibri", size=11, bold=True, color=COLORS["metric_label"])
    mlabel.alignment = Alignment(horizontal="left", vertical="center")
    mlabel.border = Border(bottom=Side(style="thin", color=COLORS["border"]))
    wb.add_named_style(mlabel)

    # Metric value
    mval = NamedStyle(name="mval")
    mval.font = Font(name="Calibri", size=11, color=COLORS["metric_label"])
    mval.alignment = Alignment(horizontal="left", vertical="center")
    mval.border = Border(bottom=Side(style="thin", color=COLORS["border"]))
    wb.add_named_style(mval)


def auto_width(ws, min_width=8, max_width=45):
    """Auto-adjust column widths based on content."""
    for col_cells in ws.columns:
        col_letter = get_column_letter(col_cells[0].column)
        max_len = 0
        for cell in col_cells:
            try:
                val = str(cell.value or "")
                max_len = max(max_len, len(val))
            except Exception:
                pass
        width = min(max(max_len + 2, min_width), max_width)
        ws.column_dimensions[col_letter].width = width


def write_header_row(ws, row, headers, style="hdr"):
    """Write a header row with style."""
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=h)
        cell.style = style


def apply_row_highlight(ws, row, row_data, col_start=1, col_end=None):
    """Highlight row if user has MS risk events. Simple binary: risk (orange) vs clean (default)."""
    if col_end is None:
        col_end = ws.max_column
    if has_risk(row_data):
        fill = PatternFill(start_color=COLORS["likely_bg"], end_color=COLORS["likely_bg"], fill_type="solid")
        font = Font(name="Calibri", size=10, color=COLORS["likely_font"])
    else:
        fill = PatternFill()  # No fill
        font = Font(name="Calibri", size=10, color="2C3E50")
    for c in range(col_start, col_end + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = font
        cell.border = THIN_BORDER



# ============================================================
# SHEET 1: EXECUTIVE SUMMARY
# ============================================================
def build_executive_summary(ws, df, threshold):
    """Build the Executive Summary sheet."""
    ws.sheet_properties.tabColor = COLORS["accent"]

    # Title block
    ws.merge_cells("A1:F1")
    title_cell = ws["A1"]
    title_cell.value = "Crystal Group — Security Investigation Report"
    title_cell.style = "title"
    ws.row_dimensions[1].height = 40

    ws.merge_cells("A2:F2")
    ws["A2"].value = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Users: {len(df)}  |  Data Source: Microsoft Entra ID Protection"
    ws["A2"].style = "sub"
    ws.row_dimensions[2].height = 22

    # --- Key Metrics ---
    row = 4
    ws.cell(row=row, column=1, value="KEY METRICS").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    row += 1

    with_risk = len(df[df["RiskSignIns"] > 0]) if "RiskSignIns" in df.columns else 0
    without_risk = len(df) - with_risk

    metrics = [
        ("Total Users Analyzed", len(df)),
        ("Users with MS Risk Events", with_risk),
        ("Users without Risk Events", without_risk),
        ("Total Alerts (all users)", int(df["AlertCount"].sum()) if "AlertCount" in df.columns else 0),
        ("Users with Foreign Access", len(df[df["NonBDSignIns"] > 0]) if "NonBDSignIns" in df.columns else 0),
    ]
    for label, value in metrics:
        ws.cell(row=row, column=1, value=label).style = "mlabel"
        ws.cell(row=row, column=2, value=value).style = "mval"
        row += 1
    row += 1

    # --- Entity Breakdown ---
    ws.cell(row=row, column=1, value="ENTITY BREAKDOWN").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    row += 1

    write_header_row(ws, row, ["Entity", "Users", "With Risk Events"])
    row += 1

    for entity in ["ABL", "CMBD", "CETBD", "CSC", "OTHER"]:
        ent_df = df[df["Entity"] == entity]
        risk_count = len(ent_df[ent_df["RiskSignIns"] > 0]) if "RiskSignIns" in ent_df.columns else 0
        ws.cell(row=row, column=1, value=entity).style = "data"
        ws.cell(row=row, column=2, value=len(ent_df)).style = "num"
        ws.cell(row=row, column=3, value=risk_count).style = "num"
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14



# ============================================================
# SHEET 2: USER INVESTIGATION (core columns)
# ============================================================
def build_user_investigation(ws, df):
    """Build the User Investigation sheet — MS Risk Signals based."""
    ws.sheet_properties.tabColor = "2980B9"

    columns = [
        ("User (UPN)", "User", "data", 35),
        ("Display Name", "DisplayName", "data", 30),
        ("Entity", "Entity", "data", 8),
        ("Department", "Department", "data", 25),
        ("Risk Sign-ins", "RiskSignIns", "num", 14),
        ("Max Risk Score", "MaxRiskScore", "num", 14),
        ("Risk Event Types", "MSRiskEvents", "num", 14),
        ("Total Sign-ins", "TotalSignIns", "num", 14),
        ("Active Days (30d)", "ActiveDays", "num", 14),
        ("Foreign Sign-ins (count)", "ForeignCountrySignIns", "num", 20),
        ("Foreign Countries (list)", "ForeignCountryList", "data", 50),
        ("Defender Alert Count", "AlertCount", "num", 16),
    ]

    # Header row
    for col_idx, (label, _, _, width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.style = "hdr"
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Data rows
    for row_idx, (_, row_data) in enumerate(df.iterrows(), 2):
        for col_idx, (label, field, style, _) in enumerate(columns, 1):
            if label == "Foreign Countries (list)":
                value = parse_json_list(row_data.get("ForeignCountryList", "[]"))
            elif field:
                value = row_data.get(field, "")
                if pd.isna(value):
                    value = ""
            else:
                value = ""

            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.style = style

        apply_row_highlight(ws, row_idx, row_data, 1, len(columns))

    # Freeze panes & auto-filter
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{len(df)+1}"



# ============================================================
# SHEET 3: DETAILED METRICS (all columns)
# ============================================================
def build_detailed_metrics(ws, df):
    """Build the Detailed Metrics sheet with all columns."""
    ws.sheet_properties.tabColor = "7F8C8D"

    # JSON columns that need parsing
    json_cols = {
        "TrustedIPs", "TrustedCountries", "AllCountries",
        "TrustedDevices", "TrustedBrowsers", "TrustedOS", "ISPList",
        "UnknownIPList", "ForeignCountryList", "NonBDCountries",
        "SuspiciousISPs",
        "AlertIPsMatched",
    }

    headers = list(df.columns)

    # Write headers
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=h)
        cell.style = "hdr"

    # Write data
    for row_idx, (_, row_data) in enumerate(df.iterrows(), 2):
        for col_idx, h in enumerate(headers, 1):
            val = row_data.get(h, "")
            if pd.isna(val):
                val = ""
            if h in json_cols and isinstance(val, str):
                val = parse_json_list(val)

            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cell.style = "num"
            else:
                cell.style = "data"

        apply_row_highlight(ws, row_idx, row_data, 1, len(headers))

    # Freeze panes & auto-filter
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(df)+1}"
    auto_width(ws, max_width=35)




# ============================================================
# SHEET 5: METHODOLOGY (investigation approach)
# ============================================================
def build_methodology(ws):
    """Build the Methodology sheet — simplified, no custom categorization."""
    ws.sheet_properties.tabColor = "8E44AD"

    # Title
    ws.merge_cells("A1:E1")
    ws["A1"].value = "Investigation Methodology"
    ws["A1"].style = "title"
    ws.row_dimensions[1].height = 40

    ws.merge_cells("A2:E2")
    ws["A2"].value = "Risk data sourced from Microsoft Entra ID Protection. No custom scoring applied."
    ws["A2"].style = "sub"
    ws.row_dimensions[2].height = 22

    # --- Data Sources ---
    row = 4
    ws.cell(row=row, column=1, value="DATA SOURCES (KQL Queries)").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    row += 1

    write_header_row(ws, row, ["Query", "Export File", "Table", "Purpose", ""])
    row += 1

    sources = [
        ("Q00", "unfamiliar_signin_incidents.csv", "AlertInfo + AlertEvidence",
         "All Unfamiliar Sign-in incidents, users, IPs"),
        ("Q01A-F", "signin_history (merged)", "EntraIdSignInEvents",
         "Sign-in history (30 days) + RiskLevelDuringSignIn"),
        ("Q02", "isp_data.csv", "IdentityLogonEvents",
         "ISP enrichment — hosting/VPS/anonymous ISPs"),
        ("Q03", "alert_data.csv", "AlertEvidence",
         "Unfamiliar sign-in alert details per user"),
        ("Q04", "user_profiles.csv", "IdentityInfo",
         "User identity info — department, job title"),
        ("Q05", "phishing_emails.csv", "EmailEvents",
         "Phishing emails received by affected users"),
    ]

    for query, file, table, purpose in sources:
        for col_idx, val in enumerate([query, file, table, purpose], 1):
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.style = "data"
        ws.merge_cells(start_row=row, start_column=4, end_row=row, end_column=5)
        row += 1

    # --- Important Notes ---
    row += 1
    ws.cell(row=row, column=1, value="IMPORTANT NOTES").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
    row += 1

    notes = [
        ("No custom scoring", "This report does NOT apply any custom risk scoring or categorization. "
         "All risk data comes directly from Microsoft Identity Protection ML models."),
        ("RiskLevelDuringSignIn", "Raw numeric value from Microsoft Entra ID. "
         "Higher values indicate higher risk. Analyst interprets based on context."),
        ("Service App Traffic", "Internal apps (AMC PROD, My Profile) generate foreign sign-ins through Azure relay IPs. "
         "These are NOT actual user locations."),
        ("SOC Analyst Role", "This report provides DATA for analyst review. "
         "The analyst makes the final determination based on context."),
        ("MS Infra IPs", "Microsoft infrastructure IPs (20.x, 40.x, 52.x, 2603:x) are auto-filtered before analysis."),
    ]

    for term, definition in notes:
        cell_t = ws.cell(row=row, column=1, value=term)
        cell_t.style = "mlabel"
        cell_d = ws.cell(row=row, column=2, value=definition)
        cell_d.style = "mval"
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=5)
        ws.row_dimensions[row].height = 36
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 30
    ws.column_dimensions["E"].width = 30



# ============================================================
# MAIN ENTRY POINT
# ============================================================
def generate_excel_report(df: pd.DataFrame, output_path: Path, threshold: float = 0.05):
    """Generate a professional multi-sheet Excel investigation report.

    Args:
        df: Summary DataFrame (sorted by UserRiskLevel)
        output_path: Path to save the .xlsx file
        threshold: Trusted threshold used in analysis
    """
    wb = Workbook()
    create_styles(wb)

    # Sheet 1: Executive Summary
    ws1 = wb.active
    ws1.title = "Executive Summary"
    build_executive_summary(ws1, df, threshold)

    # Sheet 2: User Investigation
    ws2 = wb.create_sheet("User Investigation")
    build_user_investigation(ws2, df)

    # Sheet 3: Detailed Metrics
    ws3 = wb.create_sheet("Detailed Metrics")
    build_detailed_metrics(ws3, df)

    # Sheet 4: Methodology
    ws4 = wb.create_sheet("Methodology")
    build_methodology(ws4)

    # Save
    wb.save(output_path)
    print(f"\U0001f4ca Excel report saved: {output_path}")


