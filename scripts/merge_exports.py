"""
Merge & Rename exported CSV files for the Python analysis pipeline.

Usage:
    python merge_exports.py --export-dir ../incidents/data/export

Actions:
1. Merge signin_history_01..06.csv (or 01a..01f) → signin_history.csv
2. Rename query-numbered files to pipeline names expected by analyze_signins.py:
   - 02_isp_data.csv → isp_data.csv
   - 03_alert_data.csv → alert_data.csv
   - 04_user_profiles.csv → user_profiles.csv
   - 05_phishing_check.csv → phishing_emails.csv
   - 09_cloudapp_events_bulk.csv → cloudapp_events.csv
   - 10_auth_status.csv → auth_status.csv
   - 00_unfamiliar_signin_incidents.csv → unfamiliar_signin_incidents.csv (if present)
"""

import pandas as pd
from pathlib import Path
import argparse
import sys

# Mapping: source filename pattern → target filename for Python pipeline
RENAME_MAP = {
    "02_isp_data.csv": "isp_data.csv",
    "03_alert_data.csv": "alert_data.csv",
    "04_user_profiles.csv": "user_profiles.csv",
    "05_phishing_check.csv": "phishing_emails.csv",
    "09_cloudapp_events_bulk.csv": "cloudapp_events.csv",
    "10_auth_status.csv": "auth_status.csv",
    "00_unfamiliar_signin_incidents.csv": "unfamiliar_signin_incidents.csv",
}


def merge_signin_history(export_dir: Path) -> None:
    """Merge split signin history CSVs into one file."""
    # Find all signin history parts (both naming conventions)
    parts = sorted(export_dir.glob("01*_signin_history*.csv"))
    
    if not parts:
        print("  ⚠ No signin history files found (01*_signin_history*.csv)")
        return
    
    print(f"  📋 Found {len(parts)} signin history parts:")
    dfs = []
    for p in parts:
        df = pd.read_csv(p, low_memory=False)
        print(f"     {p.name}: {len(df)} rows")
        dfs.append(df)
    
    merged = pd.concat(dfs, ignore_index=True)
    
    # Deduplicate (in case of overlapping time ranges)
    before_dedup = len(merged)
    # Use key columns for dedup — Timestamp + AccountUpn + IPAddress + SessionId
    dedup_cols = ["Timestamp", "AccountUpn", "IPAddress"]
    if "SessionId" in merged.columns:
        dedup_cols.append("SessionId")
    merged = merged.drop_duplicates(subset=dedup_cols, keep="first")
    after_dedup = len(merged)
    
    output_path = export_dir / "signin_history.csv"
    merged.to_csv(output_path, index=False)
    
    print(f"  ✅ Merged → signin_history.csv: {after_dedup} rows")
    if before_dedup != after_dedup:
        print(f"     (removed {before_dedup - after_dedup} duplicate rows)")


def rename_files(export_dir: Path) -> None:
    """Rename query-numbered files to pipeline names."""
    for src_name, dst_name in RENAME_MAP.items():
        src = export_dir / src_name
        dst = export_dir / dst_name
        
        if src.exists():
            if src_name == dst_name:
                print(f"  ✓ {src_name} (already correct name)")
                continue
            # Copy instead of rename so originals are preserved
            import shutil
            shutil.copy2(src, dst)
            print(f"  ✓ {src_name} → {dst_name}")
        else:
            # Check if target already exists (already renamed)
            if dst.exists():
                print(f"  ✓ {dst_name} (already exists)")
            else:
                print(f"  ⚠ {src_name} not found")


def main():
    parser = argparse.ArgumentParser(description="Merge & rename exported CSV files")
    parser.add_argument(
        "--export-dir",
        type=str,
        default="../incidents/data/export",
        help="Directory containing exported CSV files"
    )
    args = parser.parse_args()
    
    export_dir = Path(args.export_dir)
    if not export_dir.exists():
        print(f"ERROR: Export directory not found: {export_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("Merge & Rename Exported CSV Files")
    print("=" * 60)
    
    print("\n📂 Step 1: Merge signin history parts...")
    merge_signin_history(export_dir)
    
    print("\n📂 Step 2: Rename files for Python pipeline...")
    rename_files(export_dir)
    
    print("\n✅ Done! Ready to run analyze_signins.py")
    print(f"   python analyze_signins.py --data-dir {export_dir}")


if __name__ == "__main__":
    main()
