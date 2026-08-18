# FraudShieldAI

Hybrid AI fraud detection system combining transaction behavioral analysis (Autoencoder + Transformer fusion) with cryptocurrency network intelligence (Graph Attention Network on the Elliptic Bitcoin dataset). Includes a FastAPI inference stack, interactive dashboards, a UPI payment simulator, and an in-progress synthetic payment backend.

---

## Overview

| Component | Description |
| --- | --- |
| **Transaction engine** | Autoencoder (20%) + Transformer (80%) hybrid fusion on IEEE-CIS transactions |
| **Network intelligence** | GAT on 203,769-node Elliptic Bitcoin graph (separate from fusion) |
| **Federated learning** | FedAvg proof-of-concept across simulated bank nodes |
| **Inference API** | `09_api.py` — REST endpoints, UPI demo, analyst console |
| **Payment backend** | `backend/` — SQLAlchemy-based synthetic payment ecosystem (phased rollout) |
| **Dashboards** | Streamlit analytics + standalone HTML bank console |

**Key results (test set):**

- Fraud rate: **2.91%** on 104,284 held-out transactions
- Fusion threshold: **0.8212** (F1-optimized)
- Average inference latency: **6.99 ms** (P95: 13.08 ms)

> **Simulation disclaimer:** The UPI payment interface and demo endpoints run on precomputed scores from public datasets (IEEE-CIS, Elliptic). No real banking or payment systems are connected.

---

## Architecture

```
                    Incoming Transaction Stream
                              |
              +---------------+---------------+
              |                               |
              v                               v
     +----------------+              +----------------+
     |  Autoencoder   |              |  Transformer   |
     |  (20% weight)  |              |  (80% weight)  |
     +--------+-------+              +--------+-------+
              |                               |
              +---------------+---------------+
                              |
                              v
                   +--------------------+
                   |  Hybrid Fusion     |
                   |  threshold ≥ 0.8212|
                   +--------------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
     +----------------+              +----------------+
     |  FastAPI       |              |  GNN (GAT)     |
     |  09_api.py     |              |  Elliptic graph|
     +----------------+              +----------------+
              |                               |
              v                               v
     +----------------+              +----------------+
     |  Dashboards    |              |  Subgraph /    |
     |  HTML + Stream |              |  suspicious    |
     +----------------+              +----------------+
```

Fusion formula:

```python
fused_score = 0.80 * transformer_score + 0.20 * autoencoder_score
is_flagged = fused_score >= 0.8212
```

GNN runs on the Elliptic dataset independently — there is no shared transaction ID space between IEEE-CIS and Elliptic, so GNN scores are not fused per transaction. See [`07_hybrid_fusion.py`](07_hybrid_fusion.py) and [`DEVIATIONS_FROM_SYNOPSIS.md`](DEVIATIONS_FROM_SYNOPSIS.md).

---

## Repository Structure

```
fraudshield-env/
├── ML Pipeline (run in order)
│   ├── 01_data_prep.py              IEEE-CIS preprocessing & feature engineering
│   ├── 02_train_autoencoder.py      Reconstruction-based anomaly detection
│   ├── 03_build_sequences.py        Temporal sequence tensors for Transformer
│   ├── 04_train_transformer.py        Behavioral sequence model
│   ├── 05_prepare_elliptic.py       Elliptic Bitcoin graph construction
│   ├── 06_train_gnn.py              Graph Attention Network training
│   ├── 07_hybrid_fusion.py          Fusion, threshold tuning, fusion_results.csv
│   └── 08_federated_stub.py         FedAvg simulation across bank nodes
│
├── Application Layer
│   ├── 09_api.py                    Main FastAPI server (inference + UPI demo + console)
│   ├── 10_dashboard.py              Streamlit analytics dashboard
│   ├── 11_bank_dashboard.html       Standalone HTML bank analyst console
│   └── backend/                     FraudShieldAI Pay synthetic payment backend
│       ├── app.py                   FastAPI entry (uvicorn backend.app:app)
│       ├── database.py              SQLAlchemy engine & session
│       ├── seed_data.py             Synthetic users, accounts, transactions
│       └── models/models.py         ORM models (User, Account, Transaction, Alert, …)
│
├── Testing & Benchmarks
│   ├── test_e2e.py                  15-step end-to-end validation (no server required)
│   ├── test_phase3.py               Phase 3 artifact & import verification
│   ├── verify_endpoints.py          Endpoint logic verification (offline)
│   ├── benchmark_api.py             Model-level latency benchmark (100 predictions)
│   └── benchmark_latency.py         HTTP latency benchmark against running API
│
├── Utilities
│   ├── generate_pdf.py              Quick-reference PDF (links, commands, profiles)
│   └── patch.py                     HTML patch utility for UPI demo page
│
├── Results & Examples (committed)
│   ├── fusion_results.csv           104,284 test predictions + scores
│   ├── autoencoder_examples.csv     Sample AE scores
│   ├── transformer_examples.csv     Sample Transformer scores
│   ├── gnn_examples.csv             Sample GNN predictions
│   ├── benchmark_results.json       Latency benchmark output
│   ├── autoencoder_results.png      Training loss plot
│   ├── transformer_loss.png         Training loss plot
│   ├── gnn_loss.png                 Training loss plot
│   └── FraudShieldAI_Links_And_Commands.pdf
│
├── Documentation
│   ├── ARCHITECTURE.md              System architecture deep dive
│   ├── IMPLEMENTATION_RESULTS.md    Metrics, model specs, phase results
│   ├── DEMO_COMMANDS.txt            Step-by-step demo script
│   ├── DEVIATIONS_FROM_SYNOPSIS.md  Deliberate design deviations
│   ├── FILES_CHANGED.md             Phase 3 change manifest
│   ├── PHASE3_CHECKLIST.md          Phase 3 checklist
│   ├── PHASE3_REPORT.md             Phase 3 completion report
│   ├── PHASE3_SUMMARY.md            Phase 3 summary
│   ├── PHASE3_TESTING.md            Phase 3 testing guide
│   ├── README_PHASE3.md             Phase 3 README
│   ├── PHASE_4_CHECKLIST.md         Phase 4 checklist
│   └── PHASE_4_COMPLETION_REPORT.md Phase 4 QA & documentation report
│
├── Generated / Local (gitignored — required for training & live inference)
│   ├── data/                        Processed features, labels, Elliptic graph
│   ├── *.pt                         Trained model weights (AE, Transformer, GNN)
│   └── fraudshield_pay.db           SQLite DB for backend payment ecosystem
│
├── frontend/                        React frontend scaffold (in progress)
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.10+ (tested with 3.14.3)
- Virtual environment (`.venv` or `.venv_new`)
- Trained model weights (`*.pt`) and `data/` directory (not in git — generate via pipeline scripts 01–07)
- `fusion_results.csv` (included in repo)

---

## Installation

```powershell
cd c:\Users\moham\fraudshield-env

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

### 1. Start the main inference API

```powershell
.\.venv\Scripts\python -m uvicorn 09_api:app --reload --host 127.0.0.1 --port 8000
```

| URL | Purpose |
| --- | --- |
| http://127.0.0.1:8000/ | UPI payment simulator |
| http://127.0.0.1:8000/console | Bank analyst console |
| http://127.0.0.1:8000/docs | Swagger API documentation |
| http://127.0.0.1:8000/health | Health check |

### 2. Start Streamlit analytics

```powershell
.\.venv\Scripts\streamlit run 10_dashboard.py
```

Opens at http://localhost:8501 — model architecture, fusion results, GNN subgraph explorer, federated learning section.

### 3. Open the HTML bank dashboard

Open [`11_bank_dashboard.html`](11_bank_dashboard.html) in a browser (requires the API running on port 8000).

### 4. Start the payment backend (optional, in development)

```powershell
.\.venv\Scripts\python -m uvicorn backend.app:app --reload --port 8001
```

Docs at http://127.0.0.1:8001/docs. Seed data via `backend/seed_data.py` after first run.

---

## UPI Simulator User Profiles

The `/pay` endpoint maps demo users to precomputed fraud scores from IEEE-CIS transactions.

| Profile ID | Name | Role |
| --- | --- | --- |
| `faris` | Faris | Regular personal account |
| `rahul` | Rahul | Frequent peer-to-peer transfers |
| `ahmed` | Ahmed | Retail merchant account |
| `priya` | Priya | Corporate high-volume |
| `ananya` | Ananya | Freelance / international |
| `arjun` | Arjun | New account (low history) |
| `kiran` | Kiran | Whitelisted e-commerce |
| `neha` | Neha | High-velocity account |

---

## API Reference

### `09_api.py` — Fraud Detection & Demo

**System**

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Service status |
| GET | `/` | UPI payment app (HTML) |
| GET | `/console` | Bank analyst console (HTML) |

**Predictions**

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/predict_by_id/{transaction_id}` | Scores for a transaction by ID |
| GET | `/predict_by_id?transaction_id={id}` | Same, query-param variant |
| POST | `/predict` | Predict by transaction ID (JSON body) |
| GET | `/transactions/sample?limit=N` | Random sample transactions |

**Demo & Dashboard**

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/pay` | UPI payment with real-time fraud verdict |
| GET | `/api/dashboard_stats` | Console metrics (counts, fraud rate, alerts) |
| GET | `/api/gnn_graph` | GNN subgraph for fraud ring visualization |

**GNN**

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/gnn/suspicious` | Top suspicious Elliptic network nodes |
| GET | `/gnn/subgraph/{node_id}` | Neighborhood subgraph (±2 hops) |

Example prediction response:

```json
{
  "transaction_id": 3301550,
  "autoencoder_score": 0.1439,
  "transformer_score": 0.4498,
  "fused_score": 0.3886,
  "flagged": false,
  "explanation": "..."
}
```

### `backend/app.py` — FraudShieldAI Pay (in development)

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/health` | Health check |
| GET | `/api/info` | Service info & simulation disclaimer |
| WS | `/ws/events` | Real-time payment/fraud events |
| GET | `/api/auth/test` | Auth phase placeholder |
| GET | `/api/payments/test` | Payments phase placeholder |
| GET | `/api/analyst/test` | Analyst console phase placeholder |

---

## ML Pipeline

Run sequentially after placing raw IEEE-CIS and Elliptic data in `data/`:

```powershell
python 01_data_prep.py
python 02_train_autoencoder.py
python 03_build_sequences.py
python 04_train_transformer.py
python 05_prepare_elliptic.py
python 06_train_gnn.py
python 07_hybrid_fusion.py
python 08_federated_stub.py   # optional proof-of-concept
```

| Script | Output |
| --- | --- |
| `01_data_prep.py` | `data/features.npy`, `labels.npy`, `transaction_ids.npy`, `mask.npy` |
| `02_train_autoencoder.py` | `autoencoder_model.pt` |
| `04_train_transformer.py` | `transformer_model.pt` |
| `05_prepare_elliptic.py` | `data/elliptic_graph.pt` |
| `06_train_gnn.py` | `gnn_model.pt` |
| `07_hybrid_fusion.py` | `fusion_results.csv` |

---

## Models & Data

| Artifact | Type | Role |
| --- | --- | --- |
| `autoencoder_model.pt` | Reconstruction AE (~239 KB) | Anomaly via reconstruction error (20% fusion) |
| `transformer_model.pt` | Transformer encoder (~511 KB) | Behavioral sequences (80% fusion) |
| `gnn_model.pt` | Graph Attention Network (~237 KB) | Elliptic node classification |

| Dataset | Size | Source |
| --- | --- | --- |
| IEEE-CIS (train) | 590,540 transactions, 424 features | Kaggle IEEE-CIS Fraud Detection |
| IEEE-CIS (test) | 104,284 transactions | Held-out via `07_hybrid_fusion.py` |
| Elliptic Bitcoin | 203,769 nodes, 468,710 edges | Elliptic++ dataset |

---

## Testing & Benchmarks

```powershell
# End-to-end validation (15 steps, no server)
.\.venv\Scripts\python test_e2e.py

# Phase 3 artifact verification
.\.venv\Scripts\python test_phase3.py

# Offline endpoint logic checks
.\.venv\Scripts\python verify_endpoints.py

# Model-level latency (100 predictions, no server)
.\.venv\Scripts\python benchmark_api.py

# HTTP latency (requires API running on :8000)
.\.venv\Scripts\python benchmark_latency.py
```

**Benchmark results** (`benchmark_results.json`):

| Metric | Value |
| --- | --- |
| Average | 6.99 ms |
| Median | 5.68 ms |
| P95 | 13.08 ms |
| P99 | 32.27 ms |
| Min / Max | 2.37 / 61.86 ms |

Generate a printable command reference:

```powershell
.\.venv\Scripts\python generate_pdf.py
```

Outputs `FraudShieldAI_Links_And_Commands.pdf`.

---

## Documentation Index

| Document | Contents |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full system design, data flow, model specs |
| [IMPLEMENTATION_RESULTS.md](IMPLEMENTATION_RESULTS.md) | Training metrics, inference performance |
| [DEMO_COMMANDS.txt](DEMO_COMMANDS.txt) | Complete demo walkthrough |
| [PHASE_4_COMPLETION_REPORT.md](PHASE_4_COMPLETION_REPORT.md) | Final QA status and verification evidence |
| [DEVIATIONS_FROM_SYNOPSIS.md](DEVIATIONS_FROM_SYNOPSIS.md) | FedAvg vs Flower, GNN visualization scope |

---

## Limitations

1. Models are trained once — no online or continuous learning
2. GNN and transaction fusion operate on separate datasets with no entity resolution
3. Federated learning is a simulation stub, not distributed training
4. Payment backend (`backend/`) is a phased synthetic ecosystem — auth, payments, and analyst routes are placeholders
5. Academic datasets only — not validated on real banking data

---

## License

Academic research project. For educational and research use.
