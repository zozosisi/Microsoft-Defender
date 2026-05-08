# Tài Liệu Rút Kinh Nghiệm: Tối Ưu Logic Điều Tra Tự Động (Post-Mortem)

> **Mục đích:** Tài liệu này ghi nhận lại các lỗ hổng logic (False Positives/False Negatives) đã được phát hiện trong quá trình xây dựng hệ thống tự động hóa điều tra sự cố (Automated Incident Response) bằng Python, nguyên nhân gốc rễ và cách hệ thống đã được tinh chỉnh để giải quyết.

---

## 1. Lỗi Bỏ Lọt Hacker Sử Dụng IP Nội Địa (False Negative)

### Mô tả Vấn đề
Tài khoản **`Zakir.Ahmed@bd.crystal-martin.com`** bị tấn công chiếm đoạt (Compromised) và Hacker đã thực hiện hành vi trộm cắp dữ liệu (`MailItemsAccessed`, `FileDownloaded`). Tuy nhiên, hệ thống ban đầu báo cáo tài khoản này không có hành vi Data Breach (0 DataBreachEvents).

### Nguyên nhân Gốc rễ
- Bộ lọc Data Breach của hệ thống ban đầu được thiết lập chỉ quét các hành vi CloudAppEvents xuất phát từ **"HackerBotnetCountries"** (tức là chỉ nhắm vào các IP đến từ **Nước Ngoài**, không thuộc Bangladesh - BD).
- Tuy nhiên, trong trường hợp này, Hacker đã sử dụng một hạ tầng mạng nội địa tại Bangladesh (ISP: `axiata (bangladesh) limited`) để thực hiện cuộc tấn công. 
- Do IP của Hacker trùng với Quốc gia làm việc của user (BD), hệ thống đã coi đây là mạng an toàn và bỏ qua toàn bộ hành vi đánh cắp dữ liệu.

### Giải pháp Khắc phục
- Loại bỏ tư duy "Hacker luôn đến từ nước ngoài".
- Tái cấu trúc logic: Hệ thống giờ đây sẽ đưa **tất cả các IP Chưa Từng Thấy (Unknown IPs)** vào tầm ngắm, không phân biệt IP đó nằm ở trong nước hay quốc tế. Nếu có bất kỳ hành vi tương tác dữ liệu bất thường nào phát sinh từ một IP lạ, hệ thống lập tức theo vết.
- **Kết quả:** Hệ thống lập tức tóm gọn Hacker của Zakir Ahmed và cộng 1000 điểm phạt Data Breach.

---

## 2. Lỗi Phạt Oan Người Dùng Đi Công Tác (False Positive)

### Mô tả Vấn đề
Tài khoản **`button_lin@crystal-csc.cn`** (Button Lin) đi công tác từ Trung Quốc sang Việt Nam (VN) và Hồng Kông (HK). Anh ấy có thực hiện check email và tải file công việc bình thường. Hệ thống ngay lập tức gán cho tài khoản này nhãn **🚨 CONFIRMED COMPROMISED** và phạt 1190 điểm rủi ro.

### Nguyên nhân Gốc rễ
- Sau khi áp dụng bản vá lỗi số 1 (Đưa tất cả IP lạ vào tầm ngắm Data Breach), hệ thống lại mắc phải một lỗi quá nhạy cảm.
- Khi Button Lin mở email bằng Laptop công ty qua Wi-Fi khách sạn, hệ thống thấy có thao tác `MailItemsAccessed` từ một `Unknown IP`.
- **Tuy nhiên (Bug Telemetry của Entra ID):** Mặc dù Button Lin luôn dùng Laptop công ty (Trusted Device), nhưng log của Entra ID thỉnh thoảng lại bị rớt thông tin thiết bị (DeviceName bị rỗng) trên cùng một địa chỉ IP khách sạn đó. Do đó, hệ thống tưởng lầm rằng có một "Unknown Device" đang truy cập từ "Unknown IP" và gán nhãn Suspicious cho IP này.

### Giải pháp Khắc phục
- Bổ sung định nghĩa **Context-Aware** và **Telemetry Tolerance**:
- **Logic mới:** Một IP lạ chỉ bị coi là Đáng Ngờ (Suspicious IP) và bị đưa vào diện quét Data Breach **NẾU VÀ CHỈ NẾU** IP đó **chưa từng bao giờ** được sử dụng cùng với một **Thiết bị Hợp lệ (Trusted Device)**.
- Nếu một IP lạ có 100 lần đăng nhập bằng Trusted Device, nhưng bị rớt log rỗng mất 5 lần, hệ thống vẫn sẽ tha bổng cho IP này vì đã chứng minh được sự hiện diện của thiết bị an toàn.
- **Kết quả:** Các Data Breach events từ IP khách sạn của Button Lin giảm từ 199 xuống còn 12 (chỉ còn lại những IP lạ thực sự chưa từng gắn với Laptop công ty). Phân loại giảm xuống Likely Compromised.

---

## 3. Lỗi Tra Cứu Xuyên Bảng (Join Key Error)

### Mô tả Vấn đề
Khi đối chiếu dữ liệu giữa `signin_history.csv` (lịch sử đăng nhập) và `cloudapp_events.csv` (lịch sử thao tác app), Python script ban đầu trả về 0 kết quả cho tất cả người dùng, dù dữ liệu thực tế vẫn tồn tại.

### Nguyên nhân Gốc rễ
- Sự bất đồng nhất về Schema (Cấu trúc dữ liệu) giữa các nền tảng của Microsoft. 
- Log đăng nhập (Entra ID) thường định danh người dùng bằng địa chỉ Email (`AccountUpn`). Trong khi đó, một số bảng của Defender (như `CloudAppEvents`) lại định danh người dùng bằng dãy mã GUID (`AccountObjectId`).
- Việc dùng chuỗi Email để quét trong cột chứa mã GUID tự nhiên không mang lại bất kỳ kết quả nào.

### Giải pháp Khắc phục
- Cập nhật cơ chế Mapping trong Python: Yêu cầu script phải đồng bộ cả 2 trường `AccountId` (Email) và `AccountObjectId` (GUID). Bất kỳ truy vấn chéo nào cũng phải so khớp song song cả 2 định dạng này để tránh rớt dữ liệu (Data Loss).

---

## 4. Lỗi Thiếu Dữ Liệu MFA & Mật Khẩu (Data Dependency)

### Mô tả Vấn đề
Báo cáo điều tra (Report) hiển thị `Unknown` cho trạng thái MFA và thời gian đổi mật khẩu của toàn bộ user bị ảnh hưởng.

### Nguyên nhân Gốc rễ
- File `auth_status.csv` được trích xuất từ bảng `IdentityAccountInfo` (thuộc Defender for Identity). Tuy nhiên, môi trường hiện tại chưa đồng bộ toàn diện Defender for Identity (hoặc cấu hình UEBA chưa phủ hết), dẫn đến cột `EnrolledMfas` trống trơn và thời gian trả về `Invalid date`.

### Giải pháp Khắc phục
- Thiết kế tính năng **"Cross-Table Fallback" (Dự phòng chéo)**.
- Khi nhận thấy `IdentityAccountInfo` bị thiếu dữ liệu, Python sẽ tự động quay ngược lại phân tích bảng Log Đăng Nhập (`signin_history.csv`). 
- Nếu trong 30 ngày qua, hệ thống phát hiện có bất kỳ lần đăng nhập nào của user có tham số `AuthenticationRequirement == MultiFactorAuthentication`, Python sẽ tự động kết luận tài khoản này ĐÃ CÓ MFA (MFA Enforced).
- **Kết quả:** Hệ thống vẫn trích xuất được bằng chứng 100% mà không bị phụ thuộc chết vào một nguồn dữ liệu duy nhất.

---

## 5. Lỗi Gán Nhãm AiTM Cho IP Hạ Tầng Microsoft (False Positive — KQL 11)

### Mô tả Vấn đề
Tài khoản **`Rahim.Uddin@crystal-cet.com.bd`** bị KQL 11 flag là **"🚨 100% AiTM Token Theft"** do SessionId xuất hiện ở cả Bangladesh (BD) và Nhật Bản (JP). Tuy nhiên, đây là False Positive.

### Nguyên nhân Gốc rễ
- IP "Nhật Bản" (`2603:1046:c09:4bb::5` và `2603:1046:c09:4ad::5`) thuộc dải `2603:1046::/32` — đây là **MICROSOFT-CORP-MSN-AS-BLOCK (AS8075)**, IP hạ tầng nội bộ của Microsoft Exchange Online.
- Khi Exchange Online thực hiện các tác vụ nền (Managed Folder Assistant, mailbox auditing, auto-forwarding check), nó ghi log sign-in từ IP datacenter. Country hiển thị JP vì Microsoft có datacenter tại East Japan.
- DeviceList rỗng `[""]` vì đây là service-level activity, không phải user sign-in từ thiết bị thực.
- KQL 11 cũ không phân biệt được IP infrastructure và IP user → gán nhãn sai.

### Giải pháp Khắc phục
- Thêm filter loại trừ Microsoft infrastructure IP ranges vào cả **KQL 11** và **Python pipeline**.
- Dải IP được loại trừ: `2603:1046:`, `2603:1036:`, `2603:1026:`, `2603:1056:`, `40.107.`, `52.100.`, `20.190.`, `40.126.`
- **Kết quả:** Rahim Uddin không còn bị flag False Positive. Các session từ Exchange Online backend được tự động loại trừ.

---

## 6. Lỗi Baseline Bị Ô Nhiễm Bởi Hacker (Baseline Contamination — Python Pipeline)

### Mô tả Vấn đề
Pipeline kết luận **Niaz Morshed** là "100% AiTM" dựa trên session nhảy từ BD sang HK/CN. Tuy nhiên, phân tích sâu cho thấy HK và CN đều nằm trong TrustedCountries baseline của Niaz (20 countries). Kết luận "100%" quá tự tin và không chính xác.

### Nguyên nhân Gốc rễ
- `build_user_baseline()` tính TrustedCountries từ **toàn bộ 30 ngày** sign-in data, bao gồm cả khoảng thời gian hacker đã hoạt động.
- Nếu hacker tạo đủ nhiều sign-in từ 1 quốc gia (≥ 5% tổng sign-ins), quốc gia đó lọt vào TrustedCountries → pipeline coi đó là bình thường.
- Các user bị compromised nặng nhất (Touhith=24, Sumi=24, Abdul=23, Nargis=21, Niaz=20 TrustedCountries) cũng là những user có TrustedCountries cao nhất — gợi ý chính hacker đã tạo ra các sign-in đó.

### Giải pháp Khắc phục
- Thêm **Baseline Contamination Warning**: Khi user có hơn 15 TrustedCountries, pipeline tự động cảnh báo `"⚠️ X Trusted Countries — possible baseline contamination by attacker"`.
- Trong KQL 11: Thay đổi verdict logic — nếu tất cả countries trong session đều nằm trong TrustedCountries, severity giảm từ "🚨 Highly Likely AiTM" xuống "🟡 Review Required" để analyst review thủ công.
- **Lưu ý:** Đây là giải pháp Option A (Warning-based). Option B (tính baseline chỉ từ pre-attack window) phức tạp hơn và yêu cầu biết thời điểm tấn công bắt đầu.

---
*Tài liệu này được tạo ra để lưu trữ làm Knowledge Base cho các vòng phát triển SOC Automation tiếp theo.*
