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


def risk_category(risk_level):
    """Map UserRiskLevel to styling category."""
    if pd.isna(risk_level):
        return "safe"
    r = str(risk_level)
    if r == "High":
        return "confirmed"
    elif r == "Medium":
        return "likely"
    elif r == "Low":
        return "suspicious"
    return "safe"


def get_risk_fill(category):
    """Get PatternFill for risk category."""
    return PatternFill(
        start_color=COLORS[f"{category}_bg"],
        end_color=COLORS[f"{category}_bg"],
        fill_type="solid"
    )


def get_risk_font(category, bold=False):
    """Get Font for risk category."""
    return Font(
        name="Calibri", size=10,
        color=COLORS[f"{category}_font"],
        bold=bold
    )



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


def apply_risk_formatting(ws, row, risk_level, col_start=1, col_end=None):
    """Apply risk level color to an entire data row."""
    cat = risk_category(risk_level)
    fill = get_risk_fill(cat)
    font = get_risk_font(cat)
    if col_end is None:
        col_end = ws.max_column
    for c in range(col_start, col_end + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = fill
        cell.font = font
        cell.border = THIN_BORDER



# ============================================================
# SHEET 1: EXECUTIVE SUMMARY
# ============================================================
def build_executive_summary(ws, df, threshold):
    """Build the Executive Summary sheet — MS Risk Signals based."""
    ws.sheet_properties.tabColor = COLORS["accent"]

    # Title block
    ws.merge_cells("A1:F1")
    title_cell = ws["A1"]
    title_cell.value = "Crystal Group — Security Investigation Report v6.0"
    title_cell.style = "title"
    ws.row_dimensions[1].height = 40

    ws.merge_cells("A2:F2")
    ws["A2"].value = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Users: {len(df)}  |  Source: Microsoft Risk Signals"
    ws["A2"].style = "sub"
    ws.row_dimensions[2].height = 22

    # --- Risk Level Distribution ---
    row = 4
    ws.cell(row=row, column=1, value="MICROSOFT RISK LEVEL DISTRIBUTION").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    row += 1

    risk_types = [
        ("High", "confirmed"),
        ("Medium", "likely"),
        ("Low", "suspicious"),
        ("None", "safe"),
    ]

    headers = ["Risk Level", "Users", "% of Total"]
    write_header_row(ws, row, headers)
    row += 1

    for risk_name, cat in risk_types:
        count = len(df[df["UserRiskLevel"] == risk_name]) if "UserRiskLevel" in df.columns else 0
        pct = count / len(df) * 100 if len(df) > 0 else 0

        cell_v = ws.cell(row=row, column=1, value=f"MS Risk: {risk_name}")
        cell_c = ws.cell(row=row, column=2, value=count)
        cell_p = ws.cell(row=row, column=3, value=f"{pct:.1f}%")

        fill = get_risk_fill(cat)
        font = get_risk_font(cat, bold=True)
        for c in [cell_v, cell_c, cell_p]:
            c.fill = fill
            c.font = font
            c.border = THIN_BORDER
            c.alignment = Alignment(vertical="center")
        cell_c.alignment = Alignment(horizontal="center", vertical="center")
        cell_p.alignment = Alignment(horizontal="center", vertical="center")
        row += 1

    # Total row
    for c in range(1, 4):
        cell = ws.cell(row=row, column=c)
        cell.font = Font(name="Calibri", size=10, bold=True, color=COLORS["header_font"])
        cell.fill = PatternFill(start_color=COLORS["header_bg"], end_color=COLORS["header_bg"], fill_type="solid")
        cell.border = THIN_BORDER
    ws.cell(row=row, column=1).value = "TOTAL"
    ws.cell(row=row, column=2).value = len(df)
    ws.cell(row=row, column=2).alignment = Alignment(horizontal="center", vertical="center")
    row += 2

    # --- Entity Breakdown ---
    ws.cell(row=row, column=1, value="ENTITY BREAKDOWN").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    row += 1

    write_header_row(ws, row, ["Entity", "Users", "With Risk Events"])
    row += 1

    for entity in ["ABL", "CMBD", "CETBD", "CSC", "OTHER"]:
        ent_df = df[df["Entity"] == entity]
        risk_count = len(ent_df[ent_df["MSTotalRiskSignIns"] > 0]) if "MSTotalRiskSignIns" in ent_df.columns else 0
        ws.cell(row=row, column=1, value=entity).style = "data"
        ws.cell(row=row, column=2, value=len(ent_df)).style = "num"
        ws.cell(row=row, column=3, value=risk_count).style = "num"
        row += 1
    row += 1

    # --- Key Metrics ---
    ws.cell(row=row, column=1, value="KEY METRICS").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    row += 1

    metrics = [
        ("Total Alerts (all users)", df["AlertCount"].sum() if "AlertCount" in df.columns else 0),
        ("Users with MS High Risk", len(df[df["MSHighRiskSignIns"] > 0]) if "MSHighRiskSignIns" in df.columns else 0),
        ("Users with MS Medium Risk", len(df[df["MSMediumRiskSignIns"] > 0]) if "MSMediumRiskSignIns" in df.columns else 0),
        ("Users with Foreign Access", len(df[df["NonBDSignIns"] > 0]) if "NonBDSignIns" in df.columns else 0),
        ("Users with Admin Role", len(df[df["IsAdmin"] == True]) if "IsAdmin" in df.columns else 0),
    ]
    for label, value in metrics:
        ws.cell(row=row, column=1, value=label).style = "mlabel"
        ws.cell(row=row, column=2, value=value).style = "mval"
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
        ("MS Risk Level", "UserRiskLevel", "data", 14),
        ("MS High Risk", "MSHighRiskSignIns", "num", 12),
        ("MS Medium Risk", "MSMediumRiskSignIns", "num", 14),
        ("MS Risk Events", "MSRiskEvents", "num", 14),
        ("Total Sign-ins", "TotalSignIns", "num", 14),
        ("Active Days (30d)", "ActiveDays", "num", 14),
        ("Foreign Sign-ins (count)", "ForeignCountrySignIns", "num", 20),
        ("Foreign Countries (list)", "ForeignCountryList", "data", 50),
        ("Defender Alert Count", "AlertCount", "num", 16),
        ("MFA Status", "MFAStatus", "data", 32),
        ("Account Status", "AccountStatus", "data", 14),
        ("Is Admin", "IsAdmin", "data", 10),
    ]

    # Header row
    for col_idx, (label, _, _, width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.style = "hdr"
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Data rows
    for row_idx, (_, row_data) in enumerate(df.iterrows(), 2):
        risk_level = row_data.get("UserRiskLevel", "None")

        for col_idx, (label, field, style, _) in enumerate(columns, 1):
            if label == "Foreign Countries (list)":
                value = parse_json_list(row_data.get("ForeignCountryList", "[]"))
            elif label == "Is Admin":
                value = "YES" if row_data.get("IsAdmin", False) else "No"
            elif field:
                value = row_data.get(field, "")
                if pd.isna(value):
                    value = ""
            else:
                value = ""

            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.style = style

        # Apply risk-level row coloring
        apply_risk_formatting(ws, row_idx, risk_level, 1, len(columns))

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
        risk_level = row_data.get("UserRiskLevel", "None")
        for col_idx, h in enumerate(headers, 1):
            val = row_data.get(h, "")
            if pd.isna(val):
                val = ""
            # Parse JSON columns
            if h in json_cols and isinstance(val, str):
                val = parse_json_list(val)

            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            # Use num style for numeric columns
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                cell.style = "num"
            else:
                cell.style = "data"

        apply_risk_formatting(ws, row_idx, risk_level, 1, len(headers))

    # Freeze panes & auto-filter
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(df)+1}"
    auto_width(ws, max_width=35)


# ============================================================
# SHEET 4: ACTION PLAN (based on MS Risk Level)
# ============================================================
def build_action_plan(ws, df):
    """Build the Action Plan sheet — based on MS Risk Level."""
    ws.sheet_properties.tabColor = "E74C3C"

    columns = [
        ("User", 35),
        ("Display Name", 28),
        ("Entity", 8),
        ("MS Risk Level", 14),
        ("Priority", 10),
        ("Recommended Actions", 75),
        ("Status", 12),
    ]

    # Headers
    for col_idx, (label, width) in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.style = "hdr"
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Action templates (mapped to risk_category keys)
    actions = {
        "confirmed": (
            "P1 — CRITICAL",
            "1. Revoke all active sessions immediately\n"
            "2. Reset password\n"
            "3. Re-enroll MFA (FIDO2 preferred)\n"
            "4. Review & remove suspicious mailbox rules\n"
            "5. Forensic review of MS risk event details\n"
            "6. Notify affected data owners"
        ),
        "likely": (
            "P2 — HIGH",
            "1. Revoke all active sessions\n"
            "2. Reset password\n"
            "3. Monitor sign-in activity for 72 hours\n"
            "4. Review mailbox rules for suspicious forwarding"
        ),
        "suspicious": (
            "P3 — MEDIUM",
            "1. Monitor sign-in activity\n"
            "2. Verify with user if activity is legitimate\n"
            "3. Consider password reset if unverified"
        ),
        "safe": (
            "P4 — LOW",
            "No immediate action required. Continue monitoring."
        ),
    }

    for row_idx, (_, row_data) in enumerate(df.iterrows(), 2):
        risk_level = row_data.get("UserRiskLevel", "None")
        cat = risk_category(risk_level)
        priority, action_text = actions[cat]

        values = [
            row_data.get("User", ""),
            row_data.get("DisplayName", ""),
            row_data.get("Entity", ""),
            risk_level,
            priority,
            action_text,
            "Pending",
        ]

        for col_idx, val in enumerate(values, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.style = "data"
            if col_idx == 6:  # Actions column — wrap text
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        apply_risk_formatting(ws, row_idx, risk_level, 1, len(columns))

        # Priority cell bold
        p_cell = ws.cell(row=row_idx, column=5)
        p_cell.font = Font(name="Calibri", size=10, bold=True, color=COLORS[f"{cat}_font"])

        # Row height for action text
        ws.row_dimensions[row_idx].height = 75 if cat in ("confirmed", "likely") else 40

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{len(df)+1}"



# ============================================================
# SHEET 5: METHODOLOGY (investigation approach)
# ============================================================
def build_methodology(ws):
    """Build the Methodology sheet documenting the investigation approach."""
    ws.sheet_properties.tabColor = "8E44AD"  # Purple

    # --- Title ---
    ws.merge_cells("A1:F1")
    title_cell = ws["A1"]
    title_cell.value = "Investigation Methodology — v6.0 (Microsoft Risk Signals)"
    title_cell.style = "title"
    ws.row_dimensions[1].height = 40

    ws.merge_cells("A2:F2")
    ws["A2"].value = "This report uses Microsoft Identity Protection ML signals as the primary risk assessment. No custom scoring system."
    ws["A2"].style = "sub"
    ws.row_dimensions[2].height = 22

    # --- Section 1: Risk Assessment Source ---
    row = 4
    ws.cell(row=row, column=1, value="RISK ASSESSMENT SOURCE").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 1

    headers = ["Risk Level", "RiskLevelDuringSignIn", "Color", "Meaning", "", ""]
    write_header_row(ws, row, headers)
    row += 1

    risk_levels = [
        ("High", ">= 100", "confirmed",
         "Microsoft ML detected high-confidence compromise indicators (token theft, impossible travel, known attacker IP, etc.)"),
        ("Medium", ">= 50", "likely",
         "Microsoft ML detected medium-confidence risk signals (atypical travel, suspicious browser, leaked credentials)"),
        ("Low", ">= 10", "suspicious",
         "Microsoft ML detected low-confidence anomalies (unfamiliar sign-in properties)"),
        ("None", "0 or N/A", "safe",
         "No risk signals detected by Microsoft Identity Protection"),
    ]

    for risk_name, threshold, cat, meaning in risk_levels:
        fill = get_risk_fill(cat)
        font = get_risk_font(cat)
        for col_idx, val in enumerate([risk_name, threshold, cat.upper(), meaning], 1):
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.fill = fill
            cell.font = font
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.merge_cells(start_row=row, start_column=4, end_row=row, end_column=6)
        ws.row_dimensions[row].height = 32
        row += 1

    # --- Section 2: Additional Evidence ---
    row += 1
    ws.cell(row=row, column=1, value="ADDITIONAL EVIDENCE (contextual — not scored)").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 1

    write_header_row(ws, row, ["Evidence Type", "Source", "Purpose", "", "", ""])
    row += 1

    evidence = [
        ("Foreign Country Sign-ins", "Q01 Sign-in History",
         "Non-BD sign-ins — may be legitimate VPN/travel or service proxies (e.g., AMC PROD)"),
        ("Defender Alerts", "Q03 Alert Data",
         "Unfamiliar sign-in property alerts triggered by Entra ID Protection"),
        ("ISP Analysis", "Q02 ISP Data",
         "Suspicious ISPs (hosting/VPN providers) — context for analyst review"),
        ("Phishing Emails", "Q05 Phishing Check",
         "User was targeted by phishing campaign — increases compromise likelihood"),
    ]

    for ev_type, source, purpose in evidence:
        for col_idx, val in enumerate([ev_type, source, purpose], 1):
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.style = "data"
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=6)
        ws.row_dimensions[row].height = 28
        row += 1

    # --- Section 3: Data Sources ---
    row += 1
    ws.cell(row=row, column=1, value="DATA SOURCES (KQL Queries)").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 1

    write_header_row(ws, row, ["Query", "Export File", "Table", "Purpose", "", ""])
    row += 1

    sources = [
        ("Q00", "unfamiliar_signin_incidents.csv", "AlertInfo + AlertEvidence",
         "Master query — all Unfamiliar Sign-in incidents, users, IPs"),
        ("Q01A-F", "signin_history_01..06.csv -> merged", "EntraIdSignInEvents",
         "Sign-in history (30 days, split 6 parts) + RiskLevelDuringSignIn + AuthProcessingDetails"),
        ("Q02", "isp_data.csv", "IdentityLogonEvents",
         "ISP enrichment — identify hosting/VPS/anonymous ISPs"),
        ("Q03", "alert_data.csv", "AlertEvidence",
         "Unfamiliar sign-in alert details per user"),
        ("Q04", "user_profiles.csv", "IdentityInfo",
         "User identity info — department, job title"),
        ("Q05", "phishing_emails.csv", "EmailEvents",
         "Phishing emails received by affected users"),

        ("Q10", "auth_status.csv", "IdentityAccountInfo",
         "MFA status, password reset history, admin roles"),
    ]

    for query, file, table, purpose in sources:
        for col_idx, val in enumerate([query, file, table, purpose], 1):
            cell = ws.cell(row=row, column=col_idx, value=val)
            cell.style = "data"
        ws.merge_cells(start_row=row, start_column=4, end_row=row, end_column=6)
        row += 1

    # --- Section 4: Important Notes ---
    row += 1
    ws.cell(row=row, column=1, value="IMPORTANT NOTES").style = "mlabel"
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=6)
    row += 1

    notes = [
        ("Why no custom scoring?", "Custom heuristics (DeviceName-based, off-hours, etc.) produced massive false positives. "
         "71% of sign-ins have empty DeviceName — a normal Entra ID behavior, not a risk indicator."),
        ("Why Microsoft Risk Signals?", "Microsoft Identity Protection has full visibility into token chains, browser fingerprints, "
         "and global attacker IP reputation. Their ML model is far more accurate than any custom heuristic."),
        ("Service App Traffic", "Internal apps (AMC PROD, My Profile) generate foreign sign-ins through Azure relay IPs. "
         "These are NOT actual user locations and should be ignored for geolocation analysis."),
        ("SOC Analyst Role", "This report provides DATA for analyst review. The analyst makes the final determination "
         "based on MS risk signals and contextual factors (travel, VPN, etc.)."),
        ("MS Infra IPs", "Microsoft infrastructure IPs (20.x, 40.x, 52.x, 2603:x) are auto-filtered before analysis."),
    ]

    for term, definition in notes:
        cell_t = ws.cell(row=row, column=1, value=term)
        cell_t.style = "mlabel"
        cell_d = ws.cell(row=row, column=2, value=definition)
        cell_d.style = "mval"
        ws.merge_cells(start_row=row, start_column=2, end_row=row, end_column=6)
        ws.row_dimensions[row].height = 36
        row += 1

    # Column widths
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 30
    ws.column_dimensions["E"].width = 18
    ws.column_dimensions["F"].width = 45



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

    # Sheet 4: Action Plan
    ws4 = wb.create_sheet("Action Plan")
    build_action_plan(ws4, df)

    # Sheet 5: Methodology
    ws5 = wb.create_sheet("Methodology")
    build_methodology(ws5)

    # Save
    wb.save(output_path)
    print(f"\U0001f4ca Excel report saved: {output_path}")


