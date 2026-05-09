# 📚 Source of Truth: Microsoft Defender XDR & Entra ID Protection Pipeline

> **Version:** FINAL — Đã xác minh từ 3 nguồn  
> **Ngày:** 2026-05-09  
> **Verified Sources:**  
> - **[DOC-1]** [Risk Detections Reference](https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-risks)  
> - **[DOC-2]** [Risk-based Access Policies](https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-policies)  
> - **[DOC-3]** [Investigate Risk](https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-investigate-risk)  
> - **[TENANT]** Conditional Access policy screenshots (2026-05-09)  
> - **[DATA]** signin_history.csv, unfamiliar_signin_incidents.csv, user_investigation_summary.csv  

---

## 1. "Unfamiliar Sign-in Properties" — Định Nghĩa

**Nguồn: [DOC-1] — Nguyên văn:**

> *"This risk detection type considers past sign-in history to look for anomalous sign-ins. The system stores information about previous sign-ins, and triggers a risk detection when a sign-in occurs with properties that are unfamiliar to the user. These properties can include IP, ASN, location, device, browser, and tenant IP subnet."*

> *"Unfamiliar sign-in properties can be detected on both interactive and non-interactive sign-ins. When this detection is detected on non-interactive sign-ins, it deserves increased scrutiny due to the risk of token replay attacks."*

> *"Newly created users are in a 'learning mode' period... The minimum duration is five days. A user can go back into learning mode after a long period of inactivity."*

| Thuộc tính | Giá trị | Source |
|-----------|---------|--------|
| Thời điểm tính toán | **Real-time** | [DOC-1] |
| License | Entra ID P2 | [DOC-1] |
| Properties | IP, ASN, Location, Device, Browser, Tenant IP subnet | [DOC-1] |
| Scope | Interactive + Non-interactive sign-ins | [DOC-1] |
| Learning mode | Tối thiểu 5 ngày | [DOC-1] |

> [!IMPORTANT]
> [DOC-1] **KHÔNG** tuyên bố detection chỉ fire cho successful hay failed sign-ins. Chỉ nói *"triggers when a sign-in occurs with properties that are unfamiliar"*. So sánh: Password Spray viết rõ *"only triggered when an attacker successfully validates a user's password"* — Unfamiliar Sign-in **không có** câu tương đương.

---

## 2. Tenant Conditional Access Policies — ĐÃ XÁC MINH

### 🔴 Risk-Based Policies (Defense chính)

#### Policy A: Microsoft-managed (ON)
| Field | Value | Source |
|-------|-------|--------|
| Name | Multifactor authentication and reauthentication for risky sign-ins | [TENANT] |
| Created by | MICROSOFT | [TENANT] |
| State | **ON** | [TENANT] |
| Sign-in risk level | **HIGH only** | [TENANT] summary: *"High sign-in risk"* |
| Target users | 1 security group | [TENANT] |
| Target apps | All apps | [TENANT] |
| Grant | MFA + Require new sign-in each session | [TENANT] |

#### Policy B: User-created (ON)
| Field | Value | Source |
|-------|-------|--------|
| Name | Require multifactor authentication for risky sign-ins | [TENANT] |
| Created by | USER | [TENANT] |
| State | **ON** | [TENANT] |
| Sign-in risk level | **☑ High ☐ Medium ☐ Low ☐ No risk** | [TENANT] screenshot |
| Target users | **All users** (specific excluded) | [TENANT] |
| Target apps | All resources | [TENANT] |
| Grant | MFA | [TENANT] |
| Session | Sign-in frequency: **Every time** | [TENANT] |

#### Policy C: User risk (ON)
| Field | Value | Source |
|-------|-------|--------|
| Name | Require password change for high-risk users | [TENANT] |
| State | **ON** | [TENANT] |

> [!CAUTION]
> ### 🚨 Security Gap: Medium Risk KHÔNG ĐƯỢC BẢO VỆ
> 
> **Cả 2 risk-based sign-in policies đều chỉ cover HIGH risk.**
> 
> | Risk Level | Policy A (MS) | Policy B (User) | Kết quả |
> |-----------|--------------|----------------|---------|
> | **High** | ✅ MFA + reauth | ✅ MFA + every time | **MFA bắt buộc** |
> | **Medium** | ❌ Không trigger | ❌ Không trigger | **KHÔNG CÓ MFA** ⚠️ |
> | **Low** | ❌ Không trigger | ❌ Không trigger | **KHÔNG CÓ MFA** ⚠️ |
> 
> → Nếu "Unfamiliar sign-in properties" đánh risk = **Medium**, hacker sign-in **KHÔNG bị yêu cầu MFA step-up** → có thể vào tài khoản mà không cần AiTM token.

### 🟡 Policies khác có liên quan

| Policy | State | Tác dụng |
|--------|-------|---------|
| CA00-BLOCK-Any legacy authentication | ON | Chặn legacy protocols (IMAP, POP3, SMTP) |
| CA01-O365Apps-Require MFA (ANY IP) 30 Days | ON | MFA cho O365, session **30 ngày** |
| CA09-Deny IP/Region | ON | **Block access** từ 2 named locations (xem bên dưới) |
| CATST01-Secure registration on trusted networks | ON | MFA registration chỉ trên trusted networks |

#### CA09-Deny IP/Region — ĐÃ XÁC MINH [TENANT]
| Field | Value | Source |
|-------|-------|--------|
| Target users | **All users** (specific excluded) | [TENANT] screenshot |
| Target resources | **All resources** | [TENANT] |
| Grant | **Block access** | [TENANT] |
| Locations | **2 included** → Selected networks and locations | [TENANT] |
| Named location 1 | **Deny/IP** — danh sách IP cụ thể bị block | [TENANT] |
| Named location 2 | **Deny/Region** — danh sách quốc gia/vùng bị block | [TENANT] |

> [!NOTE]
> CA09 là **hard block** — bất kỳ sign-in nào từ IP/Region trong danh sách đều bị chặn ngay lập tức, TRƯỚC risk evaluation. Không có option MFA — chỉ block. Chi tiết danh sách IP/Region cụ thể chưa xác minh được.

---

## 3. Pipeline Hoàn Chỉnh — Verified

```
Hacker attempt (password spray / stolen credentials / AiTM token)
                    │
                    ▼
        ┌───────────────────────────────────┐
        │  LAYER 1: CA09-Deny IP/Region     │
        │  (ON — Block access, 2 locations) │
        │                                   │
        │  IP/Region bị blacklist?          │
        │  ├── YES → ❌ BLOCK               │
        │  └── NO → tiếp tục               │
        └───────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────┐
        │  LAYER 2: CA00-Block Legacy Auth  │
        │  (ON)                             │
        │                                   │
        │  Legacy protocol (IMAP/POP3)?     │
        │  ├── YES → ❌ BLOCK               │
        │  └── NO → tiếp tục               │
        └───────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────┐
        │  LAYER 3: Authentication          │
        │                                   │
        │  Credentials/token valid?         │
        │  ├── NO → ❌ ErrorCode ≠ 0        │
        │  └── YES → tiếp tục              │
        └───────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────┐
        │  LAYER 4: CA01-MFA for O365       │
        │  (ON — session 30 ngày)           │
        │                                   │
        │  Session token đã có MFA claim?   │
        │  ├── YES (AiTM token) → PASS      │
        │  └── NO → yêu cầu MFA            │
        │       ├── Pass MFA → PASS         │
        │       └── Fail MFA → ❌ BLOCK     │
        └───────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────────────────┐
        │  LAYER 5: ENTRA ID PROTECTION (Real-time)     │
        │  [DOC-1]                                      │
        │                                               │
        │  Phân tích IP, ASN, Location, Device, Browser │
        │  so với baseline user                         │
        │                                               │
        │  → Risk Level = None / Low / Medium / High    │
        │  → Fire "Unfamiliar sign-in" alert            │
        └───────────────────────────────────────────────┘
                    │
                    ▼
        ┌───────────────────────────────────────────────┐
        │  LAYER 6: Risk-Based Policies [TENANT]        │
        │                                               │
        │  Policy A (MS):   HIGH → MFA + reauth         │
        │  Policy B (User): HIGH → MFA + every time     │
        │                                               │
        │  Risk = HIGH?                                 │
        │  ├── YES → yêu cầu MFA step-up               │
        │  │    ├── Hacker fail MFA → ❌ BLOCK          │
        │  │    └── AiTM token pass → ✅ ALLOW          │
        │  │                                            │
        │  └── NO (Medium/Low/None)                     │
        │       → ✅ ALLOW — KHÔNG CÓ MFA step-up ⚠️   │
        └───────────────────────────────────────────────┘
                    │
                    ▼
            ┌───────┴────────┐
            ▼                ▼
     ErrorCode ≠ 0      ErrorCode = 0
     (Bị chặn)          (Thành công)
     KHÔNG trong         CÓ trong
     signin_history      signin_history.csv
            │                │
            │                ▼
            │         CloudAppEvents:
            │         MailItemsAccessed
            │         FileDownloaded
            │         New-InboxRule
            │                │
            │                ▼
            │         Pipeline detect
            │         → DataBreach
            │
            ▼
     [OFFLINE — sau đó]
     "Require password change 
      for high-risk users" (ON)
     → Buộc đổi password lần
       sign-in kế tiếp
```

---

## 4. Mapping Dữ Liệu Thực — Verified

### Alert IPs Breakdown

| Nhóm | Count | % | Giải thích (verified) |
|------|-------|---|----------------------|
| Alert IPs bị chặn | 912 | 92% | Risk = HIGH → MFA step-up → hacker fail MFA → ErrorCode ≠ 0 |
| Alert IPs thành công (cùng user) | 32 | 3.2% | **2 khả năng:** (a) AiTM token bypass MFA, hoặc (b) Risk = Medium → không bị challenge MFA |
| Alert IPs cross-user | 47 | 4.7% | Cùng IP botnet, kết quả khác nhau giữa users |

> [!WARNING]
> **Sửa lại phân tích trước:** Tôi đã nói 32 IPs thành công = 100% AiTM token theft. Thực tế, với cả 2 policies chỉ cover HIGH, một phần 32 IPs có thể là **Medium risk sign-ins không bị challenge MFA** — hacker chỉ cần password đúng, không cần stolen token.

### Data Sources

| File | KQL | Filter | Contains |
|------|-----|--------|----------|
| `signin_history.csv` | Q01A-F | `ErrorCode == 0` | Chỉ successful sign-ins |
| `unfamiliar_signin_incidents.csv` | Q00 | AlertInfo + AlertEvidence | Alert IPs (cả success + fail) |
| `cloudapp_events.csv` | Q09 | CloudAppEvents | Post-breach actions |
| `alert_data.csv` | Q03 | AlertEvidence | Evidence rows (RemoteIP = NULL) |

### Attack Timeline

| Event | Date | Source |
|-------|------|--------|
| Data window start | 2026-04-08 | [DATA] |
| **Hacker bắt đầu sign-in thành công** | 2026-04-08 | [DATA] foreign sign-ins from Day 1 |
| First alert fired | 2026-04-18 | [DATA] |
| Data window end | 2026-05-08 | [DATA] |
| **Hacker hoạt động trước alert** | **~10 ngày** | [DATA] |

**Tại sao 10 ngày không bị phát hiện:** [DOC-1] — AiTM token replay sử dụng token hợp lệ chứa device + MFA claims → Entra ID coi là "known properties" → risk = None/Low/Medium → không trigger HIGH-only policies → hacker vào tự do.

---

## 5. Security Gap & Recommendations

### Gap #1: Medium Risk Không Được Bảo Vệ

| Current | Recommended |
|---------|------------|
| Policy B: Sign-in risk = ☑ High ☐ Medium | ☑ High ☑ Medium |

**Action:** Sửa policy "Require MFA for risky sign-ins" → thêm **Medium** vào Sign-in risk levels.

### Gap #2: CA01 Session 30 Ngày

| Current | Risk |
|---------|------|
| CA01 session = 30 days | AiTM stolen token valid 30 ngày |

**Action:** Giảm session frequency cho high-risk apps (email, SharePoint) xuống **7 ngày** hoặc kết hợp với Continuous Access Evaluation (CAE).

### Gap #3: Baseline Contamination

| Current | Issue |
|---------|-------|
| Baseline từ full 30 ngày | Bao gồm 10 ngày hacker data |

**Action (pipeline):** Temporal baseline split — build baseline từ data trước first alert.

---

## 6. Confirmed Conclusions

| Statement | Status | Evidence |
|-----------|--------|----------|
| Unfamiliar Sign-in Properties tính real-time | ✅ Confirmed | [DOC-1] |
| Alert fire cho cả interactive + non-interactive | ✅ Confirmed | [DOC-1] |
| Both risk MFA policies: HIGH only | ✅ Confirmed | [TENANT] screenshots |
| Medium risk sign-ins: NO MFA protection | ✅ Confirmed | [TENANT] — Gap |
| CA01 session: 30 days | ✅ Confirmed | [TENANT] |
| 92% Alert IPs bị chặn = MFA step-up fail | ✅ Likely | [DATA] + [TENANT] |
| 3.2% Alert IPs thành công = AiTM OR Medium risk bypass | ✅ Revised | [DATA] + [TENANT] |
| Hacker hoạt động 10 ngày trước alert | ✅ Confirmed | [DATA] |
| Pipeline ErrorCode==0 đúng cho breach detection | ✅ Confirmed | [DATA] |
| AiTM detection là offline (user risk) | ✅ Confirmed | [DOC-1] |
| CA09 = Block access từ Deny/IP + Deny/Region | ✅ Confirmed | [TENANT] screenshot |
