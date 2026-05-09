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
NORMAL_HOUR_THRESHOLD = 0.03  # 3% — hour with >= 3% sign-ins = Normal hour

# Danh sách user đã được SOC team xác minh thủ công là AN TOÀN.
# Verdict sẽ bị override thành "🟢 Verified Safe (SOC Override)"
# bất kể Anomaly Score là bao nhiêu. CloudAppEvents sẽ bị BỎ QUA hoàn toàn.
# Format: { "email": "Lý do xác minh — Ngày xác minh" }
# Fix: Post-Mortem #9 — Button Lin (CSC entity, công tác HK/VN/CN)
VERIFIED_SAFE_USERS = {
    "button_lin@crystal-csc.cn": "Đi công tác HK/VN/CN — SOC xác minh 09-May-2026",
}

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

# Baseline contamination threshold — if a user has more than this many TrustedCountries,
# the baseline may have been polluted by attacker-generated sign-ins.
# Fix: Audit Report v2 — Niaz Morshed had 20 TrustedCountries (likely hacker-generated)
BASELINE_COUNTRY_WARNING_THRESHOLD = 15

# Minimum sign-in count for reliable baseline (5% threshold).
# Users below this use a higher threshold (15%) to prevent baseline contamination.
# Fix: Output Audit v4 — sumon.mia (14 sign-ins, 100% hacker data → all countries become Trusted)
BASELINE_LOW_VOLUME_THRESHOLD = 50
BASELINE_LOW_VOLUME_TRUSTED_THRESHOLD = 0.15  # 15% for low-volume users

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

    # Determine effective threshold based on sign-in volume
    # Fix: Output Audit v4 — low-volume users (< 50 sign-ins) use higher threshold (15%)
    # to prevent baseline contamination by hacker-generated sign-ins
    effective_threshold = TRUSTED_THRESHOLD
    if baseline["TotalSignIns"] < BASELINE_LOW_VOLUME_THRESHOLD:
        effective_threshold = BASELINE_LOW_VOLUME_TRUSTED_THRESHOLD
        baseline["BaselineLowVolume"] = True
    else:
        baseline["BaselineLowVolume"] = False
    baseline["EffectiveThreshold"] = effective_threshold

    # Trusted IPs
    baseline["TrustedIPs"] = build_trusted_set(
        user_df["IPAddress"].dropna(), effective_threshold
    )
    baseline["TotalUniqueIPs"] = user_df["IPAddress"].nunique()

    # Trusted Countries
    baseline["TrustedCountries"] = build_trusted_set(
        user_df["Country"].dropna(), effective_threshold
    )
    baseline["AllCountries"] = sorted(user_df["Country"].dropna().unique().tolist())

    # Trusted Cities
    baseline["TrustedCities"] = build_trusted_set(
        user_df["City"].dropna(), effective_threshold
    )

    # Trusted Devices
    baseline["TrustedDevices"] = build_trusted_set(
        user_df["DeviceName"].dropna(), effective_threshold
    )
    baseline["TotalUniqueDevices"] = user_df["DeviceName"].nunique()

    # Trusted Browsers
    baseline["TrustedBrowsers"] = build_trusted_set(
        user_df["Browser"].dropna(), effective_threshold
    )

    # Trusted OS
    baseline["TrustedOS"] = build_trusted_set(
        user_df["OSPlatform"].dropna(), effective_threshold
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

    # ★ FIX: Filter out Microsoft infrastructure IPs before anomaly detection
    # These are Exchange Online backend IPs that appear as foreign sign-ins but are NOT user activity
    ms_infra_mask = user_df["IPAddress"].apply(is_microsoft_infra_ip)
    ms_infra_count = int(ms_infra_mask.sum())
    anomalies["MicrosoftInfraIPsFiltered"] = ms_infra_count
    user_df = user_df[~ms_infra_mask].copy()

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
# VERDICT SCORING
# ============================================================
def compute_verdict(anomalies: dict, isp_info: dict, alert_info: dict,
                    phishing_info: dict, cloudapp_info: dict,
                    auth_info: dict = None,
                    unfamiliar_info: dict = None,
                    user_upn: str = "") -> tuple:
    """Compute anomaly score and verdict for a user."""
    
    # Fix: Post-Mortem #9 — Verified Safe User Override
    # Nếu user đã được SOC xác minh an toàn → override verdict ngay lập tức
    if user_upn.lower() in {k.lower() for k in VERIFIED_SAFE_USERS}:
        reason = VERIFIED_SAFE_USERS.get(user_upn, "SOC Override")
        return 0, f"🟢 Verified Safe (SOC Override: {reason})"
    
    score = 0

    # Foreign country sign-ins: Penalize Hacker variety, not VPN variety
    # VPN Countries = +0 points (legitimate)
    # Hacker Countries = +30 points per distinct country
    # IMPORTANT: Dedup — if a country has BOTH hacker and VPN sign-ins, don't penalize it
    # (e.g., button_lin in CN: 16900 trusted device sign-ins + 10 telemetry drops)
    hacker_only_countries = set(anomalies.get("HackerBotnetCountries", [])) - set(anomalies.get("VPNCountries", []))
    score += len(hacker_only_countries) * 30

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

    # Alert count (Defender Alerts) — CONDITIONAL scoring (v4 fix)
    # Only apply alert penalty when user has COMPROMISE indicators
    # (foreign sign-ins, suspicious IPs, or HighRisk events).
    # Users with ONLY blocked attacks (0 foreign, 0 suspicious, 0 risk) get 0 alert score.
    # Fix: Output Audit v4 — Abdullah_Zubair (40 alerts, 0 foreign → was falsely Likely Compromised)
    has_compromise_indicators = (
        len(hacker_only_countries) > 0
        or len(anomalies.get("SuspiciousIPList", [])) > 0
        or anomalies.get("HighRiskSignIns", 0) > 0
        or anomalies.get("ForeignCountrySignIns", 0) > 0
    )
    if has_compromise_indicators:
        score += min(alert_info.get("AlertCount", 0), 5) * 5

    # Alert IP correlation bonus (Unfamiliar Sign-in Incidents — Q00)
    # +3 per suspicious IP that is ALSO an Entra ID alert IP, max 30 pts
    # Source: pillar_alignment.md — Gap 1 fix
    if unfamiliar_info:
        score += min(unfamiliar_info.get("AlertIPsMatchedCount", 0), 10) * 3

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

        # Detect anomalies
        anomalies = detect_user_anomalies(user_df, baseline)

        # Enrich with ISP, alerts, profile, phishing
        isp_info = enrich_with_isp(upn, isp_df)
        alert_info = enrich_with_alerts(upn, alert_df)
        profile_info = enrich_with_profile(upn, profile_df)
        phishing_info = enrich_with_phishing(upn, phish_df)
        auth_info = enrich_with_auth_status(upn, auth_df, user_df)
        
        # Fix: Post-Mortem #9 — Bỏ qua CloudAppEvents hoàn toàn cho Verified Safe Users
        is_verified_safe = upn.lower() in {k.lower() for k in VERIFIED_SAFE_USERS}
        
        # Get suspicious IPs for cloudapp filter (Unknown IP + Unknown Device)
        suspicious_ips = anomalies.get("SuspiciousIPList", [])
        account_object_id = user_df["AccountObjectId"].iloc[0]
        if is_verified_safe:
            cloudapp_info = {"DataBreachEvents": 0, "DataBreachActions": []}
        else:
            cloudapp_info = enrich_with_cloudapp(upn, account_object_id, cloudapp_df, suspicious_ips)

        # Enrich with Unfamiliar Sign-in alert IPs (Q00)
        unfamiliar_info = enrich_with_unfamiliar_signins(upn, unfamiliar_df, suspicious_ips)

        # Compute verdict
        score, verdict = compute_verdict(anomalies, isp_info, alert_info, phishing_info, cloudapp_info, auth_info, unfamiliar_info, user_upn=upn)

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
            "TrustedCountries": json.dumps(baseline["TrustedCountries"]),
            "AllCountries": json.dumps(baseline["AllCountries"]),
            "TrustedCountryCount": len(baseline["TrustedCountries"]),
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
            "SuspiciousIPs": json.dumps(anomalies.get("SuspiciousIPList", [])),
            # Data Breach
            "DataBreachEvents": cloudapp_info["DataBreachEvents"],
            "DataBreachActions": json.dumps(cloudapp_info["DataBreachActions"]),
            # Auth Status
            "MFAStatus": auth_info["MFAStatus"],
            "LastPasswordReset": auth_info["LastPasswordReset"],
            "AccountStatus": auth_info["AccountStatus"],
            "IsAdmin": auth_info["IsAdmin"],
            # Unfamiliar Sign-in Alert correlation (Q00 — Gap 1 fix)
            "AlertIPsMatched": json.dumps(unfamiliar_info["AlertIPsMatched"]),
            "AlertIPsMatchedCount": unfamiliar_info["AlertIPsMatchedCount"],
            "UserAlertCount_Q00": unfamiliar_info["UserAlertCount"],
            "FirstAlertTimestamp": unfamiliar_info["FirstAlertTimestamp"],
            "CrossUserAlertIPs": json.dumps(unfamiliar_info["CrossUserAlertIPs"]),
            # Microsoft Infra IPs filtered
            "MicrosoftInfraIPsFiltered": anomalies.get("MicrosoftInfraIPsFiltered", 0),
            # Baseline reliability (Output Audit v4 fix)
            "EffectiveThreshold": f"{baseline['EffectiveThreshold']*100:.0f}%",
            # Baseline contamination warning (v2 + v4 low-volume fix)
            "BaselineWarning": (
                f"⚠️ LOW VOLUME ({baseline['TotalSignIns']} sign-ins) — threshold raised to {baseline['EffectiveThreshold']*100:.0f}%"
                if baseline.get("BaselineLowVolume", False)
                else (
                    f"⚠️ {len(baseline['TrustedCountries'])} Trusted Countries — possible baseline contamination by attacker"
                    if len(baseline["TrustedCountries"]) > BASELINE_COUNTRY_WARNING_THRESHOLD
                    else ""
                )
            ),
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

    # Excel report (professional multi-sheet workbook)
    xlsx_path = output_dir / "investigation_report.xlsx"
    generate_excel_report(summary_df, xlsx_path, TRUSTED_THRESHOLD)
    print(f"\n📊 Excel report saved: {xlsx_path}")

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
            f"| Trusted Countries (≥5%) | {row['TrustedCountries']} |",
            f"| All Countries Seen | {row['AllCountries']} |",
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
            f"| MS Infra IPs Filtered | {row.get('MicrosoftInfraIPsFiltered', 0)} |",
            f"| Baseline Warning | {row.get('BaselineWarning', '')} |",
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
