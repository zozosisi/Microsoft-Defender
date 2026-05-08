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

# Force UTF-8 output to prevent Windows console emoji encode errors
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# CONFIGURATION
# ============================================================
TRUSTED_THRESHOLD = 0.05  # 5% — IP/Device/Browser >= 5% total sign-ins = Trusted
NORMAL_HOUR_THRESHOLD = 0.03  # 3% — hour with >= 3% sign-ins = Normal hour

# Known BD ISPs (legitimate)
BD_ISPS_KEYWORDS = [
    "grameenphone", "robi", "banglalink", "teletalk", "btcl",
    "bangladesh", "dhaka", "carnation", "link3", "amber it",
    "aamra", "agni", "bracnet", "dhakacom", "earth telecommunication",
    "fiber@home", "isp", "maxnet", "ranks itt", "square",
    "summit communications", "x-press"
]

# Suspicious ISP keywords (VPN/Hosting/Proxy)
SUSPICIOUS_ISP_KEYWORDS = [
    "m247", "datacamp", "digitalocean", "hetzner", "ovh", "linode",
    "vultr", "amazon", "microsoft azure", "google cloud",
    "nordvpn", "expressvpn", "mullvad", "surfshark", "cyberghost",
    "private internet", "protonvpn", "tor", "cloudflare"
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


def load_cloudapp_data(data_dir: Path) -> pd.DataFrame:
    """Load CloudAppEvents data for post-breach analysis."""
    path = data_dir / "cloudapp_events.csv"
    if not path.exists():
        print("  ⚠ cloudapp_events.csv not found — Post-breach analysis will be skipped")
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], format="mixed")
    print(f"  ✓ Loaded cloudapp_events.csv: {len(df)} rows")
    return df


def load_auth_status(data_dir: Path) -> pd.DataFrame:
    """Load MFA and Password reset data."""
    path = data_dir / "auth_status.csv"
    if not path.exists():
        print("  ⚠ auth_status.csv not found — Auth status enrichment will be skipped")
        return pd.DataFrame()
    df = pd.read_csv(path, low_memory=False)
    print(f"  ✓ Loaded auth_status.csv: {len(df)} rows")
    return df



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
    """Classify ISP as BD/Suspicious/Unknown."""
    if pd.isna(isp) or isp == "":
        return "Unknown"
    isp_lower = isp.lower()
    for kw in SUSPICIOUS_ISP_KEYWORDS:
        if kw in isp_lower:
            return "Suspicious"
    for kw in BD_ISPS_KEYWORDS:
        if kw in isp_lower:
            return "BD-Trusted"
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

    # Trusted Countries
    baseline["TrustedCountries"] = build_trusted_set(
        user_df["Country"].dropna(), TRUSTED_THRESHOLD
    )
    baseline["AllCountries"] = sorted(user_df["Country"].dropna().unique().tolist())

    # Trusted Cities
    baseline["TrustedCities"] = build_trusted_set(
        user_df["City"].dropna(), TRUSTED_THRESHOLD
    )

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

    # Normal hours (UTC)
    hours = user_df["Timestamp"].dt.hour
    hour_counts = hours.value_counts()
    total = len(hours)
    normal_hours = sorted(
        hour_counts[hour_counts / total >= NORMAL_HOUR_THRESHOLD].index.tolist()
    )
    baseline["NormalHours"] = normal_hours

    # Device posture
    baseline["ManagedSignIns"] = int((user_df["IsManaged"] == 1).sum())
    baseline["UnmanagedSignIns"] = int((user_df["IsManaged"] != 1).sum())
    baseline["CompliantSignIns"] = int((user_df["IsCompliant"] == 1).sum())

    return baseline


# ============================================================
# ANOMALY DETECTION
# ============================================================
def detect_user_anomalies(user_df: pd.DataFrame, baseline: dict) -> dict:
    """Compare each sign-in against baseline, compute anomaly metrics."""
    anomalies = {}

    # Unknown IP sign-ins
    trusted_ips = set(baseline["TrustedIPs"])
    unknown_ip_mask = ~user_df["IPAddress"].isin(trusted_ips)
    anomalies["UnknownIPSignIns"] = int(unknown_ip_mask.sum())
    anomalies["UnknownIPList"] = sorted(
        user_df.loc[unknown_ip_mask, "IPAddress"].unique().tolist()
    )

    # Foreign country sign-ins
    trusted_countries = set(baseline["TrustedCountries"])
    foreign_mask = ~user_df["Country"].isin(trusted_countries) & user_df["Country"].notna()
    anomalies["ForeignCountrySignIns"] = int(foreign_mask.sum())
    anomalies["ForeignCountryList"] = sorted(
        user_df.loc[foreign_mask, "Country"].unique().tolist()
    )

    # Non-BD sign-ins (specific check)
    non_bd_mask = (user_df["Country"] != "BD") & user_df["Country"].notna()
    anomalies["NonBDSignIns"] = int(non_bd_mask.sum())
    anomalies["NonBDCountries"] = sorted(
        user_df.loc[non_bd_mask, "Country"].unique().tolist()
    )

    # VPN vs Hacker Botnet logic
    # Hacker: Foreign country sign-ins with Unknown Device (empty or not in trusted)
    trusted_devices = set(baseline["TrustedDevices"])
    hacker_mask = foreign_mask & (~user_df["DeviceName"].isin(trusted_devices) | user_df["DeviceName"].isna() | (user_df["DeviceName"].str.strip() == ""))
    vpn_mask = foreign_mask & user_df["DeviceName"].isin(trusted_devices) & user_df["DeviceName"].notna() & (user_df["DeviceName"].str.strip() != "")

    anomalies["HackerBotnetSignIns"] = int(hacker_mask.sum())
    anomalies["VPNSignIns"] = int(vpn_mask.sum())
    anomalies["HackerBotnetCountries"] = sorted(user_df.loc[hacker_mask, "Country"].dropna().unique().tolist())
    anomalies["VPNCountries"] = sorted(user_df.loc[vpn_mask, "Country"].dropna().unique().tolist())

    # Unknown device sign-ins
    trusted_devices = set(baseline["TrustedDevices"])
    unknown_dev_mask = ~user_df["DeviceName"].isin(trusted_devices) | user_df["DeviceName"].isna() | (user_df["DeviceName"].str.strip() == "")
    anomalies["UnknownDeviceSignIns"] = int(unknown_dev_mask.sum())
    
    # Trusted Device IPs (IPs that have been seen with a Trusted Device at least once)
    trusted_device_ips = set(user_df.loc[user_df["DeviceName"].isin(trusted_devices), "IPAddress"].dropna().unique())
    
    # Suspicious IPs for Data Breach Analysis (Unknown IP + never used with a Trusted Device)
    # This prevents False Positives where Entra ID telemetry randomly drops the DeviceName on a legitimate connection.
    suspicious_ip_mask = unknown_ip_mask & ~user_df["IPAddress"].isin(trusted_device_ips)
    suspicious_ip_list = sorted(user_df.loc[suspicious_ip_mask, "IPAddress"].dropna().unique().tolist())
    anomalies["SuspiciousIPList"] = suspicious_ip_list
    
    # Benign Unknown IPs = Unknown IP but Trusted Device (e.g., employee on hotel WiFi)
    # These are NOT double-counted with SuspiciousIPList in scoring
    all_unknown_ips = set(anomalies["UnknownIPList"])
    suspicious_ips_set = set(suspicious_ip_list)
    benign_unknown_ips = all_unknown_ips - suspicious_ips_set
    anomalies["BenignUnknownIPCount"] = len(benign_unknown_ips)
    
    anomalies["UnknownDeviceList"] = sorted(
        user_df.loc[unknown_dev_mask, "DeviceName"].dropna().unique().tolist()
    )

    # Unknown browser sign-ins
    trusted_browsers = set(baseline["TrustedBrowsers"])
    unknown_br_mask = ~user_df["Browser"].isin(trusted_browsers) & user_df["Browser"].notna()
    anomalies["UnknownBrowserSignIns"] = int(unknown_br_mask.sum())

    # Off-hours sign-ins
    normal_hours = set(baseline["NormalHours"])
    hours = user_df["Timestamp"].dt.hour
    offhours_mask = ~hours.isin(normal_hours)
    anomalies["OffHoursSignIns"] = int(offhours_mask.sum())

    # High risk sign-ins (RiskLevelDuringSignIn >= 50 = Medium+)
    risk_col = "RiskLevelDuringSignIn"
    if risk_col in user_df.columns:
        numeric_risk = pd.to_numeric(user_df[risk_col], errors='coerce').fillna(0)
        anomalies["HighRiskSignIns"] = int((numeric_risk >= 50).sum())
    else:
        anomalies["HighRiskSignIns"] = 0

    # Unmanaged device percentage
    total = baseline["TotalSignIns"]
    anomalies["UnmanagedPct"] = round(
        baseline["UnmanagedSignIns"] / total * 100, 1
    ) if total > 0 else 0

    return anomalies


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


def enrich_with_cloudapp(user_upn: str, account_object_id: str, cloudapp_df: pd.DataFrame, untrusted_ips: list) -> dict:
    """Check CloudAppEvents for data breach actions from untrusted IPs."""
    if cloudapp_df.empty or not untrusted_ips:
        return {"DataBreachEvents": 0, "DataBreachActions": []}

    # Match by UPN (AccountId) OR AccountObjectId — no partial match to avoid false positives
    user_ca = cloudapp_df[
        (cloudapp_df["AccountId"].str.lower() == user_upn.lower()) |
        (cloudapp_df["AccountObjectId"] == account_object_id)
    ]
    
    if user_ca.empty:
        return {"DataBreachEvents": 0, "DataBreachActions": []}
        
    # Filter by Untrusted IPs (from anomalies)
    hacker_ca = user_ca[user_ca["IPAddress"].isin(untrusted_ips)]
    
    # Full list of suspicious actions (aligned with detection_logic_reference.md Section 3B)
    suspicious_actions = [
        'FileDownloaded', 'FileAccessed',           # Data theft / snooping
        'New-InboxRule', 'Set-InboxRule',            # Persistence / anti-forensics
        'MailItemsAccessed', 'eDiscoverySearch',     # Email snooping
        'FileRecycled', 'FolderRecycled',            # Data destruction
        'MessageSent',                               # Lateral movement via Teams
    ]
    
    breach_events = hacker_ca[hacker_ca["ActionType"].isin(suspicious_actions)]
    
    return {
        "DataBreachEvents": len(breach_events),
        "DataBreachActions": sorted(breach_events["ActionType"].unique().tolist())
    }


def enrich_with_auth_status(user_upn: str, auth_df: pd.DataFrame, user_df: pd.DataFrame) -> dict:
    """Extract MFA, Password reset, Account status, and Admin roles for a user."""
    result = {
        "MFAStatus": "Not Enrolled / Unknown",
        "LastPasswordReset": "Unknown",
        "AccountStatus": "Unknown",
        "IsAdmin": False,
    }
    
    # Fallback 1: Infer MFA from Sign-in Logs (AuthenticationRequirement)
    if not user_df.empty and "AuthenticationRequirement" in user_df.columns:
        mfa_signins = user_df[user_df["AuthenticationRequirement"].str.lower() == "multifactorauthentication"]
        if len(mfa_signins) > 0:
            result["MFAStatus"] = "MFA Enforced (Detected from Sign-ins)"

    # Fallback 2: IdentityAccountInfo (auth_status.csv)
    if not auth_df.empty:
        user_auth = auth_df[auth_df["AccountUpn"].str.lower() == user_upn.lower()]
        if not user_auth.empty:
            row = user_auth.iloc[0]
            
            # Parse MFA
            mfa_str = str(row.get("EnrolledMfas", ""))
            if pd.notna(row.get("EnrolledMfas")) and mfa_str.strip().lower() not in ("[]", "", "nan"):
                try:
                    mfa_list = json.loads(mfa_str)
                    result["MFAStatus"] = ", ".join(mfa_list)
                except (json.JSONDecodeError, ValueError, TypeError):
                    result["MFAStatus"] = mfa_str
                    
            # Parse Password Reset
            pwd_time = row.get("LastPasswordChangeTime")
            if pd.notna(pwd_time) and str(pwd_time).strip().lower() not in ("invalid date", "nat", "nan", ""):
                result["LastPasswordReset"] = str(pwd_time)
            
            # Parse Account Status (from Q10 enrichment)
            acct_status = row.get("AccountStatus", "")
            if pd.notna(acct_status) and str(acct_status).strip():
                result["AccountStatus"] = str(acct_status).strip()
            
            # Parse Assigned Roles — check if user is admin
            roles_str = str(row.get("AssignedRoles", "[]"))
            if pd.notna(row.get("AssignedRoles")) and roles_str.strip().lower() not in ("[]", "", "nan"):
                try:
                    roles_list = json.loads(roles_str)
                    if len(roles_list) > 0:
                        result["IsAdmin"] = True
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
        
    return result



# ============================================================
# VERDICT SCORING
# ============================================================
def compute_verdict(anomalies: dict, isp_info: dict, alert_info: dict,
                    phishing_info: dict, cloudapp_info: dict,
                    auth_info: dict = None) -> tuple:
    """Compute anomaly score and verdict for a user."""
    score = 0

    # Foreign country sign-ins: Penalize Hacker variety, not VPN variety
    # VPN Countries = +0 points (legitimate)
    # Hacker Countries = +30 points per distinct country
    score += len(anomalies.get("VPNCountries", [])) * 0
    score += len(anomalies.get("HackerBotnetCountries", [])) * 30

    # Suspicious IP sign-ins (Unknown IP + Unknown Device) — catches domestic hackers
    # +5 points per suspicious IP, max 50 pts (post-mortem #1: hacker can use local ISP)
    score += min(len(anomalies.get("SuspiciousIPList", [])), 10) * 5

    # Suspicious ISPs: High penalty per suspicious ISP
    score += len(isp_info.get("SuspiciousISPs", [])) * 15

    # Benign Unknown IPs (Unknown IP + Trusted Device = likely travel/VPN)
    # Only count IPs NOT already in SuspiciousIPList to avoid double-counting
    score += min(anomalies.get("BenignUnknownIPCount", 0), 15) * 2

    # High risk sign-ins (Entra ID Risk Event)
    score += anomalies.get("HighRiskSignIns", 0) * 5

    # Phishing emails received
    score += phishing_info.get("PhishingEmailsReceived", 0) * 5

    # Data Breach Actions (CloudAppEvents)
    if cloudapp_info.get("DataBreachEvents", 0) > 0:
        score += 1000  # Instant massive penalty

    # Off-hours sign-ins (cap at 10 pts)
    score += min(anomalies.get("OffHoursSignIns", 0), 20) * 0.5

    # Alert count (Defender Alerts)
    score += min(alert_info.get("AlertCount", 0), 5) * 5

    # Unmanaged device percentage
    if anomalies.get("UnmanagedPct", 0) > 80:
        score += 5

    # Admin account severity boost (+10 if compromised admin)
    if auth_info and auth_info.get("IsAdmin", False) and score >= 15:
        score += 10

    # Classify
    if cloudapp_info.get("DataBreachEvents", 0) > 0:
        verdict = "🚨 CONFIRMED COMPROMISED (Data Breach)"
    elif score >= 30:
        verdict = "🔴 Likely Compromised"
    elif score >= 15:
        verdict = "🟠 Suspicious"
    else:
        verdict = "🟢 Likely Safe"

    return round(score, 1), verdict


# ============================================================
# MAIN ANALYSIS
# ============================================================
def analyze(data_dir: Path, output_dir: Path):
    """Main analysis pipeline."""
    print("=" * 60)
    print("Microsoft Defender XDR — Sign-in Investigation Analysis")
    print("=" * 60)

    # Load data
    print("\n📂 Loading data...")
    signin_df = load_signin_data(data_dir)
    isp_df = load_isp_data(data_dir)
    alert_df = load_alert_data(data_dir)
    profile_df = load_user_profiles(data_dir)
    phish_df = load_phishing_data(data_dir)
    cloudapp_df = load_cloudapp_data(data_dir)
    auth_df = load_auth_status(data_dir)

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

        # Detect anomalies
        anomalies = detect_user_anomalies(user_df, baseline)

        # Enrich with ISP, alerts, profile, phishing
        isp_info = enrich_with_isp(upn, isp_df)
        alert_info = enrich_with_alerts(upn, alert_df)
        profile_info = enrich_with_profile(upn, profile_df)
        phishing_info = enrich_with_phishing(upn, phish_df)
        auth_info = enrich_with_auth_status(upn, auth_df, user_df)
        
        # Get suspicious IPs for cloudapp filter (Unknown IP + Unknown Device)
        suspicious_ips = anomalies.get("SuspiciousIPList", [])
        account_object_id = user_df["AccountObjectId"].iloc[0]
        cloudapp_info = enrich_with_cloudapp(upn, account_object_id, cloudapp_df, suspicious_ips)

        # Compute verdict
        score, verdict = compute_verdict(anomalies, isp_info, alert_info, phishing_info, cloudapp_info, auth_info)

        # Build summary row
        row = {
            # Identity
            "User": upn,
            "DisplayName": user_df["AccountDisplayName"].iloc[0] if len(user_df) > 0 else "",
            "Entity": get_entity(upn),
            "Department": profile_info["Department"],
            "JobTitle": profile_info["JobTitle"],
            "CurrentRiskLevel": profile_info["ProfileRiskLevel"],
            # Sign-in volume
            "TotalSignIns": baseline["TotalSignIns"],
            "ActiveDays": baseline["ActiveDays"],
            "FirstSignIn": baseline["FirstSignIn"],
            "LastSignIn": baseline["LastSignIn"],
            # Baseline
            "TrustedIPs": json.dumps(baseline["TrustedIPs"]),
            "TrustedIPCount": len(baseline["TrustedIPs"]),
            "TotalUniqueIPs": baseline["TotalUniqueIPs"],
            "TrustedCountries": json.dumps(baseline["AllCountries"]),
            "TrustedCities": json.dumps(baseline["TrustedCities"]),
            "TrustedDevices": json.dumps(baseline["TrustedDevices"]),
            "TrustedBrowsers": json.dumps(baseline["TrustedBrowsers"]),
            "TrustedOS": json.dumps(baseline["TrustedOS"]),
            "ISPList": json.dumps(isp_info["ISPList"]),
            "UniqueISPs": isp_info["UniqueISPs"],
            # Anomalies
            "UnknownIPSignIns": anomalies["UnknownIPSignIns"],
            "UnknownIPList": json.dumps(anomalies["UnknownIPList"]),
            "ForeignCountrySignIns": anomalies["ForeignCountrySignIns"],
            "ForeignCountryList": json.dumps(anomalies["ForeignCountryList"]),
            "NonBDSignIns": anomalies["NonBDSignIns"],
            "NonBDCountries": json.dumps(anomalies["NonBDCountries"]),
            "UnknownDeviceSignIns": anomalies["UnknownDeviceSignIns"],
            "UnknownBrowserSignIns": anomalies["UnknownBrowserSignIns"],
            "OffHoursSignIns": anomalies["OffHoursSignIns"],
            "HighRiskSignIns": anomalies["HighRiskSignIns"],
            "ManagedSignIns": baseline["ManagedSignIns"],
            "UnmanagedSignIns": baseline["UnmanagedSignIns"],
            "UnmanagedPct": anomalies["UnmanagedPct"],
            # Alerts
            "AlertCount": alert_info["AlertCount"],
            "FirstAlert": alert_info["FirstAlert"],
            "LastAlert": alert_info["LastAlert"],
            # Phishing
            "PhishingEmailsReceived": phishing_info["PhishingEmailsReceived"],
            "SuspiciousISPs": json.dumps(isp_info["SuspiciousISPs"]),
            # Data Breach
            "DataBreachEvents": cloudapp_info["DataBreachEvents"],
            "DataBreachActions": json.dumps(cloudapp_info["DataBreachActions"]),
            # Auth Status
            "MFAStatus": auth_info["MFAStatus"],
            "LastPasswordReset": auth_info["LastPasswordReset"],
            "AccountStatus": auth_info["AccountStatus"],
            "IsAdmin": auth_info["IsAdmin"],
            # Verdict
            "AnomalyScore": score,
            "Verdict": verdict,
        }
        results.append(row)

    # Create output DataFrame
    summary_df = pd.DataFrame(results)
    summary_df = summary_df.sort_values("AnomalyScore", ascending=False)

    # Export
    output_dir.mkdir(parents=True, exist_ok=True)

    # CSV
    csv_path = output_dir / "user_investigation_summary.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"\n📊 Summary CSV saved: {csv_path}")

    # Markdown report
    md_path = output_dir / "investigation_report.md"
    generate_markdown_report(summary_df, md_path)
    print(f"📄 Markdown report saved: {md_path}")

    # Print summary stats
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    verdicts = summary_df["Verdict"].value_counts()
    for v, c in verdicts.items():
        print(f"  {v}: {c} users")

    compromised = summary_df[summary_df["Verdict"].str.contains("Compromised")]
    if len(compromised) > 0:
        print(f"\n🔴 USERS REQUIRING IMMEDIATE ACTION:")
        for _, row in compromised.iterrows():
            print(f"  • {row['User']} (Score: {row['AnomalyScore']}, "
                  f"NonBD: {row['NonBDSignIns']}, "
                  f"SuspiciousISPs: {row['SuspiciousISPs']})")

    return summary_df


# ============================================================
# REPORT GENERATION
# ============================================================
def generate_markdown_report(df: pd.DataFrame, output_path: Path):
    """Generate a markdown investigation report."""
    lines = [
        "# 🔍 Investigation Report: Unfamiliar Sign-in — BD Users",
        "",
        f"> **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> **Users analyzed:** {len(df)}",
        f"> **Trusted threshold:** {TRUSTED_THRESHOLD*100}%",
        "",
        "---",
        "",
        "## Summary",
        "",
    ]

    # Verdict summary
    for verdict_type in ["🚨 CONFIRMED COMPROMISED (Data Breach)", "🔴 Likely Compromised", "🟠 Suspicious", "🟢 Likely Safe"]:
        count = len(df[df["Verdict"] == verdict_type])
        lines.append(f"- **{verdict_type}:** {count} users")
    lines.append("")

    # Per-user details
    lines.extend(["---", "", "## User Details", ""])

    for _, row in df.iterrows():
        lines.extend([
            f"### {row['Verdict']} — {row['DisplayName']}",
            "",
            f"- **Email:** `{row['User']}`",
            f"- **Entity:** {row['Entity']} | **Dept:** {row['Department']}",
            f"- **Current Risk:** {row['CurrentRiskLevel']}",
            f"- **Anomaly Score:** {row['AnomalyScore']}",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Sign-ins | {row['TotalSignIns']} ({row['ActiveDays']} active days) |",
            f"| Trusted IPs | {row['TrustedIPCount']} / {row['TotalUniqueIPs']} unique |",
            f"| Countries | {row['TrustedCountries']} |",
            f"| ISPs | {row['ISPList']} |",
            f"| Non-BD Sign-ins | **{row['NonBDSignIns']}** → {row['NonBDCountries']} |",
            f"| Unknown IP Sign-ins | {row['UnknownIPSignIns']} |",
            f"| Unknown Device Sign-ins | {row['UnknownDeviceSignIns']} |",
            f"| Off-hours Sign-ins | {row['OffHoursSignIns']} |",
            f"| High Risk Sign-ins | {row['HighRiskSignIns']} |",
            f"| Managed / Unmanaged | {row['ManagedSignIns']} / {row['UnmanagedSignIns']} ({row['UnmanagedPct']}%) |",
            f"| Alerts | {row['AlertCount']} (first: {row['FirstAlert']}, last: {row['LastAlert']}) |",
            f"| Phishing Emails | {row['PhishingEmailsReceived']} |",
            f"| Suspicious ISPs | {row['SuspiciousISPs']} |",
            f"| MFA Enrolled | {row['MFAStatus']} |",
            f"| Last Password Reset | {row['LastPasswordReset']} |",
            f"| Account Status | {row['AccountStatus']} |",
            f"| Admin Account | {'⚠️ YES' if row['IsAdmin'] else 'No'} |",
            f"| Data Breach Events | **{row['DataBreachEvents']}** → {row['DataBreachActions']} |",
            "",
            "---",
            "",
        ])

    output_path.write_text("\n".join(lines), encoding="utf-8")


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
