# Risk Remediation: User Risk Không Clear Sau Password Reset (Hybrid AD)

> **Cập nhật:** 09-May-2026  
> **Vấn đề:** Users BD đã remediate (reset password + MFA + revoke session) nhưng vẫn HIGH risk → alert loop  
> **Trạng thái:** Đang triển khai

> [!NOTE]
> **Source:** Tài liệu này đã cross-verify 100% với Microsoft Learn (updated 21-Apr-2026):
> - 📘 [Remediate risks and unblock users](https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-remediate-unblock)
> - 📘 [Investigate risk](https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-investigate-risk)

---

## Nguyên Nhân `📘 MS LEARN`

Crystal Group dùng **Hybrid AD** (on-prem AD sync lên Entra ID). Khi admin reset password trên on-prem AD, Entra ID **KHÔNG tự động clear User Risk** — vì nó không thể xác minh password change có an toàn hay không.

| Phương thức reset | Auto-clear risk? |
|-------------------|:---:|
| Cloud SSPR (user + MFA) | ✅ |
| Admin reset qua Entra Portal | ✅ |
| On-prem AD reset (default) | ❌ |
| On-prem AD reset (với setting enabled) | ✅ |

---

## Action Plan `📘 MS LEARN` + `📊 INTERNAL`

| # | Hành động | Timeline | MS Learn Ref |
|---|-----------|----------|--------------|
| 1 | **Dismiss User Risk** cho users đã remediate | ⚡ Ngay | [Dismiss risk](https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-remediate-unblock#dismiss-risk) |
| 2 | **Enable "Allow on-premises password change to reset user risk"** | ⚡ Ngay | [Allow on-prem reset](https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-remediate-unblock#allow-on-premises-password-reset-to-remediate-user-risks) |
| 3 | **Verify PHS active** | ⚡ Ngay | [PHS docs](https://learn.microsoft.com/en-us/entra/identity/hybrid/connect/whatis-phs) |
| 4 | **Consider SSPR** | Trung hạn | [Enable SSPR](https://learn.microsoft.com/en-us/entra/identity/authentication/tutorial-enable-sspr) |

> **Lưu ý:** Step 2 chỉ áp dụng cho future password changes. Step 1 phải làm trước để clear users hiện tại.

---

## Admin Actions Reference `📘 MS LEARN`

| Action | Phân loại | Khi nào dùng |
|--------|-----------|-------------|
| **Dismiss User Risk** | Benign Positive | Risk thật nhưng đã remediate xong |
| **Confirm User Safe** | False Positive | Risk SAI — dạy lại ML |
| **Confirm Compromised** | True Positive | Xác nhận user bị hack |

### Token Theft Detections — Không tự auto-remediate `📘 MS LEARN`

Các detections sau KHÔNG tự clear khi user MFA (update Apr 2026):
- Anomalous Token
- Attacker in the Middle (AiTM)
- Verified Threat Actor IP
- Token Issuer Anomaly

→ Cần admin Dismiss thủ công.
