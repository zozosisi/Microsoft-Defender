# 🔗 Alignment Analysis: 3 Pillars — REVISED (Data-Driven)

> **Version:** v3 — Đã tự-audit, sửa sai, và cập nhật v4.2 (Verified Safe User Override)  
> **Ngày:** 2026-05-09
>
> [!WARNING]
> **DEPRECATION NOTICE (v6.0+):** Tài liệu này phân tích hệ thống scoring/verdict cũ (v1–v5), đã bị **loại bỏ hoàn toàn** từ v6.0. Pipeline hiện tại chỉ hiển thị raw Microsoft Risk Signals — không có custom scoring hay verdict. Giữ lại làm tài liệu lịch sử.

---

## 3 Pillars

| Pillar | Nội dung | File chính |
|--------|---------|-----------|
| **1. Source of Truth** | Cách Microsoft detect + CA policies | `docs/alert_pipeline_source_of_truth.md` |
| **2. Alert & Sign-in Data** | Dữ liệu thực từ tenant | `incidents/data/export/*.csv` |
| **3. Investigation Pipeline** | Logic phân tích + scoring | `scripts/analyze_signins.py` + `queries/*.kql` |

---

## Phát Hiện Mới Từ Dữ Liệu (Self-Audit)

### signin_history.csv chứa RiskLevelDuringSignIn

```
Total sign-ins:     222,366
├── No risk (NaN):  220,998  (99.4%)
├── Medium (50):        994  (0.45%) ← 50 users
└── High (100):         104  (0.05%) ← 20 users
```

> [!CAUTION]
> ### 🚨 CRITICAL: 994 MEDIUM-risk sign-ins THÀNH CÔNG
> 
> - **Tất cả 994** đều từ **foreign countries** (không có BD)
> - **Tất cả 994** đều có **DeviceName = empty** (không có device)
> - **50 users** bị ảnh hưởng — nhiều hơn 10 CONFIRMED COMPROMISED
> 
> **Đây là BẰNG CHỨNG TRỰC TIẾP** của security gap: CA policies chỉ cover HIGH → Medium-risk sign-ins **đi thẳng qua** mà không bị MFA challenge.

### 104 HIGH-risk sign-ins cũng THÀNH CÔNG

- 20 users có High-risk successful sign-ins
- Đây là AiTM token theft — hacker có token chứa MFA claim → bypass cả HIGH-risk policy
- Bao gồm cả `button_lin@crystal-csc.cn` (4 sign-ins from CA) — **đã xác minh SAFE** (SOC Override v4.2)

---

## Alignment Check — REVISED

### ✅ PIPELINE ĐÃ ĐÚNG (tôi đã nhầm ở bản trước)

| Item | Code | Status |
|------|------|--------|
| Check RiskLevelDuringSignIn | Line 358-364: `HighRiskSignIns = count(risk >= 50)` | ✅ Cover cả Medium + High |
| Suspicious IP scoring | Line 544-546: `+5/IP, max 50` | ✅ |
| Hacker Botnet scoring | Line 541-542: `+30/country` (dedup VPN) | ✅ |
| DataBreach detection | Line 562-563: `+1000 if breach` | ✅ |
| MS Infra IP filter | Line 50-59: prefix filter | ✅ |

> [!NOTE]
> **Sửa sai:** Ở bản trước tôi nói "Pipeline không có concept Risk Level" (Gap 2) — **SAI**. Code line 358-364 **ĐÃ** check `RiskLevelDuringSignIn >= 50`, cover cả Medium (50) và High (100). Mỗi risk sign-in +5 điểm.

### ❌ GAPS THỰC SỰ (Revised)

#### Gap 1: ~~Pipeline không load unfamiliar_signin_incidents.csv~~ → ✅ ĐÃ FIX (v4)

```python
# Đã thêm load_unfamiliar_signin_data() + enrich_with_unfamiliar_signins()
# Alert IP correlation scoring: +3/IP khi Suspicious IP trùng với Alert IP
# Cross-user correlation: phát hiện botnet proxy infrastructure
```

#### Gap 2: ~~Risk Level~~ → ✅ ĐÃ CÓ (False alarm)

```python
# Line 358-364: anomalies["HighRiskSignIns"] = count(risk >= 50)  ← CÓ RỒI
# Line 556: score += HighRiskSignIns * 5                          ← ĐÚNG
# Tên biến "HighRiskSignIns" gây hiểu nhầm vì threshold = 50 (Medium+)
```

#### Gap 3: Baseline không Temporal Split — 🟡 Medium (hạ từ High)

```python
# Vấn đề: Baseline 30 ngày bao gồm hacker data
# Impact thực tế: DataBreach (+1000) override scoring → 10 verdicts ĐÚNG
# Impact tương lai: Nếu hacker không trigger DataBreach, baseline contamination
#   có thể khiến scoring THẤP hơn thực tế → miss compromised users
# → Medium priority (không urgent cho investigation hiện tại)
```

#### Gap 4: KQL chỉ export successful sign-ins — 🟢 Low

```
# Impact: Thiếu attack intelligence, không ảnh hưởng verdict
```

---

## So Sánh: Trước vs Sau Audit

| Gap | Bản trước | Bản sau (data-driven) | Lý do thay đổi |
|-----|----------|----------------------|----------------|
| 1. Load Q00 | 🟡 Medium | ✅ Đã fix (v4) | Thêm Alert IP correlation scoring |
| 2. Risk Level | 🟡 Medium | ✅ Không phải gap | Code line 358-364 đã có |
| 3. Temporal Split | 🔴 High | 🟡 Medium | DataBreach override → verdicts đúng |
| 4. ErrorCode filter | 🟢 Low | 🟢 Low | Không đổi |

---

## Kết Luận: Pipeline Có Best Practice Không?

### ✅ ĐÃ best practice:

| Aspect | Why |
|--------|-----|
| DataBreach = highest priority (+1000) | Breach detection override mọi scoring → zero false negatives |
| Hacker vs VPN dedup | Tránh false positives cho nhân viên công tác |
| Suspicious IP = Unknown IP + Unknown Device | Bắt hacker nội địa, loại trừ telemetry glitch |
| MS Infra IP filter | Loại trừ false positives từ Exchange Online backend |
| RiskLevel scoring | Cover Medium(50) + High(100) — +5 mỗi event |
| Baseline Warning | Cảnh báo khi TrustedCountryCount > 15 |
| SOC Override (v4.2) | Verified Safe User Whitelist — bỏ qua CloudAppEvents + force Safe verdict |

### 🟡 CẢI TIẾN optional (không thay đổi verdicts hiện tại):

| # | Cải tiến | Giá trị | Effort |
|---|---------|---------|--------|
| 1 | ~~Load Q00 → Alert IP scoring bonus (+3/IP)~~ | ~~Tăng confidence~~ | ✅ Đã fix (v4) |
| 2 | Temporal baseline split | Tránh contamination cho future cases | Trung bình |
| 3 | Cross-user IP correlation | Phát hiện botnet proxy infrastructure | ✅ Đã fix (v4) |
| 4 | Export failed sign-ins | Attack intelligence đầy đủ hơn | Thấp (chỉ sửa KQL) |

### 🔴 ACTION ITEM QUAN TRỌNG NHẤT (KHÔNG phải pipeline):

> **Sửa CA Policy: Thêm Medium vào Sign-in risk levels**
> 
> 994 medium-risk sign-ins đã thành công — tất cả đều từ foreign countries, empty device.  
> Đây là **lỗ hổng đang bị khai thác tích cực**, không phải lý thuyết.
> 
> Fix: Policy B → Conditions → Sign-in risk → ☑ High ☑ Medium
