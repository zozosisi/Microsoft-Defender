"""
Microsoft Defender XDR — Sign-in Investigation Analysis
========================================================
Phân tích sign-in history từ CSV exports, build baseline per user,
detect anomalies, tạo bảng tổng hợp.

Usage:
    python analyze_signins.py --data-dir ../incidents/data/exports
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
import json
import sys

# Excel report generation
from excel_report import generate_excel_report

# Force UTF-8 output to prevent Windows console emoji encode errors
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# CONFIGURATION
# ============================================================
TRUSTED_THRESHOLD = 0.05  # 5% — IP/Device/Browser >= 5% total sign-ins = Trusted



# Known BD ISPs (legitimate)
BD_ISPS_KEYWORDS = [
    "grameenphone", "robi", "banglalink", "teletalk", "btcl",
    "bangladesh", "dhaka", "carnation", "link3", "amber it",
    "aamra", "agni", "bracnet", "dhakacom", "earth telecommunication",
    "fiber@home", "isp", "maxnet", "ranks itt", "square",
    "summit communications", "x-press"
]

# Known CN ISPs (legitimate) — Fix: Post-Mortem #9 (Button Lin CSC entity)
CN_ISPS_KEYWORDS = [
    "china mobile", "chinanet", "chinatelecom", "china telecom",
    "china unicom", "tencent", "alibaba",
]

# Known VN ISPs (legitimate) — Fix: Post-Mortem #9 (Button Lin CSC entity)
VN_ISPS_KEYWORDS = [
    "viettel", "vnpt", "vietnam posts", "vietnam telecom",
    "netnam", "fpt telecom",
]

# Suspicious ISP keywords (VPN/Hosting/Proxy)
SUSPICIOUS_ISP_KEYWORDS = [
    "m247", "datacamp", "digitalocean", "hetzner", "ovh", "linode",
    "vultr", "amazon", "microsoft azure", "google cloud",
    "nordvpn", "expressvpn", "mullvad", "surfshark", "cyberghost",
    "private internet", "protonvpn", "tor", "cloudflare"
]

# Microsoft Infrastructure IP prefixes (Exchange Online backend, datacenter services)
# These IPs generate sign-in logs from M365 internal services, NOT from actual users.
# Source: MICROSOFT-CORP-MSN-AS-BLOCK (AS8075)
# Fix: Audit Report v2 — Rahim Uddin False Positive (BD→JP was Exchange Online datacenter)
MICROSOFT_INFRA_IP_PREFIXES = [
    "2603:1046:",   # Microsoft Corp MSN AS Block (Exchange Online - East Japan, etc.)
    "2603:1036:",   # Microsoft Corp (US regions)
    "2603:1026:",   # Microsoft Corp (EU regions)
    "2603:1056:",   # Microsoft Corp (APAC regions)
    "40.107.",      # Microsoft Exchange Online Protection
    "52.100.",      # Microsoft Exchange Online
    "20.190.",      # Azure AD / Entra ID authentication endpoints
    "40.126.",      # Azure AD / Entra ID authentication endpoints
]



BD_DOMAINS = [
    "crystal-abl.com.bd",
    "bd.crystal-martin.com",
    "crystal-cet.com.bd"
]


# ============================================================
# DATA LOADING
# ============================================================
def load_signin_data(data_dir: Path) -> pd.DataFrame:
    """Load merged sign-in history CSV."""
    path = data_dir / "signin_history.csv"
    if not path.exists():
        print(f"ERROR: signin_history.csv not found in {data_dir}")
        sys.exit(1)

    df = pd.read_csv(path, low_memory=False)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed")
    print(f"  ✓ Loaded signin_history.csv: {len(df)} rows")
    print(f"  → Unique users: {df['AccountUpn'].nunique()}")
    return df


def load_isp_data(data_dir: Path) -> pd.DataFrame:
    """Load ISP enrichment data."""
    path = data_dir / "isp_data.csv"
    if not path.exists():
        print("  ⚠ isp_data.csv not found — ISP analysis will be skipped")
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed")
    print(f"  ✓ Loaded isp_data.csv: {len(df)} rows")
    return df


def load_alert_data(data_dir: Path) -> pd.DataFrame:
    """Load alert correlation data."""
    path = data_dir / "alert_data.csv"
    if not path.exists():
        print("  ⚠ alert_data.csv not found — Alert analysis will be skipped")
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed")
    print(f"  ✓ Loaded alert_data.csv: {len(df)} rows")
    return df


def load_user_profiles(data_dir: Path) -> pd.DataFrame:
    """Load user profile data."""
    path = data_dir / "user_profiles.csv"
    if not path.exists():
        print("  ⚠ user_profiles.csv not found — Profile enrichment will be skipped")
        return pd.DataFrame()
    df = pd.read_csv(path)
    print(f"  ✓ Loaded user_profiles.csv: {len(df)} rows")
    return df


def load_phishing_data(data_dir: Path) -> pd.DataFrame:
    """Load phishing email data."""
    path = data_dir / "phishing_emails.csv"
    if not path.exists():
        print("  ⚠ phishing_emails.csv not found — Phishing analysis will be skipped")
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed")
    print(f"  ✓ Loaded phishing_emails.csv: {len(df)} rows")
    return df




def load_unfamiliar_signin_data(data_dir: Path) -> pd.DataFrame:
    """Load Unfamiliar Sign-in Incidents data (Q00).
    
    This file contains alert IPs from Entra ID Protection 'Unfamiliar sign-in properties'
    detections, including both successful and blocked sign-in attempts.
    Source: alert_pipeline_source_of_truth.md — confirmed via MS docs + tenant CA policies.
    """
    path = data_dir / "unfamiliar_signin_incidents.csv"
    if not path.exists():
        print("  ⚠ unfamiliar_signin_incidents.csv not found — Alert IP correlation will be skipped")
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    if "AlertTimestamp" in df.columns:
        df["AlertTimestamp"] = pd.to_datetime(df["AlertTimestamp"], format="mixed")
    print(f"  ✓ Loaded unfamiliar_signin_incidents.csv: {len(df)} rows")
    print(f"    → Unique Alert IPs: {df['RemoteIP'].nunique() if 'RemoteIP' in df.columns else 'N/A'}")
    return df



def is_microsoft_infra_ip(ip: str) -> bool:
    """Check if an IP belongs to Microsoft infrastructure (Exchange Online backend, etc.).
    
    These IPs generate sign-in logs from internal M365 services (Managed Folder Assistant,
    mailbox auditing, auto-forwarding checks), NOT from actual user activity.
    Country field may show JP/US/EU based on datacenter location, causing False Positives.
    """
    if pd.isna(ip) or ip == "":
        return False
    return any(str(ip).startswith(prefix) for prefix in MICROSOFT_INFRA_IP_PREFIXES)


# ============================================================
# BASELINE BUILDING
# ============================================================
def get_entity(upn: str) -> str:
    """Extract entity from UPN domain."""
    if "crystal-abl.com.bd" in upn:
        return "ABL"
    elif "bd.crystal-martin.com" in upn:
        return "CMBD"
    elif "crystal-cet.com.bd" in upn:
        return "CETBD"
    elif "crystal-csc.cn" in upn:  # Fix: Post-Mortem #9 — CSC China entity
        return "CSC"
    return "OTHER"


def build_trusted_set(series: pd.Series, threshold: float) -> list:
    """
    From a series of values, find items that appear >= threshold% of total.
    Returns list of trusted values.
    """
    if series.empty:
        return []
    counts = series.value_counts()
    total = len(series)
    trusted = counts[counts / total >= threshold].index.tolist()
    return trusted


def classify_isp(isp: str) -> str:
    """Classify ISP as BD-Trusted/CN-Trusted/VN-Trusted/Suspicious/Unknown."""
    if pd.isna(isp) or isp == "":
        return "Unknown"
    isp_lower = isp.lower()
    for kw in SUSPICIOUS_ISP_KEYWORDS:
        if kw in isp_lower:
            return "Suspicious"
    for kw in BD_ISPS_KEYWORDS:
        if kw in isp_lower:
            return "BD-Trusted"
    # Fix: Post-Mortem #9 — nhận diện ISP Trung Quốc và Việt Nam
    for kw in CN_ISPS_KEYWORDS:
        if kw in isp_lower:
            return "CN-Trusted"
    for kw in VN_ISPS_KEYWORDS:
        if kw in isp_lower:
            return "VN-Trusted"
    return "Unknown"


def build_user_baseline(user_df: pd.DataFrame) -> dict:
    """Build behavioral baseline for a single user from their sign-in history."""
    baseline = {}

    # Sign-in volume
    baseline["TotalSignIns"] = len(user_df)
    baseline["FirstSignIn"] = user_df["Timestamp"].min().strftime("%Y-%m-%d %H:%M")
    baseline["LastSignIn"] = user_df["Timestamp"].max().strftime("%Y-%m-%d %H:%M")
    baseline["ActiveDays"] = user_df["Timestamp"].dt.date.nunique()

    # Trusted IPs
    baseline["TrustedIPs"] = build_trusted_set(
        user_df["IPAddress"].dropna(), TRUSTED_THRESHOLD
    )
    baseline["TotalUniqueIPs"] = user_df["IPAddress"].nunique()

    # Countries
    baseline["TrustedCountries"] = build_trusted_set(
        user_df["Country"].dropna(), TRUSTED_THRESHOLD
    )
    baseline["AllCountries"] = sorted(user_df["Country"].dropna().unique().tolist())

    # Trusted Devices
    baseline["TrustedDevices"] = build_trusted_set(
        user_df["DeviceName"].dropna(), TRUSTED_THRESHOLD
    )
    baseline["TotalUniqueDevices"] = user_df["DeviceName"].nunique()

    # Trusted Browsers
    baseline["TrustedBrowsers"] = build_trusted_set(
        user_df["Browser"].dropna(), TRUSTED_THRESHOLD
    )

    # Trusted OS
    baseline["TrustedOS"] = build_trusted_set(
        user_df["OSPlatform"].dropna(), TRUSTED_THRESHOLD
    )

    # Device posture
    baseline["ManagedSignIns"] = int((user_df["IsManaged"] == 1).sum())
    baseline["UnmanagedSignIns"] = int((user_df["IsManaged"] != 1).sum())
    baseline["CompliantSignIns"] = int((user_df["IsCompliant"] == 1).sum())

    return baseline


# ============================================================
# DATA AGGREGATION (context only — no scoring)
# ============================================================
def aggregate_user_data(user_df: pd.DataFrame, baseline: dict) -> dict:
    """Aggregate sign-in data for reporting. No scoring — context only."""
    result = {}

    # Filter out Microsoft infrastructure IPs
    ms_infra_mask = user_df["IPAddress"].apply(is_microsoft_infra_ip)
    result["MicrosoftInfraIPsFiltered"] = int(ms_infra_mask.sum())
    filtered_df = user_df[~ms_infra_mask].copy()

    # Foreign country sign-ins (non-BD)
    non_bd_mask = (filtered_df["Country"] != "BD") & filtered_df["Country"].notna()
    result["NonBDSignIns"] = int(non_bd_mask.sum())
    result["NonBDCountries"] = sorted(
        filtered_df.loc[non_bd_mask, "Country"].unique().tolist()
    )

    # Foreign vs trusted countries
    trusted_countries = set(baseline["TrustedCountries"])
    foreign_mask = ~filtered_df["Country"].isin(trusted_countries) & filtered_df["Country"].notna()
    result["ForeignCountrySignIns"] = int(foreign_mask.sum())
    result["ForeignCountryList"] = sorted(
        filtered_df.loc[foreign_mask, "Country"].unique().tolist()
    )

    # Unknown IPs (for context only)
    trusted_ips = set(baseline["TrustedIPs"])
    unknown_ip_mask = ~filtered_df["IPAddress"].isin(trusted_ips)
    result["UnknownIPSignIns"] = int(unknown_ip_mask.sum())
    result["UnknownIPList"] = sorted(
        filtered_df.loc[unknown_ip_mask, "IPAddress"].unique().tolist()
    )

    # --- Microsoft Risk Signals (raw values — no custom categorization) ---
    risk_col = "RiskLevelDuringSignIn"
    if risk_col in filtered_df.columns:
        numeric_risk = pd.to_numeric(filtered_df[risk_col], errors='coerce').fillna(0)
        result["RiskSignIns"] = int((numeric_risk > 0).sum())
        result["MaxRiskScore"] = int(numeric_risk.max())
    else:
        result["RiskSignIns"] = 0
        result["MaxRiskScore"] = 0

    # Risk event types
    if "RiskEventTypes" in filtered_df.columns:
        risk_events = filtered_df["RiskEventTypes"].dropna().astype(str)
        risk_events = risk_events[(risk_events.str.strip() != "") & (risk_events != "[]")]
        result["MSRiskEvents"] = len(risk_events)
    else:
        result["MSRiskEvents"] = 0

    return result



def enrich_with_isp(user_upn: str, isp_df: pd.DataFrame) -> dict:
    """Get ISP info for a user from IdentityLogonEvents data."""
    if isp_df.empty:
        return {"ISPList": [], "UniqueISPs": 0, "SuspiciousISPs": []}

    user_isp = isp_df[isp_df["AccountUpn"].str.lower() == user_upn.lower()]
    if user_isp.empty:
        return {"ISPList": [], "UniqueISPs": 0, "SuspiciousISPs": []}

    isp_list = user_isp["ISP"].dropna().unique().tolist()
    suspicious = [i for i in isp_list if classify_isp(i) == "Suspicious"]

    return {
        "ISPList": sorted(isp_list),
        "UniqueISPs": len(isp_list),
        "SuspiciousISPs": suspicious
    }


def enrich_with_alerts(user_upn: str, alert_df: pd.DataFrame) -> dict:
    """Get alert count and timeline for a user."""
    if alert_df.empty:
        return {"AlertCount": 0, "FirstAlert": "", "LastAlert": ""}

    user_alerts = alert_df[alert_df["AccountUpn"].str.lower() == user_upn.lower()]
    if user_alerts.empty:
        return {"AlertCount": 0, "FirstAlert": "", "LastAlert": ""}

    return {
        "AlertCount": user_alerts["AlertId"].nunique(),
        "FirstAlert": user_alerts["Timestamp"].min().strftime("%Y-%m-%d"),
        "LastAlert": user_alerts["Timestamp"].max().strftime("%Y-%m-%d")
    }


def enrich_with_profile(user_upn: str, profile_df: pd.DataFrame) -> dict:
    """Get user profile info."""
    if profile_df.empty:
        return {"Department": "", "JobTitle": "", "ProfileRiskLevel": ""}

    user_profile = profile_df[profile_df["AccountUpn"].str.lower() == user_upn.lower()]
    if user_profile.empty:
        return {"Department": "", "JobTitle": "", "ProfileRiskLevel": ""}

    row = user_profile.iloc[0]
    return {
        "Department": str(row.get("Department", "")),
        "JobTitle": str(row.get("JobTitle", "")),
        "ProfileRiskLevel": str(row.get("RiskLevel", ""))
    }


def enrich_with_phishing(user_upn: str, phish_df: pd.DataFrame) -> dict:
    """Check if user received phishing emails."""
    if phish_df.empty:
        return {"PhishingEmailsReceived": 0}

    # Match by email address (UPN is usually the email)
    user_phish = phish_df[
        phish_df["RecipientEmailAddress"].str.lower() == user_upn.lower()
    ]
    return {"PhishingEmailsReceived": len(user_phish)}










def enrich_with_unfamiliar_signins(user_upn: str, unfamiliar_df: pd.DataFrame,
                                    suspicious_ips: list) -> dict:
    """Cross-reference user's suspicious IPs with Unfamiliar Sign-in alert IPs.
    
    Purpose: Boost scoring confidence when a suspicious IP is also flagged by
    Entra ID Protection as 'Unfamiliar sign-in properties'.
    Source: alert_pipeline_source_of_truth.md — Gap 1 alignment fix.
    """
    result = {
        "AlertIPsMatched": [],
        "AlertIPsMatchedCount": 0,
        "UserAlertCount": 0,
        "FirstAlertTimestamp": "",
        "CrossUserAlertIPs": [],
    }
    
    if unfamiliar_df.empty or "RemoteIP" not in unfamiliar_df.columns:
        return result
    
    # Get all alert IPs for THIS user
    user_alerts = unfamiliar_df[
        unfamiliar_df["AccountUpn"].str.lower() == user_upn.lower()
    ]
    
    if not user_alerts.empty:
        result["UserAlertCount"] = len(user_alerts)
        if "AlertTimestamp" in user_alerts.columns:
            result["FirstAlertTimestamp"] = user_alerts["AlertTimestamp"].min().strftime("%Y-%m-%d %H:%M")
    
    # Cross-reference: which of our suspicious IPs are ALSO in alert IPs?
    all_alert_ips = set(unfamiliar_df["RemoteIP"].dropna().unique())
    matched = [ip for ip in suspicious_ips if ip in all_alert_ips]
    result["AlertIPsMatched"] = sorted(matched)
    result["AlertIPsMatchedCount"] = len(matched)
    
    # Cross-user: alert IPs for OTHER users that appear in this user's sign-ins
    other_user_alert_ips = set(
        unfamiliar_df[
            unfamiliar_df["AccountUpn"].str.lower() != user_upn.lower()
        ]["RemoteIP"].dropna().unique()
    )
    cross_user = [ip for ip in suspicious_ips if ip in other_user_alert_ips]
    result["CrossUserAlertIPs"] = sorted(cross_user)

    return result







# ============================================================
# MAIN ANALYSIS
# ============================================================
def analyze(data_dir: Path, output_dir: Path):
    """Main analysis pipeline — v6.0 (Microsoft Risk Signals only, no custom scoring)."""
    print("=" * 60)
    print("Microsoft Defender XDR — Sign-in Investigation Analysis v6.0")
    print("=" * 60)

    # Load data
    print("\n📂 Loading data...")
    signin_df = load_signin_data(data_dir)
    isp_df = load_isp_data(data_dir)
    alert_df = load_alert_data(data_dir)
    profile_df = load_user_profiles(data_dir)
    phish_df = load_phishing_data(data_dir)


    unfamiliar_df = load_unfamiliar_signin_data(data_dir)

    # Get unique users
    users = sorted(signin_df["AccountUpn"].unique())
    print(f"\n🔍 Analyzing {len(users)} users...")

    # Process each user
    results = []

    for i, upn in enumerate(users):
        print(f"  [{i+1}/{len(users)}] {upn}")
        user_df = signin_df[signin_df["AccountUpn"] == upn].copy()

        # Build baseline
        baseline = build_user_baseline(user_df)

        # Aggregate data (context only — no scoring)
        user_data = aggregate_user_data(user_df, baseline)

        # Enrich with ISP, alerts, profile, phishing
        isp_info = enrich_with_isp(upn, isp_df)
        alert_info = enrich_with_alerts(upn, alert_df)
        profile_info = enrich_with_profile(upn, profile_df)
        phishing_info = enrich_with_phishing(upn, phish_df)


        unknown_ips = user_data.get("UnknownIPList", [])

        # Unfamiliar Sign-in alert IPs (Q00)
        unfamiliar_info = enrich_with_unfamiliar_signins(upn, unfamiliar_df, unknown_ips)



        # Build summary row (no AnomalyScore, no Verdict — MS Risk only)
        row = {
            # Identity
            "User": upn,
            "DisplayName": user_df["AccountDisplayName"].iloc[0] if len(user_df) > 0 else "",
            "Entity": get_entity(upn),
            "Department": profile_info["Department"],
            "JobTitle": profile_info["JobTitle"],
            # Microsoft Risk Signals (raw — no custom categorization)
            "RiskSignIns": user_data["RiskSignIns"],
            "MaxRiskScore": user_data["MaxRiskScore"],
            "MSRiskEvents": user_data["MSRiskEvents"],
            # Sign-in volume
            "TotalSignIns": baseline["TotalSignIns"],
            "ActiveDays": baseline["ActiveDays"],
            "FirstSignIn": baseline["FirstSignIn"],
            "LastSignIn": baseline["LastSignIn"],
            # Foreign access
            "ForeignCountrySignIns": user_data["ForeignCountrySignIns"],
            "ForeignCountryList": json.dumps(user_data["ForeignCountryList"]),
            "NonBDSignIns": user_data["NonBDSignIns"],
            "NonBDCountries": json.dumps(user_data["NonBDCountries"]),
            # Baseline context
            "TrustedIPs": json.dumps(baseline["TrustedIPs"]),
            "TrustedIPCount": len(baseline["TrustedIPs"]),
            "TotalUniqueIPs": baseline["TotalUniqueIPs"],
            "TrustedCountries": json.dumps(baseline["TrustedCountries"]),
            "AllCountries": json.dumps(baseline["AllCountries"]),
            "TrustedCountryCount": len(baseline["TrustedCountries"]),
            "TrustedDevices": json.dumps(baseline["TrustedDevices"]),
            "TrustedBrowsers": json.dumps(baseline["TrustedBrowsers"]),
            "TrustedOS": json.dumps(baseline["TrustedOS"]),
            "ISPList": json.dumps(isp_info["ISPList"]),
            "UniqueISPs": isp_info["UniqueISPs"],
            "SuspiciousISPs": json.dumps(isp_info["SuspiciousISPs"]),
            # Unknown IPs (context)
            "UnknownIPSignIns": user_data["UnknownIPSignIns"],
            "UnknownIPList": json.dumps(user_data["UnknownIPList"]),
            # Alerts
            "AlertCount": alert_info["AlertCount"],
            "FirstAlert": alert_info["FirstAlert"],
            "LastAlert": alert_info["LastAlert"],
            # Phishing
            "PhishingEmailsReceived": phishing_info["PhishingEmailsReceived"],


            # Unfamiliar Sign-in Alert correlation (Q00)
            "AlertIPsMatched": json.dumps(unfamiliar_info["AlertIPsMatched"]),
            "AlertIPsMatchedCount": unfamiliar_info["AlertIPsMatchedCount"],
            "UserAlertCount_Q00": unfamiliar_info["UserAlertCount"],

            # Device posture
            "ManagedSignIns": baseline["ManagedSignIns"],
            "UnmanagedSignIns": baseline["UnmanagedSignIns"],
            # Infra
            "MicrosoftInfraIPsFiltered": user_data["MicrosoftInfraIPsFiltered"],
        }
        results.append(row)

    # Create output DataFrame — sorted by MaxRiskScore desc, then RiskSignIns desc
    summary_df = pd.DataFrame(results)
    summary_df = summary_df.sort_values(
        ["MaxRiskScore", "RiskSignIns"],
        ascending=[False, False]
    )

    # Export
    output_dir.mkdir(parents=True, exist_ok=True)

    # Excel report (professional multi-sheet workbook)
    xlsx_path = output_dir / "investigation_report.xlsx"
    generate_excel_report(summary_df, xlsx_path, TRUSTED_THRESHOLD)
    print(f"\n📊 Excel report saved: {xlsx_path}")

    # Print summary stats
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_with_risk = len(summary_df[summary_df["RiskSignIns"] > 0])
    print(f"  Users with MS Risk Events: {total_with_risk} / {len(summary_df)}")

    # Users with MS risk events
    risky = summary_df[summary_df["RiskSignIns"] > 0]
    if len(risky) > 0:
        print(f"\n🔍 USERS WITH MICROSOFT RISK EVENTS:")
        for _, row in risky.iterrows():
            print(f"  • {row['User']} (MaxRisk: {row['MaxRiskScore']}, "
                  f"RiskSignIns: {row['RiskSignIns']}, "
                  f"Foreign: {row['NonBDSignIns']})")



    return summary_df




# ============================================================
# CLI
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Analyze Defender XDR sign-in data for BD users"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="../incidents/data/export",
        help="Directory containing exported CSV files"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="../incidents/analysis",
        help="Directory for output files"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Trusted threshold (default: 0.05 = 5%%)"
    )
    args = parser.parse_args()

    global TRUSTED_THRESHOLD
    TRUSTED_THRESHOLD = args.threshold

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        print(f"Create the directory and place exported CSV files there.")
        print(f"\nExpected files:")
        print(f"  - signin_history.csv (required)")
        print(f"  - isp_data.csv")
        print(f"  - alert_data.csv")
        print(f"  - user_profiles.csv")
        print(f"  - phishing_emails.csv")
        sys.exit(1)

    analyze(data_dir, output_dir)


if __name__ == "__main__":
    main()
