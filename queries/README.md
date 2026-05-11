# KQL Investigation Queries — Hướng Dẫn Sử Dụng

> **Nguyên tắc thiết kế:** Tất cả queries chỉ phục vụ **1 mục đích duy nhất: lấy raw data**. Mọi phân tích nằm trong Python `analyze_signins.py`. Không có custom scoring hay verdict — chỉ hiển thị Microsoft Risk Signals raw data.

## Workflow

```
Bước 0: Chạy Query 0 (Master) → Xác định danh sách users + IPs cần investigate
Bước 1: Chạy các queries còn lại trong Advanced Hunting (security.microsoft.com)
Bước 2: Export CSV → Lưu vào folder incidents/data/export/
Bước 3: Merge signin_history_01..06.csv → signin_history.csv
Bước 4: Chạy Python script → Tự động phân tích + tạo report
```

## Kiến trúc

Tất cả queries sử dụng `let AffectedUsers` subquery — tự động lấy danh sách users bị trigger "Unfamiliar sign-in" từ `AlertEvidence`. **Không hardcode user/domain.**

```
Query 0 (AlertInfo + AlertEvidence) — Foundation
   └── Xác định ~54 affected users (ABL + CMBD + CETBD + CSC)
         │
         ├── [PIPELINE] Queries cho Python analyze_signins.py
         │     ├── Query 1A-1F: Sign-in history (EntraIdSignInEvents, split 5d/query)
         │     ├── Query 2:     ISP enrichment (IdentityLogonEvents)
         │     ├── Query 3:     Alert details — Unfamiliar sign-in (AlertEvidence)
         │     ├── Query 4:     User profiles (IdentityInfo)
         │     └── Query 5:     Phishing check (EmailEvents)
         │
         ├── [INVESTIGATION] Queries bổ sung — raw data cho deep-dive
         │     ├── Query 12:    Endpoint/malware alerts (non-identity alerts)
         │     └── Query 13:    Inbox rules changes (CloudAppEvents + JSON parse)
         │
         ├── [SUPPORT] Queries hỗ trợ
         │     ├── Query 6:     CloudApp ISP backup (dùng nếu Q02 thiếu data)
         │     ├── Query 9:     CloudApp events bulk (context cho deep-dive)
         │     └── Query 14:    Remediation history (audit/compliance)
         │
         └── [ARCHIVED] queries/archive/ — Logic đã migrate hoặc merged
               ├── Query 7:     VPN vs Hacker (archived)
               ├── Query 8:     Post-Breach single user (archived)
               ├── Query 10:    Auth status (archived — data unreliable)
               └── Query 11:    AiTM session data (merged vào Q01A-F)
```

## Danh sách queries

### Pipeline Queries (bắt buộc cho Python)

| # | File | Export CSV as | Table | Mô tả |
|---|------|---------------|-------|--------|
| **0** | `00_unfamiliar_signin_incidents.kql` | `unfamiliar_signin_incidents.csv` | `AlertInfo` + `AlertEvidence` | ⭐ Master — tất cả incidents + users + IPs |
| 1A | `01a_signin_history.kql` | `signin_history_01.csv` | `EntraIdSignInEvents` | Sign-in — ngày 1-5 (ago 30d→25d) |
| 1B | `01b_signin_history.kql` | `signin_history_02.csv` | `EntraIdSignInEvents` | Sign-in — ngày 6-10 (ago 25d→20d) |
| 1C | `01c_signin_history.kql` | `signin_history_03.csv` | `EntraIdSignInEvents` | Sign-in — ngày 11-15 (ago 20d→15d) |
| 1D | `01d_signin_history.kql` | `signin_history_04.csv` | `EntraIdSignInEvents` | Sign-in — ngày 16-20 (ago 15d→10d) |
| 1E | `01e_signin_history.kql` | `signin_history_05.csv` | `EntraIdSignInEvents` | Sign-in — ngày 21-25 (ago 10d→5d) |
| 1F | `01f_signin_history.kql` | `signin_history_06.csv` | `EntraIdSignInEvents` | Sign-in — ngày 26-30 (ago 5d→now) |
| 2 | `02_isp_data.kql` | `isp_data.csv` | `IdentityLogonEvents` | ISP enrichment |
| 3 | `03_alert_data.kql` | `alert_data.csv` | `AlertEvidence` | Unfamiliar sign-in alert evidence |
| 4 | `04_user_profiles.kql` | `user_profiles.csv` | `IdentityInfo` | User identity info |
| 5 | `05_phishing_check.kql` | `phishing_emails.csv` | `EmailEvents` | Phishing emails to affected users |

### Investigation Queries (raw data cho deep-dive)

| # | File | Export CSV as | Table | Mô tả |
|---|------|---------------|-------|--------|
| 12 | `12_infostealer_endpoint_investigation.kql` | `endpoint_alerts.csv` | `AlertEvidence` + `AlertInfo` | Tất cả alerts non-identity (malware, infostealer, credential theft) |
| 13 | `13_hidden_inbox_rules_investigation.kql` | `inbox_rules.csv` | `CloudAppEvents` | Inbox rule changes + JSON parsed RuleConfig |

### Support & Backup Queries

| # | File | Export CSV as | Table | Mô tả |
|---|------|---------------|-------|--------|
| 6 | `06_cloudapp_isp.kql` | `cloudapp_isp.csv` | `CloudAppEvents` | Backup ISP data (dùng nếu Q02 thiếu) |
| 9 | `09_cloudapp_events_bulk.kql` | `cloudapp_events.csv` | `CloudAppEvents` | Context data cho deep-dive |
| 14 | `14_remediation_history.kql` | `remediation_history.csv` | `CloudAppEvents` | Password reset, session revoke history, MFA changes |

### Archived Queries (`queries/archive/`)

| File | Lý do archive |
|------|---------------|
| `07_vpn_vs_hacker_investigation.kql` | Logic đã migrate vào Python |
| `08_post_breach_investigation.kql` | Hardcode 1 user, trùng lặp Q09 |
| `10_auth_status.kql` | Data unreliable (MFA/Account status trống), network team to verify |
| `11_aitm_token_theft_investigation.kql` | Data merged vào Q01A-F |

## Cách chạy

1. Vào `https://security.microsoft.com` → **Hunting** → **Advanced Hunting**
2. Mở từng file `.kql`, copy toàn bộ nội dung vào query editor
3. Nhấn **Run query**
4. Nhấn **Export** → **CSV**
5. Lưu file CSV với tên đúng theo bảng trên vào `incidents/data/export/`

## Chạy Python phân tích

```bash
cd scripts
pip install pandas numpy openpyxl
python analyze_signins.py --data-dir ../incidents/data/export --output-dir ../incidents/analysis
```

### Tham số tùy chỉnh

```bash
# Đổi ngưỡng trusted (mặc định 5%)
python analyze_signins.py --threshold 0.10

# Chỉ định thư mục khác
python analyze_signins.py --data-dir /path/to/csvs --output-dir /path/to/output
```

## Output

| File | Mô tả |
|------|--------|
| `incidents/analysis/investigation_report.xlsx` | ⭐ Excel report 4-sheet (auto-generated) |

## Lưu ý

- **Query 0 phải chạy TRƯỚC** — các query khác dùng cùng `let AffectedUsers` subquery
- **Query 1 split 6 phần** vì KQL limit 100K rows — mỗi query 5 ngày, export 6 CSV rồi merge thành `signin_history.csv`
- File bắt buộc: `unfamiliar_signin_incidents.csv` (Q00) + `signin_history.csv` (Q01). Các file còn lại là optional enrichment
- **Không có custom scoring hay verdict** — pipeline chỉ hiển thị raw Microsoft Risk Signals (`RiskLevelDuringSignIn`)
- Analyst tự quyết định actions dựa trên data trong report
