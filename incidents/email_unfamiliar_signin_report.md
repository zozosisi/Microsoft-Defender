
Hi Team,

Below is a summary of our 30-day investigation into the **"Unfamiliar Sign-in Properties"** incidents across Crystal Group BD entities, followed by a remediation proposal.

---

## Part 1: 30-Day Investigation Summary (Apr 11 – May 11, 2026)

### Key Metrics

| Metric | Value |
|--------|-------|
| Risky users flagged | **54** (across 4 entities) |
| Investigation period | 30 days (Apr 11 – May 11) |
| Alert type | Unfamiliar Sign-in Properties (Entra ID Identity Protection) |

### Entity Breakdown

| Entity | Users Affected |
|--------|---------------|
| ABL (crystal-abl.com.bd) | 22 users |
| CMBD (bd.crystal-martin.com) | 21 users |
| CETBD (crystal-cet.com.bd) | 10 users |
| CSC (crystal-csc.cn) | 1 user |

### Findings

- **Abnormal sign-in activity detected across most accounts.** Many users show sign-ins from multiple unfamiliar IPs (up to 120+ unique IPs per user), different operating systems (Windows, Linux, MacOS, Android, iOS), different browsers (Edge, Chrome, Firefox), and from multiple countries outside their normal location.
- **Some users may be using VPN or proxy services.** A number of accounts show sign-ins from ISPs that are residential home broadband providers in various countries (not corporate networks). Some of these IPs and country sets overlap across multiple users.

### Why Alerts Keep Recurring

The "Unfamiliar Sign-in Properties" alert is triggered by Entra ID's **ML-based Risk Engine** when it detects behavioral anomalies (unfamiliar IP, device, location). This is **independent of MFA status**.

Our BD users had their passwords reset **on-prem (Active Directory)**, but **Entra ID Protection does not recognize on-prem password changes as remediation by default**. So even though accounts are secured, they remain flagged — triggering repeated alerts every day.

---

## Part 2: Remediation Proposal

Regarding the previous question about enabling the feature to remove BD users from the Risk list after password reset — yes, we should enable it. However, it alone won't fully resolve the current issue. Here are the recommended steps:

### Step 0 — Verify All 54 Users Are Fully Remediated

**Before proceeding with any of the steps below**, we need to confirm that **all 54 affected users** have completed:

- Password Reset
- MFA Enabled/Enforced
- Session Revoked

---

### Step 1 — Dismiss User Risk (Immediate)

For all users who have been confirmed remediated in Step 0, **dismiss their user risk** to clear their "At Risk" status and stop recurring alerts.

This is safe to do only after confirming that the user's account has been secured (password reset + MFA + session revoked).

---

### Step 2 — Enable "Allow on-premises password change to reset user risk"

This prevents the same issue from recurring in the future. When a BD user resets their password on-prem, Entra ID will automatically clear their risk state.

> [!WARNING]
> This setting only applies to **future** password changes, not currently flagged users — that's why Step 0 and Step 1 must come first.

> [!NOTE]
> **Security note from Microsoft:** They recommend securing the on-prem password change process (e.g., require MFA before password change) to prevent attackers from using this feature to clear their own risk.
>
> Ref: https://learn.microsoft.com/en-us/entra/id-protection/howto-identity-protection-remediate-unblock

---

### Step 3 — Verify Password Hash Sync (PHS) is Active

The setting in Step 2 **requires Password Hash Sync** to function. Please confirm PHS is enabled and syncing correctly in Azure AD Connect.

---

Please review and let me know if you have any questions or need clarification on any of the above.

Best regards,

