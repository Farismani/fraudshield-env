# FraudShieldAI Baseline Safety Checkpoint

Date: 2026-09-06

## Checkpoint

- Git baseline commit: `8327a3e` (`Update README with academic context and results summary`)
- The working tree was already modified before this checkpoint. Those changes are preserved and are not reverted.
- Frontend production build passes.
- `backend/` Python modules compile and import.
- The existing legacy inference regression test is currently blocked because the active environment is missing `python-dateutil`.

## Protected Scope

Do not edit, retrain, overwrite, delete, or move any of these:

- `01_data_prep.py` through `08_federated_stub.py`
- `autoencoder_model.pt`
- `transformer_model.pt`
- `gnn_model.pt`
- `data/features.npy`
- `data/labels.npy`
- `data/mask.npy`
- `data/transaction_ids.npy`
- `data/window_indices.npy`
- `data/elliptic_graph.pt`
- Any model notebook or preprocessing artifact used to create the trained models

## Current Artifact Reality

The repository documentation describes the protected model and processed-data artifacts, but they are not currently present in this workspace. Therefore the payment backend must not claim live model inference until those artifacts are restored from the protected baseline.

The existing `fusion_results.csv` is available and may be read as a frozen, precomputed inference result. It is not a replacement for the missing model artifacts.

## Safe Inference Boundary

- Legacy inference entry point: `09_api.py`, `run_inference()` and its read-only runtime loader.
- Webapp integration boundary: `backend/app.py`, `fraud_score_for_transaction()`.
- Current webapp fallback: deterministic lookup from `fusion_results.csv`, blended with demo rules.
- No training code or model artifact is modified by the webapp.

## Phase Status At Checkpoint

- Phase 0: checkpoint and protected-file map documented here; artifact restoration still required.
- Phase 1: frontend/backend structure, environment URL, API, and SQLite connection exist.
- Phase 2: eight seeded demo profiles and wallet metadata exist.
- Phase 3: login, session token, PIN validation, and device tracking exist.
- Phase 4: wallet balances and insufficient-balance protection exist.
- Phase 5: send money, history, and transaction persistence exist.
- Phase 6: partial only; frozen CSV fallback exists, live model call is blocked by missing artifacts.
- Phase 7: approved, flagged, and blocked decisions plus reasons are implemented.
- Phase 8: WebSocket broadcast and frontend refresh are implemented.
- Phase 9: QR payload payments are implemented.
- Phase 10: payment requests with approve/reject are implemented.
- Phase 11: merchant mode is implemented for the `kiran` profile with static QR payments, merchant sales dashboard, daily/weekly summaries, and owner/analyst-protected refunds.
- Phase 12: analyst metrics, live feed, and freeze/reactivate actions exist; admin authentication and pending-review actions are incomplete.
- Phase 13: complete; merchant mode, downloadable transaction receipts, recent contacts, spending categories, merchant cashback, device trust management, and risk trends are implemented.
- Phase 14: focused webapp regression coverage exists in `test_webapp.py` and passes 4/4 scenarios; broader model-artifact tests remain blocked while protected files are absent.
- Phase 15: local run documentation, frontend environment example, demo credentials, and focused test command are complete; deployment is not complete.
