# KQL Investigation Queries — Hướng Dẫn Sử Dụng

## Workflow

```
Bước 0: Chạy Query 0 (Master) → Xác định danh sách users + IPs cần investigate
Bước 1: Chạy 6 queries còn lại trong Advanced Hunting (security.microsoft.com)
Bước 2: Export CSV → Lưu vào folder incidents/data/export/
Bước 3: Chạy Python script → Tự động phân tích + tạo report
```

## Kiến trúc

Tất cả queries 1-6 đều sử dụng `let AffectedUsers` subquery — tự động lấy danh sách users bị trigger "Unfamiliar sign-in" từ `AlertEvidence`. **Không hardcode domain.**

```
Query 0 (AlertInfo + AlertEvidence)
   └── Xác định 54 affected users
         ├── Query 1: Sign-in history (EntraIdSignInEvents)
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
| 1 | `01_signin_history.kql` | `signin_history.csv` | Sign-in history — all affected users |
| 2 | `02_isp_data.kql` | `isp_data.csv` | ISP enrichment (IdentityLogonEvents) |
| 3 | `03_alert_data.kql` | `alert_data.csv` | Unfamiliar sign-in alert evidence |
| 4 | `04_user_profiles.kql` | `user_profiles.csv` | User identity info |
| 5 | `05_phishing_check.kql` | `phishing_emails.csv` | Phishing emails to affected users |
| 6 | `06_cloudapp_isp.kql` | `cloudapp_isp.csv` | Backup ISP data (CloudAppEvents) |

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
- Nếu Query 1 vượt 10K rows, thêm filter: `| where LogonType == "Interactive"`
- Query 6 (CloudApp ISP) là **backup** — chỉ cần chạy nếu Query 2 không có đủ data
- File bắt buộc: `unfamiliar_signin_incidents.csv` (0) + `signin_history.csv` (1). Các file còn lại là optional enrichment
