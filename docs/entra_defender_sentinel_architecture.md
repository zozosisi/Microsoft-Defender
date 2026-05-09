# Microsoft Security Platform Architecture: Entra ID ↔ Defender XDR ↔ Sentinel

> **Cập nhật:** 09-May-2026  
> **Mục đích:** Hiểu mối quan hệ giữa 3 nền tảng bảo mật và cách chúng hoạt động cùng nhau  

> [!IMPORTANT]
> **Source Attribution:**
> - Các phần đánh dấu `📘 MS LEARN` chứa nội dung trích dẫn/tóm tắt từ Microsoft Learn chính thức.
> - Các phần đánh dấu `📊 INTERNAL` là phân tích/diễn giải nội bộ của Crystal Group SOC team, KHÔNG phải tài liệu Microsoft.
> - Diagrams và signal flow là do SOC team tự tạo dựa trên kiến trúc thực tế.

---

## 1. Tổng Quan Kiến Trúc `📊 INTERNAL`

```
┌──────────────────────────────────────────────────────────────────────┐
│                    MICROSOFT UNIFIED SECURITY PLATFORM              │
│                                                                      │
│  ┌────────────────┐   ┌──────────────────┐   ┌───────────────────┐  │
│  │  ENTRA ID      │   │  DEFENDER XDR    │   │  SENTINEL         │  │
│  │  PROTECTION    │   │  (Extended       │   │  (SIEM/SOAR)      │  │
│  │                │   │   Detection &    │   │                   │  │
│  │  Signal Source │──▶│   Response)      │──▶│  Correlation &    │  │
│  │  Identity Risk │   │                  │   │  Automation       │  │
│  │                │   │  Alert Engine    │   │                   │  │
│  └────────────────┘   └──────────────────┘   └───────────────────┘  │
│         ▲                      ▲                      ▲              │
│         │                      │                      │              │
│  ┌──────┴──────┐  ┌───────────┴──────────┐  ┌────────┴──────────┐  │
│  │ Conditional │  │ Defender for:         │  │ 3rd Party Data    │  │
│  │ Access      │  │ • Identity (on-prem) │  │ • Firewall logs   │  │
│  │ (Enforce)   │  │ • Cloud Apps         │  │ • CASB            │  │
│  │             │  │ • Office 365         │  │ • Custom apps     │  │
│  │             │  │ • Endpoint           │  │ • Multi-cloud     │  │
│  └─────────────┘  └────────────────────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Entra ID Protection — Signal Source `📘 MS LEARN` + `📊 INTERNAL`

### Vai trò
Entra ID Protection là **hệ thống ML** đánh giá rủi ro cho mỗi sign-in và mỗi user. Nó **KHÔNG chặn** — chỉ tạo tín hiệu risk level.

### Cách hoạt động

```
User Sign-in Request
       │
       ▼
┌──────────────────────────────┐
│  ENTRA ID ML RISK ENGINE    │
│                              │
│  Phân tích:                  │
│  • IP Address / ASN          │
│  • Location (Geo)            │
│  • Device fingerprint        │
│  • Browser                   │
│  • Tenant IP Subnet          │
│  • Thời gian đăng nhập       │
│                              │
│  So sánh với Baseline        │
│  (14 ngày hoặc 10 logins)    │
│                              │
│  Output: Risk Level          │
│  • None (0)                  │
│  • Low (10)                  │
│  • Medium (50)               │
│  • High (100)                │
└──────────┬───────────────────┘
           │
           ▼
    2 loại risk output:
    ┌─────────────────┐   ┌─────────────────┐
    │ SIGN-IN RISK    │   │ USER RISK       │
    │ (Real-time)     │   │ (Aggregated)    │
    │                 │   │                 │
    │ "Phiên này có   │   │ "User này có    │
    │  bị compromise  │   │  khả năng đã    │
    │  không?"        │   │  bị compromise" │
    └────────┬────────┘   └────────┬────────┘
             │                     │
             ▼                     ▼
      Conditional Access     Conditional Access
      (Real-time enforce)    (Block until remediate)
```

### Risk Detection Types (từ Microsoft Learn)

#### Sign-in Risk Detections (Real-time)

| Detection | Mô tả | Risk Level | License |
|-----------|--------|-----------|---------|
| **Unfamiliar sign-in properties** | IP/ASN/Location/Device/Browser lạ so với baseline | Medium | P2 |
| **Anonymous IP address** | Sign-in từ Tor/Anonymous VPN | Medium | Free |
| **Anomalous Token** | Token có lifetime bất thường hoặc từ location lạ | Medium-High | P2 |
| **Malicious IP address** | IP có lịch sử tấn công | High | P2 |
| **Verified threat actor IP** | IP liên quan đến nhóm APT/cybercrime (MSTIC) | High | P2 |
| **Suspicious MFA approval** | MFA approve từ location khác request | High | P2 |
| **Password spray** | Brute-force nhiều users cùng 1 password | High | P2 |

#### User Risk Detections (Offline)

| Detection | Mô tả | Risk Level | License |
|-----------|--------|-----------|---------|
| **Leaked credentials** | Password xuất hiện trên dark web (MSTIC + DCU) | High | Free |
| **Attacker in the Middle (AiTM)** | Phát hiện reverse proxy steal token | High | E5 |
| **Anomalous user activity** | Thay đổi directory bất thường | Medium | P2 |
| **Suspicious inbox forwarding** | Tạo rule forward email ra ngoài | Medium | P2 + MCAS |
| **Suspicious inbox manipulation** | Rule xóa/di chuyển email | Medium | P2 + MCAS |
| **Mass access to sensitive files** | Download hàng loạt file SharePoint/OneDrive | Medium | P2 + MCAS |

> **Lưu ý:** Nhiều detections cần **Defender for Cloud Apps (MCAS)** cung cấp data. Nếu không có MCAS → detection không hoạt động.

> **Source:** [What are risk detections? — Microsoft Learn](https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-risks)

---

## 3. Conditional Access — Enforcement Layer `📘 MS LEARN` + `📊 INTERNAL`

### Vai trò
CA **KHÔNG phát hiện threat** — nó chỉ **thực thi chính sách** dựa trên tín hiệu từ Entra ID Protection.

```
Entra ID Protection      Conditional Access         User Experience
(Risk Signal)            (Policy Engine)            (Impact)
─────────────           ────────────────           ────────────────
Risk = None     ───▶    Allow                 ───▶  Đăng nhập bình thường
Risk = Low      ───▶    Allow (or MFA)        ───▶  Có thể yêu cầu MFA
Risk = Medium   ───▶    ??? (TÙY CẤU HÌNH)   ───▶  MFA hoặc Block
Risk = High     ───▶    Require MFA + Reauth  ───▶  Bắt buộc MFA mới
```

### Tenant hiện tại (Crystal Group) `📊 INTERNAL`

| Policy | Scope | Sign-in Risk | Action |
|--------|-------|:---:|--------|
| Multifactor authentication for risky sign-ins | All users | **High only** | MFA + Reauth |
| Per-user MFA | 25 users | N/A (Off) | N/A |
| Custom: Require MFA for risky sign-ins | All users (Report-only) | **High only** | MFA + Reauth |

> **⚠️ GAP:** Medium risk KHÔNG được cover → 994 medium-risk sign-ins lọt qua không cần MFA.

### Recommended Layered Approach `📊 INTERNAL`

| Sign-in Risk | Compliant Device | Non-compliant Device |
|:---:|:---:|:---:|
| **High** | Block | Block |
| **Medium** | ✅ Allow | 🔐 Require MFA |
| **Low/None** | ✅ Allow | ✅ Allow |

**Rationale:** Nhân viên dùng laptop công ty → device compliant → bypass MFA (0 friction). Hacker AiTM → token không có device compliance claim → bị chặn.

---

## 4. Defender XDR — Alert & Correlation Engine `📘 MS LEARN` + `📊 INTERNAL`

### Vai trò
Defender XDR nhận tín hiệu từ **nhiều Defender products** và gộp thành **Incidents** (giảm alert fatigue).

### Signal Sources

```
┌──────────────────────────────────────────────────────┐
│                 DEFENDER XDR                          │
│                                                      │
│   Defender for Identity ──┐                          │
│   (On-prem AD logs)       │                          │
│                           │    ┌──────────────────┐  │
│   Defender for Cloud ─────┼──▶ │   INCIDENT       │  │
│   Apps (CloudAppEvents)   │    │   CORRELATION    │  │
│                           │    │   ENGINE (AI)    │  │
│   Defender for Office ────┤    │                  │  │
│   365 (Email threats)     │    │   Alerts ──▶     │  │
│                           │    │   Incidents      │  │
│   Defender for Endpoint ──┤    │   (Grouped)      │  │
│   (Device telemetry)  ❌  │    └──────────────────┘  │
│                           │                          │
│   Entra ID Protection ────┘                          │
│   (Risk detections)                                  │
└──────────────────────────────────────────────────────┘
```

### Cách Entra ID Protection feed vào Defender XDR

1. **Entra ID Protection** detect "Unfamiliar sign-in properties" → tạo **Risk Detection**
2. Risk Detection → trở thành **Alert** trong Defender XDR (Title: "Unfamiliar sign-in properties")
3. Defender XDR AI → gộp nhiều alerts liên quan thành **Incident** (ví dụ: 1 incident chứa 40 alerts cho cùng 1 user)
4. SOC analyst → xử lý **Incident** (không phải từng alert riêng)

### Bảng Data Tables trong Advanced Hunting

| Table | Source | Chứa gì |
|-------|--------|---------|
| `EntraIdSignInEvents` | Entra ID | Sign-in logs (IP, Country, Device, RiskLevel) |
| `IdentityLogonEvents` | Defender for Identity | On-prem + cloud logon (có ISP) |
| `IdentityInfo` | Defender for Identity | User profiles, roles, MFA |
| `AlertInfo` / `AlertEvidence` | Defender XDR | Alert metadata + evidence |
| `CloudAppEvents` | Defender for Cloud Apps | User actions (FileDownloaded, MailItemsAccessed) |
| `EmailEvents` | Defender for Office 365 | Email threat data |

### Hạn chế: Defender XDR KHÔNG tự động correlate sign-in risk với data access `📊 INTERNAL`

```
Entra ID Protection          Defender for Cloud Apps
"IP 1.2.3.4 is risky"       "User downloaded 230 files from IP 1.2.3.4"
         │                              │
         │    ❌ KHÔNG TỰ ĐỘNG         │
         │    CORRELATE               │
         └──────────────────────────────┘
         
         Pipeline Python của chúng ta LÀM VIỆC NÀY ✅
```

**Lý do:** Mỗi Defender product hoạt động trong **silo riêng**:
- Entra ID cảnh báo "IP lạ đăng nhập" (sign-in layer)
- Cloud Apps ghi nhận "user download file" (application layer)
- Nhưng **không ai nối 2 sự kiện lại** để nói "hacker dùng IP lạ để steal data"

**Giải pháp:** Microsoft Sentinel (xem Section 5).

---

## 5. Microsoft Sentinel — SIEM/SOAR (Correlation & Automation) `📘 MS LEARN` + `📊 INTERNAL`

### Vai trò
Sentinel là **missing piece** — nền tảng SIEM/SOAR correlate TẤT CẢ signals và tự động hóa response.

### Signal Flow đầy đủ (khi có Sentinel)

```
┌─────────────────┐
│ Entra ID        │──▶ Risk Detection: "Unfamiliar sign-in from IP 1.2.3.4"
│ Protection      │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Defender XDR    │──▶ Incident: "Unfamiliar Sign-in Properties"
│                 │    Alert gộp từ Entra ID
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ SENTINEL        │──▶ Analytics Rule: "Sign-in risk + Data access from same IP"
│ (SIEM/SOAR)     │
│                 │    KQL: EntraIdSignInEvents
│                 │    | where RiskLevelDuringSignIn >= 50
│                 │    | join CloudAppEvents on IPAddress
│                 │    | where ActionType in ("FileDownloaded", "MailItemsAccessed")
│                 │
│                 │──▶ Output: "🚨 DATA BREACH: User X downloaded 230 files
│                 │              from risky IP 1.2.3.4"
│                 │
│                 │──▶ Playbook (SOAR):
│                 │    1. Disable user account
│                 │    2. Revoke all sessions
│                 │    3. Isolate device (if MDE available)
│                 │    4. Notify SOC team
│                 │    5. Create ticket
└─────────────────┘
```

### Tại sao Sentinel giải quyết được vấn đề?

| Capability | Defender XDR (hiện tại) | + Sentinel |
|-----------|:-:|:-:|
| Sign-in risk detection | ✅ | ✅ |
| File download logging | ✅ | ✅ |
| **Cross-correlate sign-in risk + file access** | ❌ | ✅ |
| Custom detection rules (KQL) | ⚠️ Limited | ✅ Full |
| Automated response (SOAR) | ⚠️ Basic | ✅ Playbooks |
| Third-party data correlation | ❌ | ✅ |
| Long-term log retention | 30 days | ✅ Configurable |
| Advanced hunting across all data | ✅ | ✅ + more |

### Sentinel Onboarding (Unified Portal)

Từ 2024, Microsoft hỗ trợ **Unified Security Operations Platform** — Sentinel tích hợp trực tiếp trong Defender portal:

```
Defender Portal (security.microsoft.com)
├── Incidents & Alerts      ← Unified queue (XDR + Sentinel)
├── Advanced Hunting        ← KQL across all tables
├── Custom Detection Rules  ← Sentinel Analytics Rules
├── Automation              ← Playbooks (Logic Apps)
└── Reports & Workbooks     ← Sentinel Workbooks
```

**Yêu cầu:**
- Azure subscription + Log Analytics workspace
- Microsoft Sentinel resource
- Connector: Microsoft Defender XDR (auto-sync incidents)

> **Source:** [Connect Microsoft Sentinel to the Defender portal — Microsoft Learn](https://learn.microsoft.com/en-us/defender-xdr/microsoft-sentinel-onboard)

---

## 6. Tổng Hợp: Signal Flow End-to-End `📊 INTERNAL`

```
PHASE 1: DETECTION (Phát hiện)
════════════════════════════════
   User Sign-in
       │
       ▼
   Entra ID ML ──▶ Risk Level: Medium
       │
       ▼
   Conditional Access ──▶ Policy check
       │                  (High only → BYPASS ⚠️)
       ▼
   Sign-in SUCCESS ──▶ EntraIdSignInEvents table

PHASE 2: POST-AUTHENTICATION ACTIVITY
══════════════════════════════════════
   Hacker (with stolen token)
       │
       ├──▶ MailItemsAccessed ──▶ CloudAppEvents
       ├──▶ FileDownloaded    ──▶ CloudAppEvents
       └──▶ New-InboxRule     ──▶ CloudAppEvents

PHASE 3: ALERTING
══════════════════
   Entra ID ──▶ Alert: "Unfamiliar sign-in" ──▶ Defender XDR Incident
   Cloud Apps ──▶ (No alert — actions look normal) ❌

PHASE 4: CORRELATION (CHỈ CÓ KHI CÓ SENTINEL HOẶC CUSTOM PIPELINE)
═══════════════════════════════════════════════════════════════════
   Option A: Sentinel Analytics Rule (auto)
   Option B: Python Pipeline (chúng ta) ← ĐANG DÙNG
   
   "IP 1.2.3.4 triggered risk alert AND downloaded 230 files"
   → 🚨 CONFIRMED DATA BREACH
```

---

## 7. Áp Dụng Cho Crystal Group `📊 INTERNAL`

### Hiện trạng

| Component | Status | Impact |
|-----------|--------|--------|
| Entra ID P2 | ✅ Active | Risk detections hoạt động |
| Defender for Cloud Apps | ✅ Active | CloudAppEvents có data |
| Defender for Office 365 | ✅ Active | Email threat data |
| Defender for Identity | ⚠️ Partial | IdentityLogonEvents có, ISP có |
| **Defender for Endpoint** | ❌ Missing | Không có device telemetry |
| **Microsoft Sentinel** | ❌ Missing | Không có auto-correlation |
| CA Policy | ⚠️ High only | Medium risk bypass MFA |

### Hậu quả

Vì **thiếu Sentinel** và **thiếu Defender for Endpoint**:
1. 295 "Unfamiliar sign-in" alerts được tạo ✅
2. Nhưng **không ai** auto-correlate với CloudAppEvents ❌
3. 10 users bị data breach mà Defender **không alert** ❌
4. Pipeline Python của chúng ta **thay thế vai trò Sentinel** bằng manual correlation ✅

### Khuyến nghị theo thứ tự ưu tiên

| # | Action | Cost | Value |
|---|--------|------|-------|
| 1 | **CA Policy: Medium + Non-compliant → MFA** | Free | Chặn hacker không có device |
| 2 | **Deploy Microsoft Sentinel** | ~$2-5/GB/day | Auto-correlate + SOAR |
| 3 | **Sentinel Analytics Rule** cho Data Breach | Free (after Sentinel) | Phát hiện breach real-time |
| 4 | **Deploy Defender for Endpoint** | E5 license | Device-level visibility |
| 5 | **Reduce session lifetime** (CAE) | Free | Thu hẹp AiTM window |

---

## References (Microsoft Learn — Verified)

| Document | URL |
|----------|-----|
| What are risk detections? | https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-risks |
| Risk-based Conditional Access policies | https://learn.microsoft.com/en-us/entra/id-protection/concept-identity-protection-policies |
| Investigate risk | https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-investigate-risk |
| Defender XDR + Sentinel integration | https://learn.microsoft.com/en-us/defender-xdr/microsoft-365-defender-integration-with-azure-sentinel |
| Connect Sentinel to Defender portal | https://learn.microsoft.com/en-us/defender-xdr/microsoft-sentinel-onboard |
