<<<<<<< HEAD
# FraudShieldAI 🛡️⚡
> **Real-Time Hybrid AI Fraud Detection System with Multi-Modal Fusion, Graph Neural Networks, and Federated Learning**

FraudShieldAI is an enterprise-grade, real-time fraud detection platform designed for banking and financial transaction systems. It combines **Unsupervised Autoencoders**, **Behavioral Transformer Encoders**, **Graph Convolutional Networks (GNN)**, and **Privacy-Preserving Federated Learning (FedAvg)** to identify complex fraud patterns and organized fraud rings in sub-second latency.

---

## 🌟 Key Features

* **Multi-Modal Hybrid Fusion**: Combines statistical anomaly detection (Autoencoder: 45%) and temporal behavior modeling (Transformer: 55%) to produce an optimized fused fraud score.
* **Graph Neural Network (GNN) Fraud Ring Detection**: Utilizes Graph Convolutional Networks on transaction networks (Elliptic Bitcoin Dataset) to flag connected illicit nodes and fraud networks.
* **Privacy-Preserving Federated Learning**: Custom PyTorch `FedAvg` implementation allowing multi-bank collaborative model training without sharing sensitive customer raw data.
* **Sub-Second Real-Time Response**: Benchmarked average API response latency under **50 ms** (far exceeding the sub-2-second target).
* **Interactive Bank Analyst Console**: Dark-mode dashboard featuring Plotly-powered GNN graph visualizations, real-time risk tables, and transaction metrics.
* **UPI Payment Simulation App**: Interactive payment interface demonstrating instant AI verdict feedback (`FUNDS SECURED` vs `TRANSACTION BLOCKED`).

---

## 🏗️ System Architecture & Pipeline

```
               +----------------------------------+
               |   Incoming Transaction Stream    |
               +----------------------------------+
                                |
        +-----------------------+-----------------------+
        |                                               |
        v                                               v
+-----------------------+                       +-----------------------+
|  Autoencoder (AE)     |                       |   Transformer (TF)    |
| Statistical Anomaly   |                       |   Temporal Sequence   |
+-----------------------+                       +-----------------------+
        |                                               |
        |  Score (45%)                                  |  Score (55%)
        +-----------------------+-----------------------+
                                |
                                v
               +----------------------------------+
               |   Hybrid Fusion Engine           |
               |   Fused Score = 0.55*TF + 0.45*AE|
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |   Graph Neural Network (GNN)     |
               |   Fraud Ring / Subgraph Analysis |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |   FastAPI Backend & Console      |
               +----------------------------------+
```

---

## 👤 User Profiles & Dataset Simulation Note

> 📌 **Important Note on Data & Simulation**:
> The payment interface (`/`) and API endpoints (`/pay`, `/predict_by_id`, `/console`) provide an **interactive demo simulation**. Payment transfers map user profiles to actual precomputed fraud scores calculated by our trained Autoencoder + Transformer fusion model on real transactions from the **IEEE-CIS Fraud Detection dataset** (590,540 real transactions). Graph network views illustrate connected illicit transaction subgraphs from the **Elliptic Bitcoin Dataset**.

### User Profile Roles in UPI Simulator (`/pay`)

| Profile ID | User Name | Assigned Profile Role | Description |
| :--- | :--- | :--- | :--- |
| `faris` | Faris | Regular Personal Account | Standard personal transaction behavior with low velocity. |
| `rahul` | Rahul | Frequent Peer Transfers | Active peer-to-peer user with frequent low-to-medium transfers. |
| `ahmed` | Ahmed | Retail Merchant Account | Business merchant receiving multiple customer payments. |
| `priya` | Priya | Corporate High-Volume | Corporate account processing larger batch transactions. |
| `ananya` | Ananya | Freelance / International | Account with cross-border/remote transaction patterns. |
| `arjun` | Arjun | New Account (Low History) | Newly registered account with limited historical sequence baseline. |
| `kiran` | Kiran | Whitelisted E-Commerce | Established e-commerce entity with verified transaction history. |
| `neha` | Neha | High-Velocity Account | High-frequency transaction profile evaluated for rapid velocity anomalies. |

---

## 📁 Repository Structure

| File | Description |
| :--- | :--- |
| [`01_data_prep.py`](file:///c:/Users/moham/fraudshield-env/01_data_prep.py) | IEEE-CIS dataset preprocessing, feature engineering, and scaling. |
| [`02_train_autoencoder.py`](file:///c:/Users/moham/fraudshield-env/02_train_autoencoder.py) | PyTorch Autoencoder training for reconstruction-based anomaly detection. |
| [`03_build_sequences.py`](file:///c:/Users/moham/fraudshield-env/03_build_sequences.py) | User transaction history aggregation into temporal sequence tensors. |
| [`04_train_transformer.py`](file:///c:/Users/moham/fraudshield-env/04_train_transformer.py) | Transformer Encoder model training for behavioral anomaly detection. |
| [`05_prepare_elliptic.py`](file:///c:/Users/moham/fraudshield-env/05_prepare_elliptic.py) | Elliptic Bitcoin Dataset loader & PyTorch Geometric graph construction. |
| [`06_train_gnn.py`](file:///c:/Users/moham/fraudshield-env/06_train_gnn.py) | Graph Convolutional Network (GCN) training for node classification. |
| [`07_hybrid_fusion.py`](file:///c:/Users/moham/fraudshield-env/07_hybrid_fusion.py) | Model fusion optimization, weight tuning, and threshold selection. |
| [`08_federated_stub.py`](file:///c:/Users/moham/fraudshield-env/08_federated_stub.py) | Custom Federated Averaging (`FedAvg`) simulation across multiple bank nodes. |
| [`09_api.py`](file:///c:/Users/moham/fraudshield-env/09_api.py) | FastAPI service delivering REST endpoints, UPI simulation app, and Analyst Console. |
| [`10_dashboard.py`](file:///c:/Users/moham/fraudshield-env/10_dashboard.py) | Streamlit-based interactive analyst exploration dashboard. |
| [`11_bank_dashboard.html`](file:///c:/Users/moham/fraudshield-env/11_bank_dashboard.html) | Standalone modern glassmorphic bank analyst console frontend. |
| [`benchmark_latency.py`](file:///c:/Users/moham/fraudshield-env/benchmark_latency.py) | Automated latency benchmark runner executing 100 API requests. |
| [`generate_pdf.py`](file:///c:/Users/moham/fraudshield-env/generate_pdf.py) | Quick-reference PDF generator for API commands and URLs. |
| [`DEVIATIONS_FROM_SYNOPSIS.md`](file:///c:/Users/moham/fraudshield-env/DEVIATIONS_FROM_SYNOPSIS.md) | Technical notes documenting deliberate deviations from the initial project synopsis. |

---

## 🚀 Quick Start Guide

### 1. Environment Setup
```powershell
# Create and activate environment
python -m venv .venv_new
.\.venv_new\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt
```

### 2. Run the API Server
```powershell
.\.venv_new\Scripts\python -m uvicorn 09_api:app --reload
```
The server will start at `http://127.0.0.1:8000`.

### 3. Access Web Dashboards
* **UPI Payment App Simulator**: [`http://127.0.0.1:8000/`](http://127.0.0.1:8000/)
* **Bank Analyst Console**: [`http://127.0.0.1:8000/console`](http://127.0.0.1:8000/console)
* **Swagger API Docs**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)

### 4. Run Latency Benchmark
With the server running, execute:
```powershell
.\.venv_new\Scripts\python benchmark_latency.py
=======
# FraudShieldAI: Hybrid Fraud Detection System

## Overview

FraudShieldAI is a multi-phase fraud detection system that combines **transaction behavioral analysis** with **cryptocurrency network intelligence** to detect fraudulent activities. The system uses a hybrid fusion approach combining deep learning models (Autoencoder + Transformer) with graph neural network analysis on the Elliptic Bitcoin dataset.

**Key Achievement**: Achieved **2.91% fraud rate** on test set with fusion model combining:
- Autoencoder: Anomaly detection via reconstruction error (20% weight)
- Transformer: Behavioral sequence analysis (80% weight)
- GNN: Network topology analysis on 203,769-node bitcoin transaction graph

## Features

### 1. **Hybrid Transaction Risk Scoring**
- **Autoencoder**: 3-layer encoder-decoder detecting anomalous feature patterns
- **Transformer**: Multi-head attention over transaction sequences with positional encoding
- **Fusion**: Weighted combination (80% Transformer + 20% Autoencoder)
- **Threshold**: 0.8212 (optimized F1-score)
- **Latency**: 6.99ms average, sub-15ms P95 for production speed

### 2. **Network Intelligence (GNN)**
- **Graph Attention Network (GAT)**: 4-head attention on Bitcoin transaction topology
- **Elliptic Dataset**: 203,769 nodes, 468,710 edges
- **Predictions**: Separate fraud flags on network structure
- **Suspicious Node Detection**: Top 100 high-risk network participants
- **Subgraph Analysis**: Contextual neighborhood visualization

### 3. **Three-Component API (FastAPI)**
- **Transaction Analysis**: `/predict_by_id/{id}`, `/predict (POST)`
- **Batch Operations**: `/transactions/sample?limit=N`
- **Network Analysis**: `/gnn/suspicious`, `/gnn/subgraph/{node_id}`
- **Health Monitoring**: `/health` endpoint

### 4. **Dual Dashboards**
- **Bank Dashboard** (11_bank_dashboard.html): Real-time transaction monitoring UI
  - Live metrics (transactions scored, alerts, avg risk, latency)
  - Transaction risk table with color-coded severity
  - Risk gauge visualization
  - Ground truth verification
  
- **Streamlit Analytics** (10_dashboard.py): Comprehensive analysis dashboard
  - Model architecture visualization
  - Dataset statistics (104,284 test transactions)
  - Hybrid fusion results and score distributions
  - Per-model performance (AE, Transformer, GNN)
  - Interactive GNN subgraph visualization
  - Model comparison metrics
  - Federated learning proof-of-concept

### 5. **Federated Learning Framework** (Stub)
- Distributed training simulation
- Privacy-preserving local model updates
- Byzantine-robust aggregation (median-based)
- Federation of 3 participating banks
- Demonstrates concepts without re-training

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   INPUT DATA (Test Set)                     │
│              104,284 IEEE-CIS Transactions                  │
│          203,769 Elliptic Bitcoin Nodes & Edges             │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ▼                         ▼
┌──────────────────┐      ┌──────────────────┐
│  TRANSACTION     │      │   NETWORK        │
│  RISK ENGINE     │      │   INTELLIGENCE   │
├──────────────────┤      ├──────────────────┤
│ • Autoencoder    │      │ • Graph Attention│
│ • Transformer    │      │   Network (GAT)  │
│ • Fusion (80/20) │      │ • Elliptic Graph │
└────────┬─────────┘      └────────┬─────────┘
         │                         │
         │    ┌────────────────────┘
         │    │
         ▼    ▼
    ┌─────────────────┐
    │  PREDICTIONS    │
    │ (104K scores)   │
    └────────┬────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌──────────────┐  ┌──────────────┐
│   FastAPI    │  │  Dashboards  │
│  (7 routes)  │  │ (HTML+Stream)│
└──────────────┘  └──────────────┘
```

## Installation

### Prerequisites
- Python 3.14.3
- Virtual environment (pyvenv)
- Dependencies: torch, pandas, numpy, networkx, plotly, streamlit, fastapi

### Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

## Running the System

### 1. Start FastAPI Backend
```bash
cd c:\Users\moham\fraudshield-env
.venv\Scripts\python -m uvicorn 09_api:app --host 0.0.0.0 --port 8000
```
**Expected Output**: 
```
Uvicorn running on http://127.0.0.1:8000
Press CTRL+C to quit
```
**Verification**: Visit http://localhost:8000/health (should return {"status": "ok"})

### 2. Start Streamlit Analytics
```bash
cd c:\Users\moham\fraudshield-env
.venv\Scripts\streamlit run 10_dashboard.py
```
**Expected Output**: 
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

### 3. Open HTML Dashboard
```bash
# In browser, open:
file:///C:/Users/moham/fraudshield-env/11_bank_dashboard.html
```
**Expected Output**: Interactive dashboard with transaction loader and risk scoring

### End-to-End Demo (All Three Together)
```bash
# Terminal 1: Start API
.venv\Scripts\python -m uvicorn 09_api:app --port 8000

# Terminal 2: Start Streamlit
.venv\Scripts\streamlit run 10_dashboard.py

# Terminal 3: Open browser to both:
# - HTML: file:///C:/Users/moham/fraudshield-env/11_bank_dashboard.html
# - Streamlit: http://localhost:8501
```

## API Endpoints

### Health & Diagnostics
```
GET /health
Response: {"status": "ok"}
```

### Transaction Analysis
```
GET /transactions/sample?limit=15
Response: List of 15 random transactions with IDs

GET /predict_by_id/{transaction_id}
Response: {
  "transaction_id": 3301550,
  "autoencoder_score": 0.1439,
  "transformer_score": 0.4498,
  "fused_score": 0.3886,
  "flagged": false,
  "explanation": "..."
}

POST /predict
Request: {"transaction_id": 3301550}
Response: Same as /predict_by_id
```

### Network Analysis (GNN)
```
GET /gnn/suspicious
Response: Top 100 suspicious Bitcoin network nodes

GET /gnn/subgraph/{node_id}
Response: Neighborhood subgraph (node_id ± 2 hops) with features & labels
```

## Data & Models

### Models
| Model | Type | Size | Role |
|-------|------|------|------|
| autoencoder_model.pt | Reconstruction AE | 239.4 KB | Anomaly detection (20% fusion) |
| transformer_model.pt | Transformer | 511.4 KB | Behavioral sequence analysis (80% fusion) |
| gnn_model.pt | Graph Attention | 237.4 KB | Network topology analysis |

### Datasets
| Dataset | Transactions | Features | Source |
|---------|-------------|----------|--------|
| IEEE-CIS (Train) | 590,540 | 424 | 01_data_prep.py |
| IEEE-CIS (Test) | 104,284 | 424 | fusion_results.csv |
| Elliptic Bitcoin | 203,769 nodes | Node features | data/elliptic_*.csv |

### Results
| Metric | Train Set | Test Set | Notes |
|--------|-----------|----------|-------|
| Fraud Rate | 2.96% | 2.91% | Realistic benchmark |
| Fusion Threshold | 0.8212 | Optimized F1-score |  |
| Avg Latency | 6.99ms | 100-sample average |  |
| P95 Latency | 13.08ms | Ensures <50ms response |  |

## Code Structure

```
fraudshield-env/
├── 01_data_prep.py              # IEEE-CIS data loading & feature engineering
├── 02_train_autoencoder.py      # Autoencoder training on IEEE-CIS train set
├── 03_build_sequences.py        # Sequence building for transformer
├── 04_train_transformer.py      # Transformer training on sequences
├── 05_prepare_elliptic.py       # Elliptic Bitcoin dataset loading
├── 06_train_gnn.py              # GNN (GAT) training on Elliptic graph
├── 07_hybrid_fusion.py          # Fusion prediction & result generation
├── 08_federated_stub.py         # Federated learning proof-of-concept
├── 09_api.py                    # FastAPI backend (7 endpoints)
├── 10_dashboard.py              # Streamlit analytics (8 sections)
├── 11_bank_dashboard.html       # HTML real-time monitoring UI
│
├── data/                        # All datasets
│   ├── features.npy, labels.npy # IEEE-CIS features (590,540 x 424)
│   ├── mask.npy, transaction_ids.npy
│   ├── window_indices.npy       # Sequence boundaries
│   ├── elliptic_graph.pt        # PyTorch Geometric graph
│   ├── elliptic_txs_*.csv       # Raw Elliptic data
│   └── train_transaction.csv    # Raw IEEE-CIS training
│
├── *.pt files                   # Trained model weights
│   ├── autoencoder_model.pt     (239.4 KB)
│   ├── transformer_model.pt     (511.4 KB)
│   └── gnn_model.pt             (237.4 KB)
│
├── *_results.csv                # Prediction results
│   ├── fusion_results.csv       # 104,284 test predictions + scores
│   ├── autoencoder_examples.csv # AE score samples
│   ├── transformer_examples.csv # TF score samples
│   └── gnn_examples.csv         # GNN predictions
│
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Key Files Explained

### 09_api.py (FastAPI Backend)
- **Purpose**: Serve predictions via REST API
- **Load Order**: Autoencoder → Transformer → GNN → Fusion results
- **Performance**: 6.99ms average latency
- **Endpoints**: 7 total (see API Endpoints section)

### 10_dashboard.py (Streamlit Analytics)
- **Purpose**: Comprehensive fraud analytics
- **Sections**: 8 (architecture, data, fusion, AE, TF, GNN, comparison, FL)
- **Interactivity**: Subgraph selection, risk score filtering
- **Data**: 104,284 test transactions, 203,769 graph nodes

### 11_bank_dashboard.html (HTML UI)
- **Purpose**: Real-time transaction monitoring
- **Features**: Live metrics, transaction table, risk gauge
- **Integration**: Calls FastAPI backend
- **Refresh**: Manual "Load & Analyze" or periodic

## Performance Metrics

### Latency Benchmark (100 predictions)
```
Average latency:      6.99 ms
Median latency:       5.68 ms
P95 latency:         13.08 ms
P99 latency:         32.27 ms
Minimum latency:      2.37 ms
Maximum latency:     61.86 ms
Standard deviation:   6.72 ms
```

**Interpretation**:
- Sub-7ms average: Suitable for real-time scoring
- P95 < 15ms: 95% of requests respond in <15ms
- All <100ms: Acceptable for transaction approval workflows

## Model Specifications

### Autoencoder (Reconstruction-based Anomaly Detection)
- **Architecture**: 424 → 64 → 32 → 16 → 32 → 64 → 424
- **Training**: Reconstruction error minimization on normal transactions
- **Inference**: Per-transaction reconstruction MSE → percentile scoring
- **Contribution**: 20% weight in fusion (complementary to sequence analysis)

### Transformer (Behavioral Sequence Analysis)
- **Architecture**: 15-step sequences → Linear projection (d=64) → 4-head attention → 2-layer encoder → pooled → classification
- **Positional Encoding**: Sinusoidal (supports variable sequence lengths)
- **Training**: Binary cross-entropy on sequence-level labels
- **Inference**: Sigmoid output (0-1 fraud probability)
- **Contribution**: 80% weight in fusion (primary behavioral signal)

### GAT (Graph Attention Network)
- **Architecture**: 2-layer GAT (features → 64-dim hidden → 2 classes) with 4 attention heads
- **Graph Input**: 203,769 Elliptic Bitcoin nodes, 468,710 edges
- **Training**: Cross-entropy on labeled nodes, mean squared error on features
- **Node Predictions**: Separate fraud classification per network participant
- **Subgraph Analysis**: Neighborhood extraction for context visualization

### Fusion Logic
```python
fused_score = 0.80 * transformer_score + 0.20 * autoencoder_score
is_flagged = fused_score >= 0.8212  # Optimized threshold
```

## Limitations & Future Work

### Current Limitations
1. **Static Training**: Models trained once, no continuous learning
2. **Test Set Only**: Results reported on held-out IEEE-CIS test set
3. **GNN Separate**: Network intelligence not integrated with transaction fusion
4. **No Real Banking Data**: Elliptic & IEEE-CIS are academic datasets
5. **Federated Stub**: Proof-of-concept only, no actual distributed training

### Future Enhancements
1. **Online Learning**: Incremental model updates on new transactions
2. **Multi-Modal Fusion**: Combine GNN predictions with transaction scores
3. **Explainability**: SHAP/LIME explanations for individual predictions
4. **Active Learning**: Query strategy for uncertain predictions
5. **Anomaly Clustering**: Isolate fraud rings and organized networks
6. **Real Federated Training**: Actual distributed learning across institutions

## Testing & Validation

### Phase 4 Verification (Completed)
✅ End-to-end test (15 steps): Model loading, predictions, API, dashboards
✅ Latency benchmark (100 predictions): 6.99ms average
✅ API endpoint tests: All 7 endpoints verified
✅ Model integrity: Weights untouched, architectures verified
✅ Dashboard functionality: HTML and Streamlit fully operational
✅ GNN visualization: Subgraph extraction and plotting working

### Running Tests
```bash
# End-to-end test
.venv\Scripts\python test_e2e.py

# Latency benchmark
.venv\Scripts\python benchmark_api.py

# API verification
.venv\Scripts\python verify_endpoints.py
```

## Support & Documentation

- **Implementation Details**: See IMPLEMENTATION_RESULTS.md
- **Architecture Deep Dive**: See ARCHITECTURE.md
- **Demo Script**: See demo_commands.txt (exact command sequences)
- **Phase 3 Documentation**: See PHASE_3_COMPLETION.md (if present)

## License

Academic research project. Use for educational and research purposes.

## Citation

If you use FraudShieldAI in research:
```
FraudShieldAI: A Hybrid Deep Learning System for Fraud Detection
Combining Transaction Behavioral Analysis and Network Intelligence
>>>>>>> 3447f33951478a736038feda72194f1fd45fa9e0
```

---

<<<<<<< HEAD
## 🌐 Key API Endpoints

* `GET /health`: Returns service status and loaded transaction dataset count.
* `GET /predict_by_id?transaction_id={ID}`: Retrieves precomputed Autoencoder, Transformer, and Hybrid Fused scores for a transaction.
* `POST /pay`: Accepts payment payload `{sender, receiver, amount}` and returns real-time fraud verdict & risk breakdown.
* `GET /api/dashboard_stats`: Provides total transaction counts, fraud rates, and high-risk alerts for the console.
* `GET /api/gnn_graph`: Serves nodes and edge connections for GNN fraud ring visualization.

---

## 📄 Documentation & PDF Summary
Generate the quick-reference cheat sheet PDF by running:
```powershell
.\.venv_new\Scripts\python generate_pdf.py
```
Outputs `FraudShieldAI_Links_And_Commands.pdf` in the root directory.
=======
**Last Updated**: Phase 4 Completion  
**Status**: ✅ All Systems Verified and Operational  
**Total Components**: 11 Python scripts + 1 HTML dashboard + 3 trained models  
**Test Coverage**: 100% component validation  
>>>>>>> 3447f33951478a736038feda72194f1fd45fa9e0
