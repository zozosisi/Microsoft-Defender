# KQL Investigation Queries — Hướng Dẫn Sử Dụng

## Workflow

```
Bước 0: Chạy Query 0 (Master) → Xác định danh sách users + IPs cần investigate
Bước 1: Chạy 11 queries còn lại trong Advanced Hunting (security.microsoft.com)
Bước 2: Export CSV → Lưu vào folder incidents/data/export/
Bước 3: Chạy Python script → Tự động phân tích + tạo report
```

## Kiến trúc

Tất cả queries 1-6 đều sử dụng `let AffectedUsers` subquery — tự động lấy danh sách users bị trigger "Unfamiliar sign-in" từ `AlertEvidence`. **Không hardcode domain.**

```
Query 0 (AlertInfo + AlertEvidence)
   └── Xác định ~54 affected users
         ├── Query 1A-1F: Sign-in history (split 5 ngày/query, limit 100K rows)
         ├── Query 2: ISP enrichment (IdentityLogonEvents)
         ├── Query 3: Alert details (AlertEvidence)
         ├── Query 4: User profiles (IdentityInfo)
         ├── Query 5: Phishing check (EmailEvents)
         └── Query 6: CloudApp ISP backup (CloudAppEvents)
```

## Danh sách queries

| # | File | Export CSV as | Mô tả |
|---|------|---------------|--------|
| **0** | **`00_unfamiliar_signin_incidents.kql`** | **`unfamiliar_signin_incidents.csv`** | **⭐ Master — tất cả incidents + users + IPs** |
| 1A | `01a_signin_history.kql` | `signin_history_01.csv` | Sign-in — ngày 1-5 (ago 30d→25d) |
| 1B | `01b_signin_history.kql` | `signin_history_02.csv` | Sign-in — ngày 6-10 (ago 25d→20d) |
| 1C | `01c_signin_history.kql` | `signin_history_03.csv` | Sign-in — ngày 11-15 (ago 20d→15d) |
| 1D | `01d_signin_history.kql` | `signin_history_04.csv` | Sign-in — ngày 16-20 (ago 15d→10d) |
| 1E | `01e_signin_history.kql` | `signin_history_05.csv` | Sign-in — ngày 21-25 (ago 10d→5d) |
| 1F | `01f_signin_history.kql` | `signin_history_06.csv` | Sign-in — ngày 26-30 (ago 5d→now) |
| 2 | `02_isp_data.kql` | `isp_data.csv` | ISP enrichment (IdentityLogonEvents) |
| 3 | `03_alert_data.kql` | `alert_data.csv` | Unfamiliar sign-in alert evidence |
| 4 | `04_user_profiles.kql` | `user_profiles.csv` | User identity info |
| 5 | `05_phishing_check.kql` | `phishing_emails.csv` | Phishing emails to affected users |
| 6 | `06_cloudapp_isp.kql` | `cloudapp_isp.csv` | Backup ISP data (CloudAppEvents) |
| 7 | `07_vpn_vs_hacker_investigation.kql` | *(manual)* | Phân biệt VPN vs Hacker theo DeviceStatus (dùng EntraIdSignInEvents) |
| 08 | `08_post_breach_investigation.kql` | Hỗ trợ điều tra tay để săn lùng các hành động xâm nhập dữ liệu. | `CloudAppEvents` |
| 09 | `09_cloudapp_events_bulk.kql` | Export hàng loạt dữ liệu hành vi ứng dụng cho toàn bộ tổ chức (dùng cho pipeline). | `CloudAppEvents` |
| 10 | `10_auth_status.kql` | Export thông tin MFA, trạng thái tài khoản, và lịch sử đổi mật khẩu. | `IdentityInfo`, `IdentityAccountInfo` |
| 11 | `11_aitm_token_theft_investigation.kql` | **Chốt hạ:** Phát hiện Hacker trộm Cookie Session (Pass-the-Cookie/AiTM). Phân biệt VPN vs AiTM bằng DeviceList + TrustedCountries baseline. **v2:** Filter Microsoft infra IPs, thêm 🟡 Review Required tier. | `EntraIdSignInEvents` |
| 12 | `12_infostealer_endpoint_investigation.kql` | **Chốt hạ:** Quét xem máy tính của user có bị nhiễm mã độc trộm mật khẩu (Redline, Raccoon) hay không. | `AlertEvidence`, `AlertInfo` |
| 13 | `13_hidden_inbox_rules_investigation.kql` | **Chốt hạ:** Phát hiện Hacker cài cắm các Rule ẩn để forward trộm email ra bên ngoài. | `CloudAppEvents` |

## Cách chạy

1. Vào `https://security.microsoft.com` → **Hunting** → **Advanced Hunting**
2. Mở từng file `.kql`, copy toàn bộ nội dung vào query editor
3. Nhấn **Run query**
4. Nhấn **Export** → **CSV**
5. Lưu file CSV với tên đúng theo bảng trên vào `incidents/data/export/`

## Chạy Python phân tích

```bash
cd scripts
pip install pandas numpy
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
| `incidents/analysis/user_investigation_summary.csv` | Bảng tổng hợp — mỗi row = 1 user |
| `incidents/analysis/investigation_report.md` | Báo cáo markdown chi tiết |

## Lưu ý

- **Query 0 phải chạy TRƯỚC** — các query 1-6 dùng cùng `let AffectedUsers` subquery
- **Query 1 split 6 phần** vì KQL limit 100K rows — mỗi query 5 ngày, export 6 CSV rồi merge
- Query 6 (CloudApp ISP) là **backup** — chỉ cần chạy nếu Query 2 không có đủ data
- Query 7 & 8 là **công cụ điều tra thủ công** (manual) — cần thay `targetUser` trước khi chạy
- **Query 9 có thể hit giới hạn 10K rows** — nếu bị truncate, chia theo thời gian (15d + 15d)
- Query 10 có thể trả `EnrolledMfas` trống nếu Defender for Identity chưa sync — Python có fallback
- **Query 11 (v2):** Filter Microsoft infrastructure IPs (`2603:10x6:`, `40.107.`, `52.100.`) + TrustedCountries baseline awareness (4-tier verdict: 🚨→🟡→🟢→🟠)
- File bắt buộc: `unfamiliar_signin_incidents.csv` (0) + `signin_history_*.csv` (1A-1F). Các file còn lại là optional enrichment
