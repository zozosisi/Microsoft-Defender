# Hệ Thống Phân Tích Sự Cố Microsoft Defender: Business Logic Reference

> **Cập nhật lần cuối:** 11-May-2026 (v5.0 — Raw Data Only architecture, Q07/Q08 archived, Q11-Q13 rewritten)
> **Mục đích:** Tài liệu này mô tả chi tiết nghiệp vụ và logic tính toán đằng sau công cụ `analyze_signins.py` để giúp đội ngũ SOC/IT hiểu rõ cách hệ thống đưa ra quyết định cảnh báo.

---

## 1. Nguồn Dữ Liệu Đầu Vào (Data Ingestion)

> **Nguyên tắc thiết kế (v5.0):** Tất cả KQL queries chỉ phục vụ **1 mục đích duy nhất: lấy raw data**. Mọi logic phân tích (baseline building, scoring, verdict) nằm **hoàn toàn trong Python** `analyze_signins.py`.

Hệ thống kết hợp dữ liệu từ bộ KQL truy vấn để tạo góc nhìn 360 độ về một người dùng, đọc vào qua các file CSV:

### Pipeline chính (bắt buộc)
1. **`unfamiliar_signin_incidents.csv`** (Query 00): ⭐ Master query — toàn bộ incidents + users + IPs (`AlertInfo` + `AlertEvidence`). Bao gồm 4 entity: ABL, CMBD, CETBD, CSC.
2. **`signin_history.csv`** (Query 01A-01F): Lịch sử đăng nhập từ Entra ID (`EntraIdSignInEvents`). Split 6 queries × 5 ngày do limit 100K rows.
3. **`isp_data.csv`** (Query 02): Dữ liệu nhà mạng (`IdentityLogonEvents`).
4. **`alert_data.csv`** (Query 03): Các cảnh báo "Unfamiliar sign-in" (`AlertEvidence`).
5. **`user_profiles.csv`** (Query 04): Thông tin phòng ban, chức vụ (`IdentityInfo`).
6. **`phishing_emails.csv`** (Query 05): Lịch sử nhận email lừa đảo (`EmailEvents`).
7. **`cloudapp_events.csv`** (Query 09): Dữ liệu hành vi thao tác file/ứng dụng (`CloudAppEvents`) dùng để phát hiện Data Breach.
8. **`auth_status.csv`** (Query 10): Trạng thái đăng ký MFA và thời gian đổi mật khẩu (`IdentityAccountInfo`).
   - *Cơ chế Fallback (Dự phòng):* Nếu dữ liệu `IdentityAccountInfo` trống (do tenant chưa tích hợp đầy đủ UEBA/Defender for Identity), hệ thống sẽ tự động quét chéo bảng `signin_history.csv` để tìm cột `AuthenticationRequirement`. Nếu có lịch sử yêu cầu MFA, user sẽ được đánh dấu là "MFA Enforced (Detected from Sign-ins)".

### Investigation queries (raw data cho deep-dive)
9. **`aitm_session_data.csv`** (Query 11): Raw session data kèm `AuthenticationProcessingDetails` cho AiTM detection.
10. **`endpoint_alerts.csv`** (Query 12): Tất cả alerts non-identity (malware, infostealer, credential theft).
11. **`inbox_rules.csv`** (Query 13): Inbox rule changes kèm parsed JSON `RuleConfig`.

### Archived queries (`queries/archive/`)
- **Query 07** (VPN vs Hacker): Logic đã migrate 100% vào `detect_user_anomalies()`. Archived.
- **Query 08** (Post-Breach single user): Hardcode 1 user, trùng lặp Q09 + `enrich_with_cloudapp()`. Archived.

> **⚠️ Thay đổi quan trọng (v5.0 — 11-May-2026):**
> - **Q00:** Thêm domain `crystal-csc.cn` vào filter (trước đó thiếu CSC entity).
> - **Q07 & Q08:** Archived vào `queries/archive/` — logic đã 100% trong Python.
> - **Q11:** Rewrite thành raw data export (bỏ hardcode users, bỏ baseline building + verdict trong KQL). Python sẽ tự detect AiTM.
> - **Q12:** Rewrite thành raw data export (bỏ hardcode users, bỏ keyword filter). Export tất cả non-identity alerts.
> - **Q13:** Rewrite thành raw data export (bỏ hardcode users, bỏ verdict logic). Giữ JSON parsing (`RawEventData`) trong KQL vì hiệu quả hơn Python.

---

## 2. Xây Dựng Baseline (Hành Vi Thói Quen)
Thay vì sử dụng quy tắc tĩnh (static rules), hệ thống tự động học thói quen của từng user trong 30 ngày qua bằng cách thiết lập **Trusted Baseline** với ngưỡng `5%` (TRUSTED_THRESHOLD).

Một thuộc tính (IP, Quốc gia, Thiết bị, Trình duyệt) được coi là **"Đáng tin cậy" (Trusted)** nếu nó chiếm ít nhất 5% tổng số lần đăng nhập của người dùng đó.
*Ví dụ: Nếu user có 100 lần đăng nhập, trong đó 90 lần bằng máy `CMA-PC438` và 5 lần bằng `iPhone`, thì cả 2 thiết bị này đều được coi là Trusted.*

> **⚠️ Cảnh báo Baseline Contamination (v2 — 08-May-2026):**
> Nếu Hacker đã tạo đủ nhiều sign-in từ các quốc gia khác nhau (≥ 5% mỗi nước), các quốc gia đó sẽ bị tính nhầm thành "TrustedCountries". Hệ thống sẽ tự động **cảnh báo** khi một user có hơn 15 TrustedCountries — đây là dấu hiệu baseline bị ô nhiễm bởi attacker.
> *Nguồn: Audit Report KQL 11 — case Niaz Morshed (20 TrustedCountries, bao gồm HK/CN do hacker tạo).*

> **🆕 Dynamic Baseline Threshold (v4.1 — 09-May-2026):**
> Users có **< 50 sign-ins** tự động dùng **threshold 15%** thay vì 5%. Ngăn baseline contamination cho low-volume users khi hacker sign-ins chiếm tỷ lệ cao.
> *Nguồn: Output Audit v4 — case sumon.mia (14 sign-ins, 100% foreign → tất cả countries thành Trusted ở 5%).*
> *Case Rahman.Mustafizur: Score tăng từ 55 → 408 sau fix — 10 hacker countries bị phát hiện đúng.*

---

## 3. Logic Nhận Diện Bất Thường (Anomaly Detection)

Hệ thống so sánh các lần đăng nhập với Baseline để tìm ra sự khác biệt:

### A. Phân biệt VPN/Công tác hợp lệ và Hacker (2 tầng nhận diện)
Đây là logic cốt lõi để loại bỏ False Positives cho các nhân viên đi công tác hoặc làm việc ở chi nhánh nước ngoài:

**Tầng 1 — Hacker Botnet (Foreign Country):**
*   **Hacker Botnet:** Đăng nhập từ **quốc gia lạ** (Foreign Country — không nằm trong TrustedCountries) **VÀ** thiết bị là thiết bị lạ (Unknown Device). → Phạt +30đ/country.
*   **VPN/Công tác hợp lệ:** Truy cập từ quốc gia lạ **NHƯNG** thiết bị sử dụng là **Trusted Device** (Tên máy tính quen thuộc). → +0đ.
*   **⚠️ Dedup (v3):** Nếu một quốc gia có **cả** sign-in Hacker (Unknown Device) **VÀ** sign-in VPN (Trusted Device), quốc gia đó **KHÔNG bị phạt**. Code: `hacker_only_countries = HackerBotnetCountries MINUS VPNCountries`. Điều này tránh False Positive cho nhân viên ở nước ngoài khi Entra ID thỉnh thoảng mất log DeviceName.

**Tầng 2 — Suspicious IP (Bất kể quốc gia — bắt hacker nội địa):**
*   Một IP được coi là **Suspicious** nếu nó là **Unknown IP** (không nằm trong TrustedIPs) **VÀ** **chưa từng xuất hiện cùng Trusted Device**. → Phạt +5đ/IP.
*   *Lý do:* Entra ID thường xuyên bị lỗi "inconsistent telemetry" (nhả log mất thông tin DeviceName trên cùng 1 IP/Laptop hợp lệ). Việc check "IP đó đã bao giờ dùng thiết bị an toàn chưa" giúp loại trừ 100% False Positive cho nhân viên đi công tác dùng WiFi công cộng.
*   Logic này được bổ sung sau [Post-Mortem #1](post_mortem_logic_fixes.md): hacker có thể dùng IP nội địa (cùng country với user) nên không thể chỉ dựa vào Foreign Country.
*   **Lưu ý:** Suspicious IP scoring **không double-count** với Benign Unknown IP scoring. Mỗi IP chỉ rơi vào 1 nhóm.

### B. Hành vi Xâm nhập (Post-Breach / Data Breach)
Hệ thống quét `CloudAppEvents` bằng cách đối chiếu với các địa chỉ IP của Hacker. Để giải quyết các điểm mù (xem thêm tại [Tài liệu Post-Mortem](post_mortem_logic_fixes.md)), một IP chỉ được đưa vào tầm ngắm Data Breach nếu nó đáp ứng điều kiện **Suspicious IP**:
- Là một địa chỉ mạng lạ (Unknown IP)
- **VÀ** xuất phát từ một thiết bị lạ / không định danh (Unknown/Empty Device)

Nếu phát hiện Suspicious IP có bất kỳ hành động nào dưới đây, mức độ nghiêm trọng sẽ tăng lên Tối Đa:
- Đánh cắp: `FileDownloaded`
- Phá hoại: `FileRecycled`, `FolderRecycled`
- Đọc trộm: `MailItemsAccessed`, `eDiscoverySearch`, `FileAccessed`
- Phát tán mã độc: `MessageSent` (qua Teams)
- Ẩn giấu vết: `New-InboxRule`, `Set-InboxRule`

> **Lưu ý:** `FileAccessed` (truy cập file) được bao gồm vì dữ liệu thực tế cho thấy đây là hành vi phổ biến thứ 2 của hacker (527 events), chỉ sau `MailItemsAccessed`.

### C. Loại trừ Microsoft Infrastructure IPs (v2 — 08-May-2026)

Hệ thống tự động loại trừ các IP thuộc hạ tầng nội bộ của Microsoft trước khi tính anomaly. Các IP này phát sinh khi Exchange Online thực hiện tác vụ nền (Managed Folder Assistant, mailbox auditing, auto-forwarding check) và ghi log sign-in từ IP datacenter — KHÔNG phải hoạt động của user thực.

**Dải IP được loại trừ:**
| Prefix | Mô tả |
|--------|--------|
| `2603:1046:` | Microsoft Corp MSN AS Block (Exchange Online - East Japan, etc.) |
| `2603:1036:` | Microsoft Corp (US regions) |
| `2603:1026:` | Microsoft Corp (EU regions) |
| `2603:1056:` | Microsoft Corp (APAC regions) |
| `40.107.` | Microsoft Exchange Online Protection |
| `52.100.` | Microsoft Exchange Online |
| `20.190.` | Azure AD / Entra ID authentication endpoints |
| `40.126.` | Azure AD / Entra ID authentication endpoints |

> *Nguồn: Audit Report KQL 11 — case Rahim Uddin (BD→JP): IP `2603:1046:c09:4bb::5` bị flag là AiTM Token Theft, nhưng thực tế là Exchange Online datacenter tại East Japan.*

---

## 4. Hệ Thống Tính Điểm (Scoring Matrix)

Điểm Anomaly Score được tính cộng dồn dựa trên các rủi ro sau:

| Rủi Ro | Công thức phạt (Penalty) | Max Cap | Ý Nghĩa |
|--------|---------------------------|---------|---------|
| **Data Breach Actions** | **+1000 điểm** (Ngay lập tức) | - | Hacker đã chạm vào dữ liệu (Xóa/Tải file) |
| **Suspicious IP Sign-ins** | **+5 điểm** / mỗi IP đáng ngờ | Max 50đ | Unknown IP + Unknown Device — bắt hacker nội địa |
| **Hacker Botnet Countries** | **+30 điểm** / mỗi quốc gia lạ | - | Hacker dùng Residential Proxy. **Dedup:** countries có cả VPN sign-in sẽ bị loại |
| **VPN Countries** | **+0 điểm** | - | Người dùng hợp lệ dùng VPN công ty |
| **Suspicious ISPs** | **+15 điểm** / mỗi ISP độc hại | - | Đăng nhập từ Hosting, VPS, mạng ẩn danh |
| **Unknown IPs** | **+2 điểm** / mỗi IP lạ | Max 30đ | IP lạ nhưng dùng Trusted Device (VPN/công tác) — không overlap SuspiciousIP |
| **Entra ID Risk Events** | **+5 điểm** / sự kiện | - | Microsoft đã gắn cờ Medium/High Risk cho session này (RiskLevel >= 50) |
| **Defender Alerts** | **+5 điểm** / cảnh báo | Max 25đ | **CONDITIONAL (v4.1):** Chỉ tính khi user CÓ compromise indicators (foreign sign-ins, suspicious IPs, hoặc HighRisk). Users chỉ bị blocked attack → 0 điểm |
| **Alert IP Correlation** | **+3 điểm** / mỗi IP trùng khớp | Max 30đ | Suspicious IP trùng với Unfamiliar Sign-in alert IP (Q00). **[MỚI v4]** |
| **Phishing Target** | **+5 điểm** / email lừa đảo | - | User là mục tiêu của chiến dịch Phishing |
| **Off-Hours Sign-ins** | **+0.5 điểm** / lần đăng nhập | Max 10đ | Đăng nhập vào ban đêm (ngoài giờ hành chính) |
| **Unmanaged Devices** | **+5 điểm** | Tĩnh | Nếu >80% lượt đăng nhập từ thiết bị cá nhân |
| **Admin Account Boost** | **+10 điểm** | Tĩnh | Nếu tài khoản có quyền Admin và đã bị nghi ngờ (≥ 15đ) |

---

## 5. Phân Loại Kết Quả (Verdict Classification)

Dựa vào tổng điểm, hệ thống gán 1 trong 4 nhãn sau để phân cấp ưu tiên xử lý:

1. **🚨 CONFIRMED COMPROMISED (Data Breach):** Bất kể điểm số là bao nhiêu, chỉ cần có hành vi Data Breach (hacker chạm vào dữ liệu), user bị đánh dấu đỏ khẩn cấp. Phải Block ngay lập tức.
2. **🔴 Likely Compromised (Score >= 30):** Rủi ro cực cao, có dấu hiệu Impossible Travel, dùng Botnet. Cần Investigate và Block.
3. **🟠 Suspicious (15 <= Score < 30):** Có hành vi lạ, dùng IP/ISP rủi ro nhưng chưa rõ ràng là hacker. Cần liên hệ người dùng để xác nhận (MFA re-registration).
4. **🟢 Likely Safe (Score < 15):** Điểm số thấp, hành vi chủ yếu là False Positive (ví dụ: nhân sự đi công tác hoặc dùng VPN an toàn). Không cần xử lý.

### 🆕 Verified Safe User Override (v4.2 — 09-May-2026)

Ngoài 4 nhãn tự động trên, hệ thống hỗ trợ cơ chế **SOC Override** cho phép analyst đánh dấu user đã xác minh thủ công là an toàn:

5. **🟢 Verified Safe (SOC Override):** User nằm trong whitelist `VERIFIED_SAFE_USERS`. Bất kể anomaly score:
   - CloudAppEvents **bị bỏ qua hoàn toàn** (DataBreachEvents = 0)
   - Anomaly Score = **0**
   - Verdict hiển thị lý do xác minh: `"SOC Override: [lý do]"`

**Cách sử dụng:** Thêm user vào dictionary `VERIFIED_SAFE_USERS` trong `analyze_signins.py`:
```python
VERIFIED_SAFE_USERS = {
    "user@domain.com": "Lý do xác minh — Ngày xác minh",
}
```

> *Nguồn: Post-Mortem #9 — case Button Lin (CSC entity, công tác HK/VN/CN → bị gán CONFIRMED COMPROMISED sai).*

---

## 6. CSV Output Columns (v3 — 08-May-2026)

File `user_investigation_summary.csv` chứa các cột đáng chú ý:

| Cột | Mô tả |
|-----|--------|
| `TrustedCountries` | Danh sách countries thực sự Trusted (≥5% sign-ins). *Trước v3 bị ghi sai = AllCountries.* |
| `AllCountries` | **[MỚI]** Tất cả countries từng xuất hiện trong sign-in history (bao gồm cả hacker-generated) |
| `TrustedCountryCount` | Số lượng TrustedCountries (≥5%) — dùng cho BaselineWarning |
| `SuspiciousIPs` | **[MỚI]** Danh sách IP cụ thể gây ra DataBreach (Unknown IP + chưa từng dùng Trusted Device) |
| `MicrosoftInfraIPsFiltered` | Số lượng MS infra IPs đã bị filter trước khi tính anomaly |
| `BaselineWarning` | Cảnh báo nếu TrustedCountryCount > 15 (baseline contamination) |
| `AlertIPsMatched` | **[MỚI v4]** Danh sách Suspicious IPs trùng với Unfamiliar Sign-in alert IPs (Q00) |
| `AlertIPsMatchedCount` | **[MỚI v4]** Số lượng IPs trùng khớp (dùng cho scoring +3/IP) |
| `UserAlertCount_Q00` | **[MỚI v4]** Tổng số alerts từ Q00 cho user này |
| `FirstAlertTimestamp` | **[MỚI v4]** Thời điểm alert đầu tiên — dùng cho temporal baseline split |
| `CrossUserAlertIPs` | **[MỚI v4]** Alert IPs xuất hiện ở user KHÁC nhưng sign-in thành công ở user này — botnet indicator |
| `EffectiveThreshold` | **[MỚI v4.1]** Threshold thực tế dùng cho baseline (5% hoặc 15% cho low-volume users) |

> **Lưu ý (v4 — 09-May-2026):**
> - Thêm `unfamiliar_signin_incidents.csv` (Q00) làm data source mới — chứa 991 Alert IPs từ Entra ID Protection.
> - Alert IP Correlation scoring: +3/IP khi Suspicious IP trùng với Alert IP, capped 30đ.
> - Cross-User correlation: phát hiện khi cùng 1 IP botnet tấn công nhiều users.
> - Source: `docs/alert_pipeline_source_of_truth.md`, `docs/pillar_alignment.md`
