# Microsoft Defender XDR — Investigation & Schema Reference

> **Tenant:** Crystal Group (crystal-martin.com / crystal-abl.com.bd / crystal-cet.com.bd)  
> **Last Updated:** 2026-05-07  
> **Purpose:** Tài liệu hóa schema, phân tích incidents, và hỗ trợ điều tra bảo mật trên Microsoft Defender XDR

---

## 📋 Tổng Quan

Repository này chứa toàn bộ tài liệu kỹ thuật phục vụ công tác **điều tra bảo mật (Security Investigation)** trên nền tảng Microsoft Defender XDR cho Crystal Group, bao gồm:

- Schema reference đầy đủ từ Advanced Hunting (35/36 tables)
- Phân tích incident "Unfamiliar Sign-in Properties" (295 incidents, 55 risky users)
- Dữ liệu Risky Users và Incidents Queue
- KQL queries mẫu cho điều tra

---

## 🏗️ Cấu Trúc Project

```
Microsoft-Defender/
│
├── README.md                                  ← File này
│
├── schemas/                                   ← Schema reference & raw data
│   ├── Complete_Schema_Reference.md           ← Schema đầy đủ 35 tables (auto-generated)
│   ├── Advanced_Hunting_Schema_Reference.md   ← Schema reference gốc (hand-written)
│   ├── All_Schemas_Combined.csv               ← Raw schema data (750 columns, 35 tables)
│   ├── get_all_schemas.kql                    ← KQL queries để export schema từ tenant
│   └── raw/                                   ← Individual CSV exports per table
│       ├── New query (3).csv → (37).csv       ← 35 CSV files từ Advanced Hunting
│
├── incidents/                                 ← Phân tích & dữ liệu incidents
│   ├── analysis_unfamiliar_signin.md          ← Báo cáo phân tích root cause
│   ├── investigation_chat_log.md              ← Full analysis + KQL + IR playbook
│   └── data/
│       ├── risky_users_20260506.csv           ← 55 users At Risk
│       ├── incidents_queue_20260506.csv       ← 295 incidents queue
│       └── entra_id_settings.png              ← Screenshot Identity Protection
│
└── queries/                                   ← KQL queries cho investigation
    └── (sẽ bổ sung)
```

---

## 🔐 Services Đã Deploy

| Service | Status | Ghi chú |
|---------|--------|---------|
| Microsoft Entra ID P2 | ✅ Active | Identity Protection enabled |
| Defender for Cloud Apps | ✅ Active | Có ISP, CountryCode |
| Defender for Office 365 | ✅ Active | Email protection |
| Defender for Identity | ⚠️ Partial | Có IdentityLogonEvents, thiếu DirectoryEvents |
| Vulnerability Management | ✅ Active | 8 DeviceTvm tables |
| Exposure Management | ✅ Active | Graph-based |
| **Defender for Endpoint** | ❌ Missing | Không có Device tables |
| **UEBA (Sentinel)** | ❌ Missing | Một số cột UEBA trống |

---

## 📊 Schema Overview

| Category | Tables | Columns | Tables chính cho Investigation |
|----------|--------|---------|-------------------------------|
| Alerts & Behaviors | 4 | 104 | `AlertInfo`, `AlertEvidence` |
| Apps & Identities | 10 | 329 | `EntraIdSignInEvents`, `IdentityLogonEvents`, `IdentityInfo`, `CloudAppEvents` |
| Email & Collaboration | 8 | 151 | `EmailEvents`, `EmailUrlInfo`, `EmailAttachmentInfo` |
| Vulnerability Management | 8 | 76 | `DeviceTvmSoftwareVulnerabilities` |
| Cloud Infrastructure | 3 | 73 | `CloudAuditEvents` |
| Exposure Management | 2 | 17 | `ExposureGraphNodes` |
| **Total** | **35** | **750** | |

### ❌ Table Chưa Export

| Table | Lý do | KQL Query |
|-------|-------|-----------|
| `CloudProcessEvents` | Chưa export CSV | `CloudProcessEvents \| getschema \| extend TableName = "CloudProcessEvents" \| project TableName, ColumnName, ColumnType, DataType` |

---

## 🔗 JOIN Relationships

```
AlertInfo.AlertId                    ←→  AlertEvidence.AlertId
EmailEvents.NetworkMessageId         ←→  EmailUrlInfo.NetworkMessageId
EmailEvents.NetworkMessageId         ←→  EmailAttachmentInfo.NetworkMessageId
EntraIdSignInEvents.AccountObjectId  ←→  IdentityInfo.AccountObjectId
EntraIdSignInEvents.AccountUpn       ←→  IdentityLogonEvents.AccountUpn
AlertEvidence.AccountObjectId        ←→  IdentityInfo.AccountObjectId
EmailEvents.RecipientEmailAddress    ←→  IdentityInfo.EmailAddress
CloudAppEvents.AccountObjectId       ←→  IdentityInfo.AccountObjectId
```

---

## 🚨 Incident Analysis: Unfamiliar Sign-in Properties

### Tình hình hiện tại

| Metric | Value |
|--------|-------|
| Tổng incidents | **295** |
| Risky users | **55** (4 High, 51 Medium) |
| Thời gian bùng phát | 17/04/2026 → hiện tại (leo thang) |
| Entity chính | ABL (~20 users), CMBD (~18), CETBD (~10) |
| Alert type | AAD Identity Protection → InitialAccess |

### Root Cause

Alert **"Unfamiliar Sign-in Properties"** được trigger bởi Entra ID ML Risk Engine khi phát hiện behavioral anomaly (IP/device/location lạ), **không phụ thuộc vào MFA**. Revoke session không giải quyết vì user đăng nhập lại từ cùng môi trường lạ → incident mới.

### 2 Scenario cần chẩn đoán

| Scenario | Dấu hiệu | Giải pháp |
|----------|-----------|-----------|
| **A: Infrastructure Change** | IP cùng 1-2 ASN/ISP Bangladesh | Named Locations + CA Policy |
| **B: Real Attack (AiTM)** | IP phân tán nhiều quốc gia | Token Protection + FIDO2 MFA + Hunt phishing |

### Files phân tích chi tiết

- [`analysis_unfamiliar_signin.md`](incidents/analysis_unfamiliar_signin.md) — Báo cáo tổng hợp
- [`investigation_chat_log.md`](incidents/investigation_chat_log.md) — Full analysis + KQL queries + IR playbook

---

## 🔍 Quick Start: KQL Investigation

### 1. Sign-in overview cho risky user

```kql
EntraIdSignInEvents
| where Timestamp > ago(30d)
| where AccountUpn =~ "user@domain.com"
| where ErrorCode == 0
| project Timestamp, AccountUpn, IPAddress, Country, City,
          OSPlatform, Browser, DeviceName, RiskLevelAggregated,
          IsManaged, IsCompliant, ClientAppUsed
| order by Timestamp desc
```

### 2. IP/ISP analysis (cần IdentityLogonEvents vì EntraIdSignInEvents không có ISP)

```kql
IdentityLogonEvents
| where Timestamp > ago(30d)
| where AccountUpn =~ "user@domain.com"
| where ActionType == "LogonSuccess"
| summarize SignIns=count(), Users=dcount(AccountUpn)
    by IPAddress, Location, ISP
| sort by SignIns desc
```

### 3. Alert investigation

```kql
AlertInfo
| where Timestamp > ago(30d)
| where Title has "Unfamiliar sign-in"
| join kind=inner AlertEvidence on AlertId
| where EntityType == "Account"
| summarize AlertCount=dcount(AlertId),
            LastSeen=max(Timestamp)
    by AccountUpn, AccountObjectId
| sort by AlertCount desc
```

### 4. Email threat check

```kql
EmailEvents
| where Timestamp > ago(30d)
| where ThreatTypes != ""
| project Timestamp, SenderFromAddress, RecipientEmailAddress,
          Subject, ThreatTypes, DeliveryAction, DeliveryLocation
| order by Timestamp desc
```

---

## ⚠️ Lưu Ý Quan Trọng

> `EntraIdSignInEvents` **KHÔNG CÓ** cột `ASN` hay `ISP`. Dùng `IdentityLogonEvents.ISP` hoặc `CloudAppEvents.ISP` thay thế.

> `EntraIdSignInEvents` dùng `Country` (string). `CloudAppEvents` dùng `CountryCode` (string). Tên cột khác nhau.

> `RiskLevelAggregated` trong `EntraIdSignInEvents` là `int`: 0=None, 10=Low, 50=Medium, 100=High.

> Tenant **không có Device tables** — investigation giới hạn ở tầng Identity + Email + Cloud.

> Ưu tiên dùng `EntraIdSignInEvents` thay vì `AADSignInEventsBeta` (deprecated).

---

## 📁 Data Files

| File | Rows | Description |
|------|------|-------------|
| `incidents/data/risky_users_20260506.csv` | 55 | Users At Risk với Risk Level, last updated time |
| `incidents/data/incidents_queue_20260506.csv` | 295 | Full incidents queue với severity, status, impacted assets |
| `schemas/All_Schemas_Combined.csv` | 751 | Toàn bộ schema 35 tables dạng CSV |
| `schemas/raw/*.csv` | 35 files | Individual schema exports per table |

---

## 🛠️ Workflow

```
1. Export schema    →  get_all_schemas.kql (chạy từng query trong Advanced Hunting)
2. Merge schemas    →  All_Schemas_Combined.csv
3. Reference doc    →  Complete_Schema_Reference.md
4. Investigation    →  Dùng KQL queries + schema reference
5. Analysis         →  Ghi nhận findings vào analysis docs
```
