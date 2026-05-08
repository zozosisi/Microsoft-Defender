# Hệ Thống Phân Tích Sự Cố Microsoft Defender: Business Logic Reference

> **Cập nhật lần cuối:** 08-May-2026
> **Mục đích:** Tài liệu này mô tả chi tiết nghiệp vụ và logic tính toán đằng sau công cụ `analyze_signins.py` để giúp đội ngũ SOC/IT hiểu rõ cách hệ thống đưa ra quyết định cảnh báo.

---

## 1. Nguồn Dữ Liệu Đầu Vào (Data Ingestion)
Hệ thống kết hợp dữ liệu từ bộ KQL truy vấn (từ 01 đến 09) để tạo góc nhìn 360 độ về một người dùng, đọc vào qua các file CSV:
1. **`signin_history.csv`** (Query 01A-01F): Lịch sử đăng nhập từ Entra ID (`AADSignInEventsBeta`).
2. **`isp_data.csv`** (Query 02): Dữ liệu nhà mạng (`IdentityLogonEvents`).
3. **`alert_data.csv`** (Query 03): Các cảnh báo bảo mật (`AlertEvidence`).
4. **`user_profiles.csv`** (Query 04): Thông tin phòng ban, chức vụ (`IdentityInfo`).
5. **`phishing_emails.csv`** (Query 05): Lịch sử nhận email lừa đảo (`EmailEvents`).
6. **`cloudapp_events.csv`** (Query 09): Dữ liệu hành vi thao tác file/ứng dụng (`CloudAppEvents`) dùng để phát hiện Data Breach.

*(Lưu ý: Query 07 và 08 là các công cụ KQL hỗ trợ điều tra thủ công (Manual Investigation) độc lập, sau khi test thành công thì logic đã được tích hợp thẳng vào Python).*

---

## 2. Xây Dựng Baseline (Hành Vi Thói Quen)
Thay vì sử dụng quy tắc tĩnh (static rules), hệ thống tự động học thói quen của từng user trong 30 ngày qua bằng cách thiết lập **Trusted Baseline** với ngưỡng `10%` (TRUSTED_THRESHOLD).

Một thuộc tính (IP, Quốc gia, Thiết bị, Trình duyệt) được coi là **"Đáng tin cậy" (Trusted)** nếu nó chiếm ít nhất 10% tổng số lần đăng nhập của người dùng đó.
*Ví dụ: Nếu user có 100 lần đăng nhập, trong đó 90 lần bằng máy `CMA-PC438` và 10 lần bằng `iPhone`, thì cả 2 thiết bị này đều được coi là Trusted.*

---

## 3. Logic Nhận Diện Bất Thường (Anomaly Detection)

Hệ thống so sánh các lần đăng nhập với Baseline để tìm ra sự khác biệt:

### A. Phân biệt VPN hợp lệ và Hacker (Botnet)
Đây là logic cốt lõi để loại bỏ False Positives cho các nhân viên đi công tác hoặc làm việc ở chi nhánh nước ngoài:
*   **VPN hợp lệ:** Đăng nhập từ IP nước ngoài (Non-BD) **NHƯNG** thiết bị sử dụng là **Trusted Device** (Tên máy tính quen thuộc).
*   **Hacker Botnet:** Đăng nhập từ IP nước ngoài (Non-BD) **VÀ** thiết bị là thiết bị lạ (không có trong Trusted Devices) hoặc không có tên thiết bị (Unknown Device).

### B. Hành vi Xâm nhập (Post-Breach / Data Breach)
Hệ thống quét `CloudAppEvents` bằng cách đối chiếu với các địa chỉ IP của Hacker. Nếu phát hiện Hacker có bất kỳ hành động nào dưới đây, mức độ nghiêm trọng sẽ tăng lên Tối Đa:
- Đánh cắp: `FileDownloaded`
- Phá hoại: `FileRecycled`, `FolderRecycled`
- Đọc trộm: `MailItemsAccessed`, `eDiscoverySearch`, `FileAccessed`
- Phát tán mã độc: `MessageSent` (qua Teams)
- Ẩn giấu vết: `New-InboxRule`, `Set-InboxRule`

---

## 4. Hệ Thống Tính Điểm (Scoring Matrix)

Điểm Anomaly Score được tính cộng dồn dựa trên các rủi ro sau:

| Rủi Ro | Công thức phạt (Penalty) | Max Cap | Ý Nghĩa |
|--------|---------------------------|---------|---------|
| **Data Breach Actions** | **+1000 điểm** (Ngay lập tức) | - | Hacker đã chạm vào dữ liệu (Xóa/Tải file) |
| **Hacker Botnet Countries** | **+30 điểm** / mỗi quốc gia lạ | - | Hacker đang dùng Residential Proxy để ẩn danh |
| **VPN Countries** | **+0 điểm** | - | Người dùng hợp lệ dùng VPN công ty |
| **Suspicious ISPs** | **+15 điểm** / mỗi ISP độc hại | - | Đăng nhập từ Hosting, VPS, mạng ẩn danh |
| **Unknown IPs** | **+2 điểm** / mỗi IP lạ | Max 30đ | Hành vi Password Spraying (nhảy IP liên tục) |
| **Entra ID Risk Events** | **+5 điểm** / sự kiện | - | Microsoft đã gắn cờ High Risk cho session này |
| **Defender Alerts** | **+5 điểm** / cảnh báo | Max 25đ | Số lượng Alert do Defender tự động sinh ra |
| **Phishing Target** | **+5 điểm** / email lừa đảo | - | User là mục tiêu của chiến dịch Phishing |
| **Off-Hours Sign-ins** | **+0.5 điểm** / lần đăng nhập | Max 10đ | Đăng nhập vào ban đêm (ngoài giờ hành chính) |
| **Unmanaged Devices** | **+5 điểm** | Tĩnh | Nếu >80% lượt đăng nhập từ thiết bị cá nhân |

---

## 5. Phân Loại Kết Quả (Verdict Classification)

Dựa vào tổng điểm, hệ thống gán 1 trong 4 nhãn sau để phân cấp ưu tiên xử lý:

1. **🚨 CONFIRMED COMPROMISED (Data Breach):** Bất kể điểm số là bao nhiêu, chỉ cần có hành vi Data Breach (hacker chạm vào dữ liệu), user bị đánh dấu đỏ khẩn cấp. Phải Block ngay lập tức.
2. **🔴 Likely Compromised (Score >= 30):** Rủi ro cực cao, có dấu hiệu Impossible Travel, dùng Botnet. Cần Investigate và Block.
3. **🟠 Suspicious (15 <= Score < 30):** Có hành vi lạ, dùng IP/ISP rủi ro nhưng chưa rõ ràng là hacker. Cần liên hệ người dùng để xác nhận (MFA re-registration).
4. **🟢 Likely Safe (Score < 15):** Điểm số thấp, hành vi chủ yếu là False Positive (ví dụ: nhân sự đi công tác hoặc dùng VPN an toàn). Không cần xử lý.
