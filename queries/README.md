# KQL Investigation Queries — Hướng Dẫn Sử Dụng

## Workflow

```
Bước 1: Chạy 8 queries trong Advanced Hunting (security.microsoft.com)
Bước 2: Export CSV → Lưu vào folder incidents/data/exports/
Bước 3: Chạy Python script → Tự động phân tích + tạo report
```

## Danh sách queries

| # | File | Export CSV as | Mô tả |
|---|------|---------------|--------|
| 1A | `01_signin_history_ABL.kql` | `signin_abl.csv` | Sign-in history — ABL users |
| 1B | `01_signin_history_CMBD.kql` | `signin_cmbd.csv` | Sign-in history — CMBD users |
| 1C | `01_signin_history_CETBD.kql` | `signin_cetbd.csv` | Sign-in history — CETBD users |
| 2 | `02_isp_data.kql` | `isp_data.csv` | ISP enrichment (IdentityLogonEvents) |
| 3 | `03_alert_data.kql` | `alert_data.csv` | Unfamiliar sign-in alerts |
| 4 | `04_user_profiles.kql` | `user_profiles.csv` | User identity info |
| 5 | `05_phishing_check.kql` | `phishing_emails.csv` | Phishing emails to BD users |
| 6 | `06_cloudapp_isp.kql` | `cloudapp_isp.csv` | Backup ISP data (CloudAppEvents) |

## Cách chạy

1. Vào `https://security.microsoft.com` → **Hunting** → **Advanced Hunting**
2. Mở từng file `.kql`, copy toàn bộ nội dung vào query editor
3. Nhấn **Run query**
4. Nhấn **Export** → **CSV**
5. Lưu file CSV với tên đúng theo bảng trên vào `incidents/data/exports/`

## Chạy Python phân tích

```bash
cd scripts
pip install pandas numpy
python analyze_signins.py --data-dir ../incidents/data/exports --output-dir ../incidents/analysis
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

- Query 1A-1C tách theo domain vì **KQL giới hạn 10,000 rows** per query
- Nếu query vẫn bị truncate (> 10K rows), thêm filter: `| where LogonType == "Interactive"` để chỉ lấy interactive sign-ins
- Query 6 (CloudApp ISP) là **backup** — chỉ cần chạy nếu Query 2 không có đủ data
- File bắt buộc: `signin_*.csv` (1A-1C). Các file còn lại là optional enrichment
