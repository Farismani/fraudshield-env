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
```

---

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
