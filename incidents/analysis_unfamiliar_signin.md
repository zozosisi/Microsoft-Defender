# 🔴 Phân Tích Alert: Unfamiliar Sign-in Properties — Crystal Group BD

> **Nguồn dữ liệu:** `RiskyUsers.csv` (55 users at risk) + `incidents-queue-20260506.csv` (295 incidents)
> **Thời điểm phân tích:** 2026-05-07, dữ liệu mới nhất tính đến ngày 2026-05-06

---

## 1. Tóm Tắt Tổng Quan

| Chỉ số | Giá trị |
|--------|---------|
| Tổng số incidents | **295** |
| Incidents đang Active | **~60+** |
| Incidents đã Resolved | **~230+** |
| Users bị At Risk (RiskyUsers.csv) | **55 users** |
| Users Risk Level = **High** | **4 users** |
| Users Risk Level = **Medium** | **51 users** |
| Thời gian bắt đầu bùng phát | **~18 April 2026** |
| Đỉnh điểm | **04–06 May 2026** |
| Entity chịu ảnh hưởng chính | **crystal-abl.com.bd**, **bd.crystal-martin.com**, **crystal-cet.com.bd** |

---

## 2. Phân Tích Nguyên Nhân Chính

### ❗ Vấn đề cốt lõi: MFA không đủ để ngăn alert "Unfamiliar Sign-in Properties"

Alert này được kích hoạt bởi **Azure AD Identity Protection**, không phải do đăng nhập thất bại hay bypass MFA. Ngay cả khi user **đã hoàn thành MFA thành công**, alert vẫn sẽ xuất hiện nếu hệ thống phát hiện các **dấu hiệu bất thường** trong phiên đăng nhập, ví dụ:

| Yếu tố kích hoạt alert | Mô tả |
|------------------------|-------|
| 🌍 **IP/Location lạ** | User đăng nhập từ IP hoặc quốc gia chưa từng xuất hiện trong lịch sử |
| 🖥️ **Device/Browser mới** | Thiết bị, OS, hoặc trình duyệt chưa từng dùng trước đây |
| ⏰ **Thời gian bất thường** | Đăng nhập vào giờ giấc khác hẳn pattern thông thường |
| 🔁 **Impossible Travel** | Đăng nhập từ 2 địa điểm xa nhau trong khoảng thời gian ngắn |
| 🧩 **ASN/ISP bất thường** | Dùng VPN, proxy, hoặc ISP chưa từng xuất hiện |
| 📱 **App mới truy cập** | Truy cập vào M365 app/service chưa từng dùng |

> **MFA chỉ xác thực danh tính — không loại trừ được risk signal về hành vi đăng nhập.** Đó là lý do tại sao sau khi enable MFA và revoke session, alert vẫn tiếp tục xuất hiện.

---

## 3. Top Users Bị Ảnh Hưởng Nhiều Nhất

Dưới đây là các users xuất hiện nhiều nhất trong incidents (tính theo số incident):

| Rank | Tên User | Email | Số Incident | Risk Level |
|------|----------|-------|-------------|------------|
| 1 | **Islam Nurul (QAD/CMBD)** | Islam.Nurul@bd.crystal-martin.com | 6+ incidents | High |
| 2 | **Shuvrodev Bepari (ADM/ABL)** | Shuvrodev_Bepari@crystal-abl.com.bd | 6+ incidents | High |
| 3 | **Jumur Akter (DYE/CETBD)** | Jumur.Akter@crystal-cet.com.bd | 5+ incidents | High |
| 4 | **Airin Rahman Rakhi (SUS/CMBD)** | Airin.Rahman@bd.crystal-martin.com | 6+ incidents | High |
| 5 | **Fahimuzzaman Md (QAD/ABL)** | Fahimuzzaman_Md@crystal-abl.com.bd | 5+ incidents | Medium |
| 6 | **Mahfuzur Rahman (QAD/CMBD)** | Mahfuzur.Rahman@bd.crystal-martin.com | 5+ incidents | Medium |
| 7 | **Rayhan Ali (QAD/ABL)** | Rayhan_Ali@crystal-abl.com.bd | 4+ incidents | Medium |
| 8 | **Nila Hasda (MER/CMBD)** | Nila.Hasda@bd.crystal-martin.com | 5+ incidents | Medium |
| 9 | **Rahim Uddin (QAD/HAY)** | Rahim.Uddin@crystal-cet.com.bd | 5+ incidents | Medium |
| 10 | **Nannu Mia (DEV/CMBD)** | Nannu.Mia@bd.crystal-martin.com | 4+ incidents | Medium |

> **Đáng chú ý:** `cmaadmmk` (tài khoản có vẻ là admin account - `cmaadmmk@bd.crystal-martin.com`) cũng xuất hiện trong incident list với Risk Level **Medium** — cần được ưu tiên kiểm tra.

---

## 4. Phân Tích Theo Domain/Entity

| Domain | Số Users At Risk (ước tính) | Mức độ |
|--------|---------------------------|--------|
| `crystal-abl.com.bd` (ABL) | ~20 users | 🔴 Cao nhất |
| `bd.crystal-martin.com` (CMBD) | ~18 users | 🔴 Cao |
| `crystal-cet.com.bd` (CETBD/HAY) | ~10 users | 🟠 Trung bình |
| `crystal-csc.cn`, `crystalgroup.com`, `.kh`, `.vn` | ~7 users | 🟡 Rải rác |

→ **ABL và CMBD là hai entity bị ảnh hưởng nặng nhất**, tập trung chủ yếu ở Bangladesh operations.

---

## 5. Timeline Bùng Phát

```
April 17-18: Bắt đầu xuất hiện (5-6 incidents/ngày)
April 19-20: Tăng mạnh (~15-20 incidents)
April 21-22: Đạt mức cao (~20 incidents)
April 23-26: Duy trì ở mức cao (~15-20/ngày)
April 27-30: Tiếp tục (~20-25 incidents)
May 01-03:   Vẫn cao (~20 incidents)
May 04-05:   Tăng đỉnh (~30 incidents)
May 06:      Rất nhiều (40+ incidents trong 1 ngày, còn nhiều Active)
```

> ⚠️ **Xu hướng đang LEO THANG, không giảm** — mỗi ngày có hàng chục incidents mới.

---

## 6. Tại Sao Revoke Session Không Giải Quyết Được Vấn Đề?

Khi bạn revoke session:
- Token hiện tại bị vô hiệu hóa ✅
- User phải đăng nhập lại ✅
- **Nhưng**: Nếu pattern đăng nhập của user vẫn từ thiết bị/location lạ → Azure AD Identity Protection sẽ tạo incident MỚI ngay lập tức ❌

**Vòng lặp xảy ra:**
```
User đăng nhập từ thiết bị/IP lạ
  → Entra ID tạo Risk Signal
    → Defender tạo Incident
      → Admin revoke session
        → User đăng nhập lại (vẫn từ IP/thiết bị đó)
          → Incident MỚI được tạo
```

---

## 7. Khuyến Nghị Hành Động (Ưu Tiên)

### 🔴 Ngay Lập Tức (0–24h)

1. **Điều tra các user High Risk trước:**
   - `Airin Rahman Rakhi` — Risk High, 6+ incidents
   - `Abdullah Zubair (ASG/ABL)` — Risk High, 16+ active alerts trong 1 incident
   - `Shuvrodev Bepari (ADM/ABL)` — Risk High, 6+ incidents
   - `Jumur Akter (DYE/CETBD)` — Risk High, nhiều incidents liên tiếp

2. **Kiểm tra tài khoản admin `cmaadmmk`:**
   - Đây có thể là service account hoặc admin account bị compromise
   - Cần kiểm tra login history ngay lập tức trong Entra ID Sign-in Logs

3. **Confirm Remediated Risk cho incidents đã investigate:**
   - Trong Microsoft Entra ID → Identity Protection → Risky Users
   - Sau khi xác nhận safe → nhấn **"Confirm users safe"** để clear risk state
   - Điều này ngăn hệ thống tiếp tục tái-tạo incident cho cùng risk event

### 🟠 Ngắn Hạn (1–7 ngày)

4. **Bật Conditional Access Policy — Block Unfamiliar Locations:**
   - Tạo Named Locations cho Bangladesh (IPs chuẩn của văn phòng)
   - Yêu cầu MFA hoặc block hoàn toàn khi sign-in từ location không thuộc danh sách

5. **Bật Conditional Access — Require Compliant Device:**
   - Chỉ cho phép đăng nhập từ Intune-managed/compliant devices
   - Điều này sẽ chặn hầu hết các sign-in từ thiết bị lạ

6. **Cấu hình Identity Protection Policy:**
   - **User risk policy**: Medium/High → Force password change + MFA
   - **Sign-in risk policy**: Medium/High → Require MFA (không chỉ notify)
   - Điều này đảm bảo system tự động remediate thay vì chỉ tạo alert

7. **Named Locations & Trusted IPs:**
   - Định nghĩa tất cả IP của office/nhà máy Bangladesh là Trusted Location
   - Giảm false positive cho users làm việc trong văn phòng

### 🟡 Dài Hạn (1–4 tuần)

8. **Review và Tune Alert Threshold:**
   - Phân tích xem bao nhiêu % alerts là False Positive (user thực sự an toàn)
   - Dùng Defender XDR → Advanced Hunting để trace sign-in logs

9. **Deploy Microsoft Authenticator Number Matching:**
   - Ngăn MFA fatigue attack (user vô tình approve MFA prompt của attacker)

10. **Tích hợp UEBA (User and Entity Behavior Analytics):**
    - Build baseline behavior cho từng user
    - Alert chỉ khi thực sự deviates từ baseline, giảm noise

---

## 8. Lý Giải "Investigation State: Unsupported alert type"

Tất cả incidents đều có `Investigation state = Unsupported alert type`. Đây là do:

- Alert type `AAD Identity Protection` thuộc loại **không có automated investigation playbook** trong Defender XDR
- Điều này là **bình thường** và không phải lỗi — cần manual review

---

## 9. Kết Luận

> **Root Cause:** Có một lượng lớn users Bangladesh đang đăng nhập từ **IP/thiết bị/location chưa từng có trong lịch sử** của họ — có thể do: (1) làm việc từ xa/di chuyển, (2) đổi thiết bị, (3) dùng mobile data thay wifi văn phòng, hoặc (4) một số tài khoản thực sự đang bị compromise.

> **MFA và revoke session không giải quyết được gốc rễ** vì alert phản ánh *hành vi đăng nhập bất thường*, không phải *xác thực thất bại*. Cần phải **remediate risk state trong Entra ID** và **áp dụng Conditional Access** để chặn hoặc kiểm soát các sign-in từ môi trường lạ.

> **⚡ Hành động ưu tiên nhất hiện tại:** Vào Entra ID → Risky Users → Investigate từng High Risk user → Confirm safe hoặc confirm compromised → Áp dụng CA Policy based on location/device compliance.

---

## 10. Cập Nhật Phân Tích Bằng Python Script (May 08)

Sau khi export toàn bộ log (222,000+ dòng) và phân tích bằng Python (`analyze_signins.py`), chúng ta đã phát hiện ra một số False Positives nghiêm trọng từ logic đánh giá ban đầu và đã tinh chỉnh lại:

### ⚠️ False Positives Do Logic "Non-BD Sign-ins"
- **Vấn đề:** Ban đầu, hệ thống cộng điểm dị thường cực kỳ cao cho *mọi* lượt đăng nhập ngoài Bangladesh. Điều này khiến các nhân sự hợp lệ tại chi nhánh nước ngoài (ví dụ: `button_lin@crystal-csc.cn` ở Trung Quốc) bị đẩy lên top rủi ro với Anomaly Score vọt lên >160,000 điểm.
- **Giải pháp:** Đã sửa Python script để phạt theo **tỷ lệ và sự đa dạng (variety)** của quốc gia/IP thay vì đếm số lần. Hệ quả: Điểm của `button_lin` giảm xuống còn 110, phản ánh đúng tính chất an toàn hơn.

### 🔴 Top Rủi Ro Thực Sự (Sau Khi Tinh Chỉnh Logic)
Khi đã loại trừ nhiễu, các user có hành vi Impossible Travel / Proxy Hopping nguy hiểm nhất lộ diện:
1. **`Zakir.Ahmed@bd.crystal-martin.com` (Top 1):** Đăng nhập từ **14 quốc gia khác nhau**, 3,279 lượt dùng IP lạ không thuộc thói quen.
2. **`Mahmudul.Hasan@bd.crystal-martin.com` (Top 2):** Đăng nhập từ **13 quốc gia khác nhau**, 995 lượt dùng IP lạ, tỷ lệ nhảy ISP không uy tín cao.

**Kết luận cuối cùng:** Tập trung khoanh vùng và chặn lập tức các user Top 5 trong file `user_investigation_summary.csv` mới nhất, do họ có dấu hiệu sử dụng proxy/botnet quy mô lớn để qua mặt hệ thống.
