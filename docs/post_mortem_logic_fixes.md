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
- Khi người dùng đi công tác, việc họ kết nối vào Wi-Fi sân bay, Wi-Fi khách sạn sẽ tự động sinh ra hàng loạt **IP lạ (Unknown IPs)**.
- Khi Button Lin mở email bằng Laptop công ty qua Wi-Fi khách sạn, hệ thống thấy có thao tác `MailItemsAccessed` từ một `Unknown IP` nên lập tức quy kết đây là hành vi Data Breach.

### Giải pháp Khắc phục
- Bổ sung định nghĩa **Context-Aware** cho hệ thống: Điểm khác biệt lớn nhất giữa một Hacker và một Nhân viên đi công tác nằm ở **Thiết Bị (Device)**.
- **Logic mới:** Một IP lạ chỉ bị coi là Đáng Ngờ (Suspicious IP) và bị đưa vào diện quét Data Breach **NẾU VÀ CHỈ NẾU** IP đó đi kèm với một **Thiết bị Xa lạ (Unknown Device)** hoặc không có định danh thiết bị.
- Ngược lại, nếu người dùng truy cập từ một IP lạ (như Wi-Fi khách sạn) nhưng vẫn đang sử dụng đúng **Thiết bị Hợp lệ (Trusted Device)** (Laptop/Điện thoại đã đăng ký), hệ thống sẽ nhận diện đây là hành vi đi công tác (Travel/Remote Work) và không phạt điểm Data Breach.
- **Kết quả:** Tài khoản Button Lin được giải oan, điểm rủi ro trở về mức an toàn (190 điểm).

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
*Tài liệu này được tạo ra để lưu trữ làm Knowledge Base cho các vòng phát triển SOC Automation tiếp theo.*
