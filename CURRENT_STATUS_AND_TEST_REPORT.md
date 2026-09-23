# FraudShield Pay Current Status and Test Report

Date: 2026-09-06

## 1. Current Architecture

The project has two application layers:

- `09_api.py`: original frozen fraud-analysis API and dashboards.
- `backend/` + `frontend/`: synthetic FraudShield Money webapp.

The webapp currently uses **precomputed fraud outputs** from `fusion_results.csv`. It does not retrain or modify any trained model. Live `.pt` model inference is intentionally not enabled because the protected model and preprocessing artifacts are not present in this workspace.

## 2. What Has Been Implemented

### Phase 0: Baseline Safety

- Protected baseline documented in `BASELINE_SAFETY.md`.
- Training scripts and model artifacts identified as protected.
- Existing changes preserved.
- No training code or model weights were edited.

### Phases 1-2: Application and Profiles

- React/Vite frontend in `frontend/`.
- FastAPI payment backend in `backend/app.py`.
- SQLite database in `fraudshield_webapp.db`.
- Eight seeded profiles with credentials, balances, risk levels, personas, devices, and wallets.
- Local environment example in `frontend/.env.example`.

### Phase 3: Authentication

- Profile login.
- Password validation.
- Session token.
- Payment PIN validation.
- Device registration and new-device alert.
- Current-user endpoint.

### Phases 4-5: Wallet and Payments

- FraudShield Money balances.
- Insufficient-balance protection.
- Sender and receiver balance updates.
- Transaction history.
- Notes and transaction status persistence.
- QR payments.
- Payment requests with approve/reject.

### Phases 6-7: Fraud Decisions

- Deterministic read-only adapter in `backend/fraud_service.py`.
- Reads scores from `fusion_results.csv`.
- Demo rules consider profile risk, amount, velocity, device, and receiver risk.
- Decisions:
  - `COMPLETED`: approved
  - `WARNING`: flagged
  - `BLOCKED`: stopped
- Risk score, risk level, reasons, and model-score hint are persisted.
- Fraud warning popup appears only for `WARNING` or `BLOCKED` payments.

### Phase 8: Real-Time Updates

- WebSocket endpoint at `/ws/events`.
- Payment events broadcast to connected clients.
- Frontend refreshes activity and admin data after events.

### Phase 9: QR Payments

- User QR payloads such as `FSQR:rahul`.
- Merchant QR payloads such as `FSQR:MRC_CAFE`.
- QR payments use the same fraud decision path as normal payments.

### Phase 10: Payment Requests

- Request money from another profile.
- Incoming request approval or rejection.
- Approval runs PIN and fraud checks.
- Fraud warning popup also applies to request approvals.

### Phase 11: Merchant Mode

- Three demo merchants.
- Static merchant QR codes.
- Merchant dashboard.
- Daily and weekly sales totals.
- Merchant payment feed.
- Owner/analyst-protected refunds.
- Merchant view available to the `kiran` profile.

### Phase 12: Admin/Analyst Dashboard

- Analyst login:
  - Username: `analyst`
  - Password: `admin001`
- Protected admin dashboard.
- User count, transaction count, volume, flagged count, blocked count.
- Live fraud/payment feed.
- Freeze and reactivate profiles.

### Phase 13: Product Features

- Downloadable transaction receipts.
- Recent contacts.
- Spending categories.
- Merchant cashback: 1% for approved merchant payments, capped at `100 FSM`.
- Cashback history.
- Device list.
- Trust/revoke device controls.
- Recent risk trend and average risk.

### Phase 14: Testing

- Focused regression suite in `test_webapp.py`.
- Current result: 4 tests passed.
- Covered login, wrong PIN, insufficient balance, transfer persistence, receipts, admin access, devices, and risk trends.

### Phase 15: Local Demo Setup

- Backend command documented.
- Frontend command documented.
- Frontend API environment configured for port `8001`.
- Demo credentials documented in `README.md`.

## 3. Local Services

Start the backend:

```powershell
.\.venv\Scripts\python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Start the frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open:

- Webapp: http://127.0.0.1:5173
- Backend docs: http://127.0.0.1:8001/docs
- Backend health: http://127.0.0.1:8001/api/health

Run tests:

```powershell
.\.venv\Scripts\python -m pytest test_webapp.py -q
```

## 4. Credentials

| Profile | Password | PIN | Intended test use |
|---|---|---|---|
| Faris | `pass001` | `1234` | Normal approved payment |
| Rahul | `pass002` | `1234` | Receiver/frequent transfers |
| Ahmed | `pass003` | `1234` | Normal profile |
| Priya | `pass004` | `1234` | Low-risk profile |
| Ananya | `pass005` | `1234` | New-device behavior |
| Arjun | `pass006` | `1234` | Medium-risk behavior |
| Kiran | `pass007` | `1234` | Merchant profile |
| Neha | `pass008` | `1234` | High-risk warning scenario |
| Analyst | `admin001` | N/A | Admin dashboard |

## 5. Test Combination Matrix

### A. Normal Approved Payment

1. Login as `Faris` / `pass001`.
2. Select receiver `Rahul`.
3. Amount: `1` or `500`.
4. PIN: `1234`.
5. Expected:
   - Transaction status: usually `COMPLETED`.
   - Sender balance decreases.
   - Receiver balance increases.
   - No fraud popup.
   - Transaction appears in Activity.

### B. Wrong PIN

1. Login as Faris.
2. Select Rahul.
3. Enter amount `1`.
4. Enter PIN `0000`.
5. Expected:
   - HTTP/API error.
   - No balance movement.
   - No successful transaction.

### C. Insufficient Balance

1. Login as Faris.
2. Select Rahul.
3. Enter amount `10000000`.
4. PIN: `1234`.
5. Expected:
   - `Insufficient FraudShield Money` error.
   - No balance movement.

### D. Fraud Warning Popup

1. Login as `Neha` / `pass008`.
2. Select receiver `Kiran`.
3. Enter amount `10000` to `15000`.
4. PIN: `1234`.
5. Expected:
   - Backend returns `WARNING` or `BLOCKED` depending on the deterministic score.
   - FraudShield warning popup appears.
   - Popup shows risk score and reasons.
   - `BLOCKED`: wallet is not debited.
   - `WARNING`: payment is flagged and may complete according to the returned status.

The popup is controlled by the response status, not by the frontend guessing. It appears only when status is `WARNING` or `BLOCKED`.

### E. QR Payment

1. Login as Faris.
2. Set QR payload to `FSQR:rahul` or `FSQR:MRC_CAFE`.
3. Enter amount and PIN `1234`.
4. Click `Pay QR`.
5. Expected:
   - Receiver or merchant receives the payment when approved.
   - Same fraud rules and warning popup apply.

### F. Merchant and Cashback

1. Login as Faris.
2. Use QR payload `FSQR:MRC_CAFE`.
3. Use a small amount such as `100` and PIN `1234`.
4. Expected:
   - Approved merchant payment receives `1 FSM` cashback.
   - Activity shows cashback earned.
5. Login as Kiran.
6. Open Merchant.
7. Expected:
   - Merchant QR is visible.
   - Daily/weekly sales are visible.
   - Sales feed contains the payment.

### G. Payment Request

1. Login as Faris.
2. Open Requests.
3. Request money from Rahul.
4. Login as Rahul in another browser/session.
5. Open Requests and approve with PIN `1234`.
6. Expected:
   - Transfer is created.
   - Request status changes to approved or blocked.
   - Fraud popup appears if the result is `WARNING` or `BLOCKED`.

### H. Admin Dashboard

1. Log in to a normal profile.
2. Open Analyst.
3. Expected: metrics and live feed are visible.
4. Freeze a profile.
5. Attempt login or payment with that profile.
6. Expected: profile is rejected as inactive.
7. Reactivate the profile.
8. Expected: login/payment becomes available again.

### I. Device Trust and Risk Trend

1. Login with a new `device_id` or use a fresh browser session.
2. Open Activity.
3. Expected:
   - Device appears in Trusted devices.
   - New-device alert may appear.
   - Trust/Revoke control changes device state.
   - Risk trend shows recent risk average and tracked payments.

## 6. Automated Test Result

Command:

```powershell
.\.venv\Scripts\python -m pytest test_webapp.py -q
```

Expected result:

```text
4 passed
```

The suite may show deprecation warnings from current FastAPI/SQLAlchemy dependencies. These warnings do not currently fail the tests.

## 7. Important Model Safety Note

The app does not retrain, overwrite, move, or edit the trained model files or training scripts. The current payment demo uses deterministic precomputed outputs from `fusion_results.csv`. Live model inference remains a future option after restoring the protected `.pt` and preprocessing artifacts.
