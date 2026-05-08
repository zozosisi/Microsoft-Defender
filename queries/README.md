# KQL Investigation Queries — Hướng Dẫn Sử Dụng

## Workflow

```
Bước 0: Chạy Query 0 (Master) → Xác định danh sách users + IPs cần investigate
Bước 1: Chạy 8 queries còn lại trong Advanced Hunting (security.microsoft.com)
Bước 2: Export CSV → Lưu vào folder incidents/data/export/
Bước 3: Chạy Python script → Tự động phân tích + tạo report
```

## Kiến trúc

Tất cả queries 1-6 đều sử dụng `let AffectedUsers` subquery — tự động lấy danh sách users bị trigger "Unfamiliar sign-in" từ `AlertEvidence`. **Không hardcode domain.**

```
Query 0 (AlertInfo + AlertEvidence)
   └── Xác định ~54 affected users
         ├── Query 1A/1B/1C: Sign-in history (split 10 ngày/query, limit 100K rows)
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
| 1A | `01a_signin_history.kql` | `signin_history_01.csv` | Sign-in history — ngày 1-10 (ago 30d→20d) |
| 1B | `01b_signin_history.kql` | `signin_history_02.csv` | Sign-in history — ngày 11-20 (ago 20d→10d) |
| 1C | `01c_signin_history.kql` | `signin_history_03.csv` | Sign-in history — ngày 21-30 (ago 10d→now) |
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
- **Query 1 split 3 phần** vì KQL limit 100K rows — export 3 CSV rồi merge
- Query 6 (CloudApp ISP) là **backup** — chỉ cần chạy nếu Query 2 không có đủ data
- File bắt buộc: `unfamiliar_signin_incidents.csv` (0) + `signin_history_*.csv` (1A-1C). Các file còn lại là optional enrichment
