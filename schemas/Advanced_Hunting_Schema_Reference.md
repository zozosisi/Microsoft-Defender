# Microsoft Defender XDR — Advanced Hunting Schema Reference

> **Tenant:** Crystal Group (crystal-martin.com / crystal-abl.com.bd / crystal-cet.com.bd)
> **Cập nhật:** 2026-05-07 — Đã xác nhận từ portal thực tế
> **Nguồn:** Screenshot schema tab + Microsoft Learn Documentation

---

## Tổng Quan Tenant

### ✅ Services Đã Deploy
- Microsoft Entra ID P2 (Identity Protection)
- Microsoft Defender for Cloud Apps
- Microsoft Defender for Office 365
- Microsoft Defender for Identity (partial — IdentityLogonEvents, IdentityInfo có)
- Defender Vulnerability Management
- Exposure Management

### ❌ Services Chưa Deploy / Chưa Onboard
- **Microsoft Defender for Endpoint** — Không có Device tables (DeviceInfo, DeviceEvents, DeviceProcessEvents...)
- **Defender for Identity (full)** — Thiếu IdentityDirectoryEvents, IdentityQueryEvents, IdentityEvents
- **UEBA (Microsoft Sentinel)** — Một số cột UEBA trong IdentityInfo sẽ trống

---

## Danh Sách Tables Available (37 tables)

### 1. Alerts & Behaviors (4 tables)

| # | Table | Mô tả |
|---|-------|--------|
| 1 | `AlertEvidence` | Evidence liên kết với alerts (files, IPs, users, devices) |
| 2 | `AlertInfo` | Alert metadata (title, severity, category) |
| 3 | `BehaviorEntities` | Entities liên quan đến UEBA behaviors |
| 4 | `BehaviorInfo` | UEBA behavior detections |

### 2. Apps & Identities (10 tables)

| # | Table | Mô tả | Ghi chú |
|---|-------|--------|---------|
| 5 | `AADSignInEventsBeta` | Sign-in events (legacy) | ⚠️ Deprecated — dùng EntraIdSignInEvents |
| 6 | `AADSpnSignInEventsBeta` | SPN sign-in events (legacy) | ⚠️ Deprecated |
| 7 | `CloudAppEvents` | Cloud app activity events | Có ISP, CountryCode |
| 8 | `EntraIdSignInEvents` | Sign-in events (current) | **PRIMARY cho investigation** |
| 9 | `EntraIdSpnSignInEvents` | Service Principal sign-ins | |
| 10 | `GraphAPIAuditEvents` | Microsoft Graph API audit | |
| 11 | `IdentityAccountInfo` | Account info from identity services | |
| 12 | `IdentityInfo` | User account details | Có RiskLevel, Department |
| 13 | `IdentityLogonEvents` | On-prem AD + Cloud auth events | **Có ISP, Location** |
| 14 | `OAuthAppInfo` | OAuth application info | |

### 3. Email & Collaboration (8 tables)

| # | Table | Mô tả |
|---|-------|--------|
| 15 | `EmailAttachmentInfo` | Email attachment metadata |
| 16 | `EmailEvents` | Email processing events |
| 17 | `EmailPostDeliveryEvents` | Post-delivery actions (ZAP, purge...) |
| 18 | `EmailUrlInfo` | URLs trong emails |
| 19 | `MessageEvents` | Teams/Copilot message events |
| 20 | `MessagePostDeliveryEvents` | Post-delivery message actions |
| 21 | `MessageUrlInfo` | URLs trong messages |
| 22 | `UrlClickEvents` | Safe Links click events |

### 4. Defender Vulnerability Management (8 tables)

| # | Table | Mô tả |
|---|-------|--------|
| 23 | `DeviceTvmInfoGathering` | TVM info gathering events |
| 24 | `DeviceTvmInfoGatheringKB` | Info gathering knowledge base |
| 25 | `DeviceTvmSecureConfigurationAssessment` | Security config assessment |
| 26 | `DeviceTvmSecureConfigurationAssessmentKB` | Config assessment KB |
| 27 | `DeviceTvmSoftwareEvidenceBeta` | Software evidence (Preview) |
| 28 | `DeviceTvmSoftwareInventory` | Software inventory |
| 29 | `DeviceTvmSoftwareVulnerabilities` | Software vulnerabilities |
| 30 | `DeviceTvmSoftwareVulnerabilitiesKB` | Vulnerability KB |

### 5. Cloud Infrastructure (4 tables)

| # | Table | Mô tả |
|---|-------|--------|
| 31 | `CloudAuditEvents` | Cloud resource audit events |
| 32 | `CloudDnsEvents` | Cloud DNS events |
| 33 | `CloudProcessEvents` | Cloud workload process events |
| 34 | `CloudStorageAggregatedEvents` | Cloud storage events |

### 6. Exposure Management (2 tables)

| # | Table | Mô tả |
|---|-------|--------|
| 35 | `ExposureGraphEdges` | Exposure graph edges |
| 36 | `ExposureGraphNodes` | Exposure graph nodes |

### 7. Other

| # | Table | Mô tả |
|---|-------|--------|
| 37 | `GraphAPIAuditEvents` | Graph API audit events |

---

## Chi Tiết Schema — Tables Quan Trọng Cho Investigation

---

### ★ EntraIdSignInEvents — Sign-in Events (PRIMARY)

> **Dùng cho:** Phân tích sign-in patterns, IP/Country, device info, risk level
> **License:** Entra ID P2

| Column | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Thời điểm sign-in | |
| `Application` | string | App được truy cập (e.g., "Office 365 Exchange Online") | |
| `ApplicationId` | string | App ID | |
| `LogonType` | string | Interactive, NonInteractive, ServicePrincipal | |
| `ErrorCode` | int | 0 = success. Ref: aka.ms/AADsigninsErrorCodes | ⭐ |
| `CorrelationId` | string | Correlation ID để trace sign-in flow | |
| `SessionId` | string | Session identifier | ⭐ |
| `AccountDisplayName` | string | Tên hiển thị user | |
| `AccountObjectId` | string | Object ID trong Entra ID | |
| `AccountUpn` | string | User Principal Name (email) | ⭐ |
| `IsConfidentialClient` | boolean | Confidential client? | |
| `IsExternalUser` | int | External user? | |
| `IsGuestUser` | boolean | Guest user? | |
| `AlternateSignInName` | string | Alternate sign-in name | |
| `LastPasswordChangeTimestamp` | datetime | Lần đổi password gần nhất | ⭐ |
| `ResourceDisplayName` | string | Resource được truy cập | |
| `ResourceId` | string | Resource ID | |
| `ResourceTenantId` | string | Resource tenant ID | |
| `DeviceName` | string | Tên device | ⭐ |
| `EntraIdDeviceId` | string | Device ID trong Entra ID | |
| `OSPlatform` | string | OS (Windows, iOS, Android...) | ⭐ |
| `DeviceTrustType` | string | AzureAD Joined, Hybrid... | ⭐ |
| `IsManaged` | int | Intune managed? | ⭐ |
| `IsCompliant` | int | Device compliant? | ⭐ |
| `AuthenticationProcessingDetails` | string | Authentication details | |
| `AuthenticationRequirement` | string | MFA requirement | ⭐ |
| `TokenIssuerType` | int | Token issuer type | |
| `RiskLevelAggregated` | int | Aggregated risk level (0/10/50/100) | ⭐ |
| `RiskDetails` | int | Risk detail code | |
| `RiskState` | int | Risk state | ⭐ |
| `UserAgent` | string | User-Agent string đầy đủ | ⭐ |
| `ClientAppUsed` | string | Browser, Mobile Apps, Desktop... | ⭐ |
| `Browser` | string | Chrome, Edge, Safari... | ⭐ |
| `ConditionalAccessPolicies` | string | CA policies đã áp dụng (JSON) | ⭐ |
| `ConditionalAccessStatus` | int | CA result | |
| `IPAddress` | string | Source IP | ⭐⭐ |
| `Country` | string | Country code (BD, VN, US...) | ⭐⭐ |
| `State` | string | State/Province | |
| `City` | string | City | ⭐ |
| `Latitude` | string | Latitude | |
| `Longitude` | string | Longitude | |
| `NetworkLocationDetails` | string | Network location details | |
| `RequestId` | string | Request ID | |
| `ReportId` | string | Report ID | |
| `EndpointCall` | string | Endpoint called | |

> ⚠️ **KHÔNG CÓ:** `ASN`, `Isp` — dùng `IdentityLogonEvents` hoặc `CloudAppEvents` thay thế

---

### ★ IdentityLogonEvents — On-prem AD + Cloud Auth

> **Dùng cho:** Lấy ISP info, on-prem auth, protocol-level analysis
> **Đặc biệt:** Có cột `Isp` và `Location` mà EntraIdSignInEvents KHÔNG có

| Column | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Event time | |
| `ActionType` | string | LogonSuccess, LogonFailed... | ⭐ |
| `Application` | string | App thực hiện auth | |
| `LogonType` | string | Interactive, RemoteInteractive, Network, Service | ⭐ |
| `Protocol` | string | NTLM, Kerberos, OAuth2... | ⭐ |
| `FailureReason` | string | Failure reason | |
| `AccountName` | string | Account name | |
| `AccountDomain` | string | Domain | |
| `AccountUpn` | string | UPN (email) | ⭐ |
| `AccountSid` | string | SID | |
| `AccountObjectId` | string | Object ID | |
| `AccountDisplayName` | string | Display name | |
| `DeviceName` | string | Device name | |
| `DeviceType` | string | Device type | |
| `OSPlatform` | string | OS | |
| `IPAddress` | string | Source IP | ⭐⭐ |
| `Port` | int | Source port | |
| `DestinationDeviceName` | string | Target device | |
| `DestinationIPAddress` | string | Target IP | |
| `DestinationPort` | int | Target port | |
| `TargetDeviceName` | string | Target device | |
| `TargetAccountDisplayName` | string | Target account | |
| `Location` | string | Geographic location | ⭐⭐ |
| `Isp` | string | **ISP name** | ⭐⭐⭐ |
| `ReportId` | string | Report ID | |
| `AdditionalFields` | dynamic | Additional data (JSON) | |

---

### ★ IdentityInfo — User Account Details

> **Dùng cho:** Enrich user data — department, risk level, roles, account status

| Column | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Record time | |
| `AccountObjectId` | string | Object ID | ⭐ |
| `AccountUpn` | string | UPN | ⭐ |
| `OnPremSid` | string | On-prem SID | |
| `AccountDisplayName` | string | Display name | |
| `AccountName` | string | Account name | |
| `AccountDomain` | string | Domain | |
| `CriticalityLevel` | int | Criticality | |
| `Type` | string | Account type | |
| `CloudSid` | string | Cloud SID | |
| `GivenName` | string | First name | |
| `Surname` | string | Last name | |
| `Department` | string | Department | ⭐ |
| `JobTitle` | string | Job title | |
| `EmailAddress` | string | Email | |
| `City` | string | City | |
| `Country` | string | Country | |
| `IsAccountEnabled` | boolean | Account enabled? | ⭐ |
| `Manager` | string | Manager | |
| `CreatedDateTime` | datetime | Account creation | |
| `RiskLevel` | string | Risk level | ⭐⭐ |
| `RiskLevelDetails` | string | Risk details | |
| `RiskStatus` | string | Risk status | ⭐⭐ |
| `Tags` | dynamic | Tags | |
| `AssignedRoles` | dynamic | Assigned roles | ⭐ |
| `TenantId` | string | Tenant ID | |
| `OnPremObjectId` | string | On-prem Object ID | |
| `TenantMembershipType` | string | Member/Guest | |
| `UserAccountControl` | string | UAC flags | |
| `IdentityEnvironment` | string | Cloud/On-Prem/Hybrid | ⭐ |
| `SourceProviders` | dynamic | Source providers | |

---

### ★ AlertInfo — Alert Metadata

| Column | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Alert time | |
| `AlertId` | string | Unique alert ID — JOIN key | ⭐⭐ |
| `Title` | string | Alert title | ⭐ |
| `Category` | string | MITRE category | ⭐ |
| `Severity` | string | Informational/Low/Medium/High | ⭐ |
| `ServiceSource` | string | Service tạo alert | |
| `DetectionSource` | string | Detection source | |
| `AttackTechniques` | string | MITRE ATT&CK techniques | |

---

### ★ AlertEvidence — Evidence Liên Kết Alert

| Column | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Evidence time | |
| `AlertId` | string | JOIN key với AlertInfo | ⭐⭐ |
| `Title` | string | Alert title | |
| `Categories` | string | Categories | |
| `AttackTechniques` | string | MITRE techniques | |
| `ServiceSource` | string | Service source | |
| `DetectionSource` | string | Detection source | |
| `EntityType` | string | Account, Ip, Url, File... | ⭐⭐ |
| `EvidenceRole` | string | Impacted, Related | ⭐ |
| `EvidenceDirection` | string | Direction | |
| `FileName` | string | File name | |
| `FolderPath` | string | File path | |
| `SHA1` | string | SHA1 hash | |
| `SHA256` | string | SHA256 hash | |
| `FileSize` | long | File size | |
| `ThreatFamily` | string | Malware family | |
| `RemoteIP` | string | Remote IP | ⭐⭐ |
| `RemoteUrl` | string | Remote URL | |
| `AccountName` | string | Account name | ⭐ |
| `AccountDomain` | string | Account domain | |
| `AccountSid` | string | SID | |
| `AccountObjectId` | string | Object ID | ⭐ |
| `AccountUpn` | string | Account UPN | ⭐ |
| `DeviceId` | string | Device ID | |
| `DeviceName` | string | Device name | |
| `LocalIP` | string | Local IP | |
| `NetworkMessageId` | string | Email message ID | |
| `EmailSubject` | string | Email subject | |
| `Application` | string | Application | |
| `ApplicationId` | int | Application ID | |
| `OAuthApplicationId` | string | OAuth App ID | ⭐ |
| `ProcessCommandLine` | string | Process command line | |
| `AdditionalFields` | string | Additional fields (JSON) | |
| `Severity` | string | Severity | |

---

### ★ CloudAppEvents — Cloud App Activity

> **Đặc biệt:** Có `ISP` và `CountryCode` — bổ sung cho EntraIdSignInEvents

| Column (chính) | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Event time | |
| `ActionType` | string | Action type | |
| `Application` | string | App name | |
| `ActivityType` | string | Activity type | |
| `AccountObjectId` | string | Account Object ID | ⭐ |
| `AccountDisplayName` | string | Display name | |
| `IPAddress` | string | IP address | ⭐⭐ |
| `IsAdminOperation` | boolean | Admin operation? | ⭐ |
| `DeviceType` | string | Device type | |
| `OSPlatform` | string | OS | |
| `City` | string | City | |
| `CountryCode` | string | Country code | ⭐⭐ |
| `ISP` | string | **ISP name** | ⭐⭐⭐ |
| `UserAgent` | string | User-Agent | ⭐ |
| `ActivityObjects` | dynamic | Activity details | |
| `RawEventData` | dynamic | Raw event data | |

---

### ★ EmailEvents — Email Processing

| Column (chính) | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Email event time | |
| `NetworkMessageId` | string | JOIN key cho EmailUrlInfo | ⭐⭐ |
| `InternetMessageId` | string | Internet message ID | |
| `SenderMailFromAddress` | string | SMTP MAIL FROM | ⭐ |
| `SenderFromAddress` | string | From header | ⭐ |
| `SenderDisplayName` | string | Sender name | |
| `SenderFromDomain` | string | Sender domain | ⭐ |
| `SenderIPv4` | string | Sender IP | |
| `RecipientEmailAddress` | string | Recipient email | ⭐⭐ |
| `Subject` | string | Email subject | ⭐ |
| `EmailDirection` | string | Inbound/Outbound/Intra-org | ⭐ |
| `DeliveryAction` | string | Delivered/Blocked | ⭐ |
| `DeliveryLocation` | string | Inbox/Junk/Quarantine | |
| `ThreatTypes` | string | Phish/Malware... | ⭐⭐ |
| `ThreatNames` | string | Threat names | |
| `DetectionMethods` | string | Detection methods | |
| `AuthenticationDetails` | string | SPF/DKIM/DMARC | ⭐ |
| `AttachmentCount` | int | Attachment count | |
| `UrlCount` | int | URL count | ⭐ |

---

### ★ EmailUrlInfo — URLs Trong Email

| Column | Type | Mô tả | Quan trọng |
|--------|------|--------|------------|
| `Timestamp` | datetime | Event time | |
| `NetworkMessageId` | string | JOIN key với EmailEvents | ⭐⭐ |
| `Url` | string | URL trong email | ⭐⭐ |
| `UrlDomain` | string | URL domain | ⭐ |
| `UrlLocation` | string | Body/Header | |
| `ReportId` | string | Report ID | |

---

## JOIN Relationships

```
AlertInfo.AlertId ←→ AlertEvidence.AlertId
EmailEvents.NetworkMessageId ←→ EmailUrlInfo.NetworkMessageId
EmailEvents.NetworkMessageId ←→ EmailAttachmentInfo.NetworkMessageId
EntraIdSignInEvents.AccountObjectId ←→ IdentityInfo.AccountObjectId
EntraIdSignInEvents.AccountUpn ←→ IdentityLogonEvents.AccountUpn
AlertEvidence.AccountObjectId ←→ IdentityInfo.AccountObjectId
EmailEvents.RecipientEmailAddress ←→ IdentityInfo.EmailAddress
```

---

## KQL Queries Xác Nhận Schema

```kql
// Chạy từng query để xác nhận columns thực tế:
EntraIdSignInEvents | getschema | project ColumnName, ColumnType, DataType
IdentityLogonEvents | getschema | project ColumnName, ColumnType, DataType
IdentityInfo | getschema | project ColumnName, ColumnType, DataType
AlertInfo | getschema | project ColumnName, ColumnType, DataType
AlertEvidence | getschema | project ColumnName, ColumnType, DataType
CloudAppEvents | getschema | project ColumnName, ColumnType, DataType
EmailEvents | getschema | project ColumnName, ColumnType, DataType
EmailUrlInfo | getschema | project ColumnName, ColumnType, DataType
```

---

## Lưu Ý Quan Trọng

> ⚠️ `EntraIdSignInEvents` **KHÔNG CÓ** cột `ASN` hay `Isp`. Dùng `IdentityLogonEvents.Isp` hoặc `CloudAppEvents.ISP` thay thế.

> ⚠️ `EntraIdSignInEvents` dùng `Country` (string). `CloudAppEvents` dùng `CountryCode` (string). Tên cột khác nhau.

> ⚠️ `RiskLevelAggregated` trong `EntraIdSignInEvents` là kiểu `int`: 0=None, 10=Low, 50=Medium, 100=High.

> ⚠️ Tenant **không có Device tables** (DeviceInfo, DeviceEvents...) — không thể trace endpoint activity. Investigation giới hạn ở tầng Identity + Email + Cloud.

> ⚠️ Cả `AADSignInEventsBeta` và `EntraIdSignInEvents` đều available — ưu tiên dùng `EntraIdSignInEvents`.
