# FraudShieldAI: A Hybrid Fraud Detection and Synthetic Digital Wallet Platform

## A Reproducible Research and System Design Report

**Author:** [Your Name]

**Affiliation:** [Department, Institution]

**Date:** September 2026

---

## Abstract

Financial fraud is difficult to detect because fraudulent activity can appear anomalous in several different ways. A transaction may contain unusual feature combinations, deviate from the behavioral history of an account, or be associated with a suspicious network of entities. This project, FraudShieldAI, investigates a hybrid fraud detection architecture combining three forms of analysis: reconstruction-based anomaly detection using an autoencoder, sequential behavioral modeling using a Transformer encoder, and network-level intelligence using a Graph Attention Network (GAT). The autoencoder and Transformer operate on the IEEE-CIS Fraud Detection dataset, while the GAT operates independently on the Elliptic Bitcoin transaction graph because the two public datasets do not share a transaction identifier or entity-resolution layer.

The transaction risk engine uses a weighted fusion of the Transformer and autoencoder outputs. The implemented fusion formula is $S_f = 0.80S_t + 0.20S_a$, where $S_t$ is the Transformer score and $S_a$ is the autoencoder percentile score. A threshold of approximately $0.8212$ is reported as the selected operating point. Repository documentation reports evaluation over 104,284 held-out transactions, with approximately 2.91% fraud prevalence, 75.9% precision, 60.8% recall, and 67.5% F1-score. The network-intelligence branch analyzes a graph containing approximately 203,769 nodes and 468,710 edges, with a reported validation accuracy of 84.7%.

In addition to the machine-learning pipeline, the project implements a synthetic FraudShield Money web application. The application provides profile authentication, wallet balances, payment PIN validation, peer transfers, QR payments, payment requests, merchant mode, cashback, device trust controls, risk summaries, fraud alerts, analyst monitoring, WebSocket updates, and a fraud-warning modal. For safety and reproducibility, the current wallet demo reads deterministic precomputed outputs from `fusion_results.csv`; it does not retrain or modify model artifacts. The paper documents the distinction between offline model evaluation, frozen-score application integration, and future live inference.

The result is a research prototype that demonstrates how heterogeneous fraud signals can be organized into a layered detection and payment-monitoring system while preserving dataset boundaries, documenting limitations, and protecting trained model artifacts.

**Keywords:** financial fraud detection, anomaly detection, Transformer, autoencoder, graph neural network, Graph Attention Network, hybrid fusion, digital wallet, payment risk, explainable fraud detection, synthetic banking system

---

## 1. Introduction

Digital payments have created highly convenient financial workflows, but they have also created a large and complex attack surface. Fraudulent transactions may be individually unusual, may violate the normal behavioral pattern of an account, or may be connected to groups of accounts involved in coordinated activity. A single fraud detector is therefore unlikely to represent every useful signal.

Traditional rule-based systems remain valuable because they are interpretable and easy to deploy, but they can be brittle when fraud patterns evolve. A high-value payment is not necessarily fraudulent, and a low-value payment can still be part of an account takeover or fraud ring. Machine-learning approaches can identify relationships that are difficult to encode manually, but they introduce challenges involving class imbalance, calibration, data leakage, temporal ordering, explainability, and deployment safety.

FraudShieldAI was designed to explore a layered response to this problem. The system separates transaction-level behavioral risk from graph-based network intelligence:

1. **Feature-space anomaly detection:** an autoencoder learns to reconstruct normal transaction representations. Large reconstruction errors are treated as anomalous.
2. **Behavioral sequence modeling:** a Transformer encoder analyzes up to 15 time-ordered transaction representations and estimates behavioral fraud risk.
3. **Hybrid transaction fusion:** the autoencoder and Transformer signals are normalized and combined into a single transaction score.
4. **Network intelligence:** a Graph Attention Network scores nodes in the Elliptic Bitcoin transaction graph and supports suspicious-node and subgraph analysis.
5. **Application delivery:** FastAPI services and dashboards expose the scores to analysts and to a closed synthetic wallet environment.

The project has two different meanings of “system.” The first is the trained fraud-analysis pipeline. The second is the synthetic product layer that simulates users, wallets, payments, merchants, alerts, and administrative controls. Keeping these layers distinct is central to the scientific interpretation of the work.

### 1.1 Research Questions

This project addresses the following questions:

1. Can static transaction anomalies and sequential behavioral deviations be combined into a useful fraud-risk score?
2. Can a separate graph model provide network intelligence without fabricating a false correspondence between unrelated public datasets?
3. Can the resulting analysis be delivered through a realistic synthetic payment workflow with authentication, balances, fraud decisions, alerts, and administrative monitoring?
4. Can the application preserve trained model artifacts and make the distinction between precomputed evaluation and live inference explicit?

### 1.2 Contributions

The project makes the following engineering and research contributions:

- A complete transaction-analysis pipeline based on an autoencoder and Transformer fusion.
- A separate GAT-based network-intelligence branch for graph-level investigation.
- A documented rationale for not fusing the Elliptic GNN score into the IEEE-CIS transaction score.
- A synthetic wallet backend with transactional money movement and fraud-aware payment statuses.
- A frontend application for profile login, payments, QR workflows, requests, merchant operation, alerts, receipts, cashback, device trust, and risk trends.
- A protected-model workflow in which training scripts and model artifacts are not modified by the webapp.
- A focused regression suite and a detailed test matrix for normal, suspicious, blocked, administrative, merchant, and security workflows.

---

## 2. System Scope and Safety Boundary

### 2.1 What the Project Is

FraudShieldAI is a research prototype and synthetic payment simulation. It is not connected to real banking infrastructure, real UPI rails, production payment processors, or real customer money. Wallet balances are simulated FraudShield Money units, referred to in the application as `FSM`.

The project contains:

- An offline machine-learning training and evaluation pipeline.
- Frozen inference results in `fusion_results.csv`.
- A legacy FastAPI analysis API in `09_api.py`.
- Streamlit and HTML analyst dashboards.
- A separate synthetic wallet backend in `backend/app.py`.
- A React/Vite frontend in `frontend/src/main.jsx`.
- A SQLite database for synthetic users, accounts, devices, transactions, merchants, alerts, rewards, and payment requests.

### 2.2 Protected Assets

The following artifacts are treated as protected:

- `01_data_prep.py` through `08_federated_stub.py`.
- `autoencoder_model.pt`.
- `transformer_model.pt`.
- `gnn_model.pt`.
- Processed feature arrays and graph artifacts under `data/`.
- Any notebook or preprocessing artifact required to reproduce the trained models.

The webapp is not permitted to retrain, overwrite, move, delete, or refactor these assets.

### 2.3 Current Application Inference Mode

The trained model pipeline originally produces scores using the saved model weights and preprocessing tensors. The current synthetic wallet application uses a read-only adapter, `backend/fraud_service.py`, that reads rows from `fusion_results.csv`. The adapter selects a row deterministically using a hash of the demo payment identity and amount. This is not the same as running the trained models on newly constructed transaction features.

Therefore, the current application should be described as:

> A fraud-aware synthetic payment application driven by deterministic precomputed outputs from the trained model pipeline and supplemented by application-level demo risk rules.

It should not be described as a live production inference system.

---

## 3. Related Technical Background

### 3.1 Reconstruction-Based Anomaly Detection

An autoencoder consists of an encoder $f_\theta$ and decoder $g_\phi$. Given an input vector $x$, the reconstructed vector is:

$$
\hat{x} = g_\phi(f_\theta(x)).
$$

The reconstruction objective is commonly expressed as mean squared error:

$$
\mathcal{L}_{AE} = \frac{1}{d}\sum_{j=1}^{d}(x_j - \hat{x}_j)^2,
$$

where $d$ is the feature dimension. When trained primarily on legitimate examples, the model may reconstruct normal patterns more accurately than unusual patterns. The resulting reconstruction error can act as an anomaly signal.

The limitation is that reconstruction error is not automatically a calibrated fraud probability. Fraud-like observations can sometimes be reconstructed well, while legitimate rare observations can receive a high error. In FraudShieldAI, the raw error is converted to a percentile-style score before fusion.

### 3.2 Transformer Sequence Modeling

A Transformer models relationships among sequence positions using self-attention. Given queries $Q$, keys $K$, and values $V$, scaled dot-product attention is:

$$
Attention(Q,K,V) = softmax\left(\frac{QK^T}{\sqrt{d_k}}\right)V.
$$

The FraudShieldAI Transformer receives up to 15 transaction feature vectors. Each 424-dimensional vector is projected to a 64-dimensional representation. Sinusoidal positional encoding is added so the model can distinguish earlier and later positions. Two Transformer encoder layers with four attention heads process the sequence. Masked pooling aggregates only valid sequence positions, which is important for users with less than 15 historical transactions.

The Transformer produces a logit that is converted to a score using the sigmoid function:

$$
S_t = \sigma(z_t) = \frac{1}{1+e^{-z_t}}.
$$

### 3.3 Graph Neural Networks and Attention

A graph neural network represents entities as nodes and relationships as edges. In a fraud context, a graph can represent transactions, accounts, addresses, wallets, or other entities. A Graph Attention Network learns different weights for neighboring nodes rather than treating every neighbor equally. This allows the model to emphasize potentially informative relationships.

The Elliptic branch in FraudShieldAI is a node-classification model. It uses two GAT layers followed by a classifier. The graph is analyzed independently from the IEEE-CIS transaction table.

### 3.4 Hybrid Fusion

Fusion combines multiple model outputs. In this project, the reported operational formula is:

$$
S_f = w_tS_t + w_aS_a,
$$

with:

$$
 w_t = 0.80, \qquad w_a = 0.20, \qquad w_t+w_a=1.
$$

The transaction is flagged when:

$$
S_f \geq \tau,
$$

where the reported threshold is approximately:

$$
\tau = 0.8212.
$$

The higher Transformer weight reflects the reported stronger contribution of sequential behavioral information. This weighting is an empirical design choice and should be re-estimated when the data distribution, feature pipeline, or operating objective changes.

---

## 4. Datasets

### 4.1 IEEE-CIS Fraud Detection Dataset

The IEEE-CIS dataset supplies the transaction-level branch. The preprocessing script expects transaction and identity files, merges them on `TransactionID`, and preserves several identifiers for a proxy user grouping.

The documented processing flow is:

1. Load transaction and identity tables.
2. Merge on `TransactionID`.
3. Inspect class imbalance and missingness.
4. Construct a proxy user identifier from `card1`, `card2`, and `addr1`.
5. Remove numeric columns with excessive missingness.
6. Fill numeric missing values using medians.
7. Fill categorical values with a missing category.
8. Encode categorical values numerically.
9. Replace infinite values and remaining missing values.
10. Standardize numeric features.
11. Sort transactions by `TransactionDT`.
12. Save processed transactions and downstream arrays.

The documented processed representation has 424 features per transaction. The reported evaluation set contains 104,284 transactions with a fraud rate near 2.91%.

### 4.2 Class Imbalance

The test population is highly imbalanced. With approximately 2.91% fraud, an always-legitimate classifier can obtain high accuracy while detecting no fraud. For this reason, precision, recall, F1-score, confusion matrices, and threshold behavior are more informative than accuracy alone.

The system emphasizes the following quantities:

- **Precision:** Of transactions flagged as fraud, how many are actually fraudulent?
- **Recall:** Of fraudulent transactions, how many are detected?
- **F1-score:** Harmonic mean of precision and recall.
- **False-positive rate:** Legitimate payments incorrectly flagged.
- **ROC-AUC:** Ranking quality across thresholds, with the caveat that it can be optimistic under severe class imbalance.

### 4.3 Elliptic Bitcoin Dataset

The graph branch uses the Elliptic Bitcoin transaction graph. The documented graph contains approximately:

- 203,769 nodes.
- 468,710 edges.
- Approximately 166 node features in the model configuration.
- Two output classes.

The graph provides network context that is unavailable in an isolated transaction row. However, the graph is not the same dataset as IEEE-CIS and does not share the same transaction identifiers.

### 4.4 Dataset Boundary and Non-Fabrication Decision

It would be scientifically invalid to take an Elliptic node score and attach it to an IEEE-CIS transaction without a real mapping between entities. FraudShieldAI therefore does not numerically include the GNN score in the transaction fusion formula. The GNN is presented as a separate investigation tool.

A production system could fuse network intelligence if it had an institution-specific entity graph with a valid mapping such as:

$$
(transaction \rightarrow account \rightarrow graph\ node\ or\ community).
$$

That mapping is not supplied by the two public benchmark datasets and is not fabricated in this project.

---

## 5. Machine-Learning Methodology

### 5.1 Pipeline Overview

The offline pipeline is organized into numbered scripts:

| Script | Role |
|---|---|
| `01_data_prep.py` | Merge and preprocess IEEE-CIS transaction and identity data |
| `02_train_autoencoder.py` | Train reconstruction-based anomaly detector |
| `03_build_sequences.py` | Build time-ordered transaction windows |
| `04_train_transformer.py` | Train behavioral Transformer |
| `05_prepare_elliptic.py` | Prepare graph tensors |
| `06_train_gnn.py` | Train graph attention network |
| `07_hybrid_fusion.py` | Score, tune, evaluate, and save hybrid results |
| `08_federated_stub.py` | Demonstrate federated-learning aggregation |

### 5.2 Autoencoder Configuration

The reported autoencoder architecture is:

$$
424 \rightarrow 64 \rightarrow 32 \rightarrow 16 \rightarrow 32 \rightarrow 64 \rightarrow 424.
$$

The bottleneck has 16 dimensions. ReLU activations are used between linear layers. The reported training setup includes:

- Normal transactions used as the main reconstruction-training population.
- Batch size: 128.
- Learning rate: 0.001.
- Optimizer: Adam.
- Loss: mean squared error.
- Up to 20 epochs with early stopping behavior described in the project documentation.
- Reported final train loss: 0.0142.
- Reported final validation loss: 0.0147.

At evaluation time, reconstruction errors are rank-normalized to make them comparable with the Transformer output.

### 5.3 Sequence Construction

The Transformer uses a maximum sequence length of 15. For each transaction, the sequence builder identifies previous transactions associated with the proxy user grouping and creates a fixed-size window. Short histories are padded. A mask identifies real positions and padding positions.

A conceptual sequence for transaction $i$ is:

$$
X_i = [x_{i-14}, x_{i-13}, \ldots, x_{i-1}, x_i],
$$

where unavailable history positions are padded and excluded by the mask.

The sequence approach gives the model access to temporal context without requiring the application to hand-design every behavioral feature.

### 5.4 Transformer Configuration

The documented Transformer configuration includes:

- Input dimension: 424.
- Projected model dimension: 64.
- Attention heads: 4.
- Encoder layers: 2.
- Feed-forward dimension: 256.
- Dropout: 0.1.
- Sequence length: 15.
- Batch size: 32.
- Learning rate: 0.0005.
- Loss: binary cross-entropy.
- Reported final train loss: 0.356.
- Reported final validation loss: 0.362.

The output is a sigmoid probability-like score. It should be interpreted as a model score unless formally calibrated against a probability calibration procedure.

### 5.5 GAT Configuration

The network-intelligence branch uses a two-layer GAT configuration:

- Input dimension: approximately 166.
- Hidden dimension: 64.
- First-layer attention heads: 4.
- Second-layer attention heads: 1 with concatenation disabled.
- Dropout: 0.3.
- Classifier output: 2 classes.
- Primary loss: cross-entropy.
- Auxiliary reconstruction or regularization objective is described in project results.
- Learning rate: 0.01.
- Reported training duration: 50 epochs.

The GAT produces node-level fraud scores and labels. The dashboard then ranks suspicious nodes and extracts neighborhoods for human investigation.

### 5.6 Fusion and Threshold Selection

The fusion script searches over Transformer weights and thresholds. The documented production-style result is:

```text
Transformer weight: 0.80
Autoencoder weight: 0.20
Threshold:          0.8212
```

The key output file is `fusion_results.csv`, with columns including:

- `TransactionID`
- `true_label`
- `autoencoder_score`
- `transformer_score`
- `fused_score`

The threshold converts the continuous score into a binary operational decision. In a real payment system, a three-way or four-way policy is generally more useful than a single binary outcome. FraudShieldAI’s synthetic wallet extends the score into statuses such as approved, warning, and blocked.

---

## 6. Evaluation Results

### 6.1 Transaction Fusion Results

The project documentation reports the following held-out evaluation summary:

| Metric | Reported value |
|---|---:|
| Evaluation transactions | 104,284 |
| Fraud prevalence | 2.91% |
| Actual fraudulent transactions | Approximately 3,035 |
| Predicted high-risk transactions | 1,847 |
| Predicted safe transactions | 102,437 |
| Precision | 75.9% |
| Recall | 60.8% |
| F1-score | 67.5% |
| False-positive rate | 1.8% |
| Fusion threshold | 0.8212 |

These values should be regenerated from the exact artifact version before final publication. The repository contains minor documentation inconsistencies, including references to 3,035 and 3,036 actual fraud cases in different reports. The final paper should select the value calculated directly from the final `fusion_results.csv` file.

### 6.2 Interpretation of Precision and Recall

A precision of 75.9% means that, among transactions flagged by the selected threshold, approximately three quarters are fraudulent under the evaluation labels. A recall of 60.8% means that the system detects approximately six out of ten fraudulent transactions.

The trade-off is operational:

- Increasing the threshold may reduce false positives but miss more fraud.
- Decreasing the threshold may catch more fraud but create more customer friction.
- A financial institution may use different thresholds for authorization, step-up verification, manual review, and post-transaction investigation.

The reported F1-optimal threshold is not automatically the optimal business threshold. Business cost functions should be evaluated in later work.

### 6.3 Component-Level Results

The project reports component configurations and comparisons, but the paper should include the exact autoencoder-only, Transformer-only, and fusion metrics from a reproducible rerun. The fusion script contains the intended comparison logic:

1. Optimize a threshold for the autoencoder score.
2. Optimize a threshold for the Transformer score.
3. Search fusion weights.
4. Optimize the fusion threshold.
5. Compare precision, recall, F1-score, AUC, and confusion matrices.

This ablation is important because the claim that fusion is beneficial should be supported by a direct comparison on the same held-out rows.

### 6.4 GNN Results

The documented GNN results include:

| Metric | Reported value |
|---|---:|
| Graph nodes | 203,769 |
| Graph edges | 468,710 |
| Validation accuracy | 84.7% |
| Training accuracy | 89.3% |
| Inference time | Approximately 0.1 seconds for all nodes |
| Model size | Approximately 237.4 KB |

Accuracy alone is insufficient for an imbalanced graph problem. A final academic experiment should also report class-specific precision, recall, F1-score, confusion matrix, PR-AUC, and the number of labeled versus unlabeled nodes.

### 6.5 Latency Results

The documented benchmark tested 100 predictions and reports:

| Latency statistic | Reported value |
|---|---:|
| Mean | 6.99 ms |
| Median | 5.68 ms |
| P95 | 13.08 ms |
| P99 | 32.27 ms |
| Maximum | 61.86 ms |
| Success rate | 100% |

The benchmark should be described precisely as a local benchmark of the implemented inference API, not as a production-scale service-level agreement. Hardware, concurrency, warm-up behavior, data-loading state, and whether scores are precomputed or recomputed must be stated in the final paper.

---

## 7. Synthetic Payment Web Application

### 7.1 Purpose

The wallet application converts model outputs into an operational product scenario. Instead of presenting only CSV files and model scores, it simulates the lifecycle of a payment:

1. A profile logs in.
2. A sender selects a receiver or merchant.
3. The sender enters an amount, note, and payment PIN.
4. The backend evaluates the payment using demo rules and a deterministic precomputed model-score hint.
5. The backend assigns an operational status.
6. Balances are updated only for non-blocked payments.
7. A transaction record and fraud reasons are stored.
8. The frontend displays success, warning, or blocked feedback.
9. Analysts can inspect live metrics and fraud events.

### 7.2 Profile Model

The seeded profiles include different synthetic behavioral personas:

- Faris: regular personal account.
- Rahul: frequent peer transfers.
- Ahmed: steady or merchant-like profile.
- Priya: premium low-risk profile.
- Ananya: new-device-sensitive profile.
- Arjun: travel and merchant-heavy profile.
- Kiran: verified merchant profile.
- Neha: high-velocity high-risk profile.

Each profile has a password, payment PIN, phone, email, UPI-style identifier, location, risk level, persona, account, and device metadata.

### 7.3 Wallet Accounting

Wallets are represented by synthetic accounts. A normal non-blocked transfer performs:

$$
B_s' = B_s - A,
$$

$$
B_r' = B_r + A,
$$

where $B_s$ is the sender balance, $B_r$ is the receiver balance, and $A$ is the payment amount.

For an approved merchant payment, the current demo also applies cashback:

$$
C = min(0.01A, 100),
$$

and credits the sender with $C$. The transaction and reward record are persisted together through the backend flow.

Blocked transactions do not debit the sender or credit the receiver.

### 7.4 Application Risk Rules

The application-level risk score is a synthetic policy layer. It starts with a profile-risk baseline and adds signals such as:

- High payment amount.
- Moderately high payment amount.
- Several recent payments.
- New device.
- High-risk receiver.
- Frozen or inactive user state.

A deterministic precomputed score from `fusion_results.csv` contributes to the demo score. The application then maps the final score into statuses:

| Risk score | Operational result |
|---:|---|
| Below 50 | `COMPLETED` / approved |
| 50 to below 76 | `WARNING` / flagged |
| 76 and above | `BLOCKED` |

These thresholds belong to the synthetic application policy. They are not the same as the original fused-model threshold of 0.8212, because the wallet layer expresses risk as a percentage-like score from 0 to 100.

### 7.5 Fraud Warning Interface

The React frontend displays a modal only when the backend response status is `WARNING` or `BLOCKED`.

For a warning, the interface communicates that:

- The payment has a suspicious pattern.
- The risk score is visible.
- The reasons are shown.
- The user can close the warning and inspect the outcome.

For a blocked result, the interface communicates that:

- The payment was stopped.
- The wallet was not debited.
- The reasons and score are shown.

The frontend does not independently invent the fraud decision. It responds to the backend status.

### 7.6 Merchant Mode

The merchant layer includes:

- Static merchant QR payloads such as `FSQR:MRC_CAFE`.
- Merchant account ownership.
- Merchant sales dashboard.
- Daily and weekly sales summaries.
- Merchant sales feed.
- Merchant owner or analyst authorization.
- Refund operations.

### 7.7 Analyst Mode

The analyst dashboard is protected by a demo analyst session. It displays:

- Number of profiles.
- Number of transactions.
- Total volume.
- Flagged transactions.
- Blocked transactions.
- Risk profiles.
- Recent transaction feed.
- Freeze/reactivate actions.

### 7.8 Additional Product Features

The application also includes:

- Transaction receipts.
- Recent contacts.
- Spending categories inferred from payment notes.
- Cashback reward history.
- Device trust and revoke controls.
- Recent risk trend and average risk.
- WebSocket-based refresh notifications.

These features are product-layer functionality rather than claims about additional trained models.

---

## 8. API and Software Architecture

### 8.1 Legacy Analysis API

The original `09_api.py` exposes endpoints for:

- Health status.
- Transaction samples.
- Prediction by transaction ID.
- Custom prediction requests.
- Suspicious GNN nodes.
- GNN subgraph extraction.
- HTML dashboards.

The legacy API contains the original live-inference implementation path, including model class definitions, runtime artifact loading, sequence validation, and score calculation. It requires the protected `.pt` and preprocessing artifacts.

### 8.2 Payment Backend API

The synthetic wallet backend exposes routes for:

- `/api/health`
- `/api/info`
- `/api/demo-profiles`
- `/api/auth/login`
- `/api/auth/me`
- `/api/users`
- `/api/wallet`
- `/api/payments/send`
- `/api/qr/pay`
- `/api/requests`
- `/api/requests/{id}/approve`
- `/api/requests/{id}/reject`
- `/api/transactions`
- `/api/transactions/{id}/receipt`
- `/api/insights`
- `/api/rewards`
- `/api/devices`
- `/api/devices/{id}/trust`
- `/api/risk-trend`
- `/api/merchants`
- `/api/merchants/{id}/dashboard`
- `/api/merchants/{id}/refund/{transaction_id}`
- `/api/admin/login`
- `/api/admin/dashboard`
- `/api/admin/users/{id}/status`
- `/ws/events`

### 8.3 Data Persistence

The SQLAlchemy model layer includes entities such as:

- `User`
- `Account`
- `Device`
- `Session`
- `Merchant`
- `Transaction`
- `Alert`
- `PaymentRequest`
- `Reward`
- `Wallet`
- Additional feature-oriented tables

The current demo uses SQLite for local reproducibility. A production deployment would require a managed database, migrations, stricter transaction isolation, durable session storage, and a real secret-management strategy.

### 8.4 Frontend Architecture

The React application uses a single main application component with state for:

- Current user session.
- Profiles and receiver options.
- Transactions.
- Requests.
- Alerts.
- Admin data.
- Merchant data.
- Rewards.
- Devices.
- Risk trend.
- Fraud-warning modal state.

The frontend communicates with the backend through a small `api()` helper and uses the configured `VITE_API_URL` environment variable.

---

## 9. Testing and Reproducibility

### 9.1 Automated Webapp Tests

The focused suite `test_webapp.py` covers:

1. Wrong password rejection and wrong PIN rejection.
2. Insufficient balance protection.
3. Successful transfer persistence, fraud decision, and receipt access.
4. Device endpoint, risk trend endpoint, and analyst dashboard access.

The documented result is:

```text
4 passed
```

### 9.2 Manual Test Matrix

A complete manual test should include:

| Scenario | Profile combination | Expected result |
|---|---|---|
| Normal payment | Faris → Rahul, amount 1 or 500 | Completed, no popup |
| Wrong PIN | Faris → Rahul, PIN 0000 | Rejected, no balance change |
| Insufficient funds | Faris → Rahul, amount 10,000,000 | Rejected |
| Suspicious payment | Neha → Kiran, amount 10,000-15,000 | Warning or blocked popup |
| User QR | Faris → `FSQR:rahul` | Normal QR transfer |
| Merchant QR | Faris → `FSQR:MRC_CAFE` | Merchant sale and possible cashback |
| Merchant dashboard | Kiran login | QR, sales, summaries |
| Payment request | Faris requests Rahul | Request then approve/reject |
| Admin control | Analyst freezes profile | Profile becomes inactive |
| Device control | Any profile with registered device | Trust/revoke state changes |
| Risk trend | Any profile with payments | Recent risk summary |

### 9.3 Model-Pipeline Tests

The offline ML pipeline should be tested separately from the webapp. Recommended tests include:

- Verify that every model file exists and matches a recorded checksum.
- Verify feature dimension and sequence length.
- Verify no NaN or infinite values enter inference.
- Verify score ranges.
- Verify fusion formula against saved component scores.
- Verify the transaction identifier mapping.
- Run the same input twice and compare outputs.
- Compare saved `fusion_results.csv` values to regenerated scores.
- Evaluate thresholds on a strictly held-out set.

### 9.4 Reproducibility Checklist

A final research release should record:

- Python version.
- PyTorch version.
- PyTorch Geometric version.
- scikit-learn version.
- Operating system.
- CPU/GPU hardware.
- Random seeds.
- Dataset versions and download dates.
- Model checkpoints and SHA-256 checksums.
- Preprocessing configuration.
- Train/validation/test split logic.
- Threshold-selection procedure.
- Benchmark request count and concurrency.

---

## 10. Threats to Validity and Limitations

### 10.1 Precomputed Application Scores

The current wallet app does not pass every new payment through the trained model. It uses deterministic precomputed rows from `fusion_results.csv`. This means the webapp demonstrates fraud-aware product behavior, but it is not evidence that the trained model dynamically understands a newly entered wallet payment.

### 10.2 Public Dataset Mismatch

IEEE-CIS and Elliptic represent different domains and entity spaces. The decision not to fuse their scores per transaction is scientifically appropriate, but it also means the final application does not yet provide unified transaction-plus-network risk for the same real entity.

### 10.3 Proxy User Identity

The transaction sequence pipeline uses a proxy user identifier derived from available card and address fields. This is not guaranteed to be a real customer identity and may not represent an account in a production banking system.

### 10.4 Potential Temporal Leakage Risk

Sequence and threshold evaluation must be carefully audited for temporal leakage. A production paper should demonstrate that training, validation, and test data are separated by time or entity in a way that prevents future information from influencing past predictions.

### 10.5 Threshold Tuning

Selecting a threshold on a test set can inflate reported performance. The final publication should use training/validation data for threshold selection and reserve a final untouched test set for one-time reporting.

### 10.6 Metric Inconsistencies

Existing project reports contain minor inconsistencies, including different stated actual fraud counts and differences between documented threshold-search descriptions. Before publication, the metrics should be regenerated from one canonical artifact and copied into every report from that source.

### 10.7 Synthetic Wallet Behavior

Wallet profiles, balances, payment PINs, merchants, risk baselines, and application rules are synthetic. They are useful for demonstrating workflows but cannot establish real-world fraud-prevention effectiveness.

### 10.8 Security Limitations

The current local demo uses simple in-memory tokens and demo credentials. It is not production authentication. A real deployment would need:

- Password hashing and credential rotation.
- Secure, expiring sessions or signed JWTs.
- CSRF and rate-limit protections.
- Secret management.
- Database migrations.
- Audit logs.
- Access-control separation.
- Secure WebSocket authorization.
- Encryption in transit and at rest.
- Fraud-model governance and rollback procedures.

### 10.9 GNN Evaluation Limitations

Reported GNN accuracy does not fully characterize performance under class imbalance. Precision-recall analysis, temporal split evaluation, calibration, and false-positive cost analysis are required before making deployment claims.

---

## 11. Ethical, Privacy, and Governance Considerations

Fraud detection systems can protect users, but incorrect decisions can also deny legitimate payments, freeze accounts, or create unequal friction. A responsible system should therefore:

- Provide an explanation or reason code for adverse decisions.
- Support review and appeal workflows.
- Distinguish a warning from a definitive fraud finding.
- Monitor false positives across user groups.
- Avoid using proxy features without documented justification.
- Minimize retained personal data.
- Restrict access to transaction and device information.
- Record model versions and decision timestamps.
- Periodically evaluate drift and performance decay.
- Avoid presenting a model score as proof of criminal behavior.

The current project uses public datasets and synthetic identities for research demonstration. It does not process real customer data.

---

## 12. Recommended Experimental Extensions

### 12.1 Better Fusion Evaluation

Run an ablation study comparing:

1. Rule-based baseline.
2. Autoencoder only.
3. Transformer only.
4. Equal-weight fusion.
5. Optimized-weight fusion.
6. Fusion with calibrated probabilities.

Report confidence intervals using bootstrap resampling and evaluate on a final untouched test set.

### 12.2 Cost-Sensitive Thresholding

Replace F1-only threshold tuning with an expected-cost objective:

$$
RiskCost(\tau) = C_{FN}FN(\tau) + C_{FP}FP(\tau) + C_{Friction}Review(\tau),
$$

where $C_{FN}$ is the cost of missed fraud, $C_{FP}$ is the cost of false positives, and $C_{Friction}$ is the operational cost of challenging or reviewing a payment.

### 12.3 Probability Calibration

Apply Platt scaling, isotonic regression, or another calibration method on a validation set. This would make the score more interpretable as an estimated probability, although calibration must be monitored under distribution shift.

### 12.4 Real Entity Graph Integration

Build an institution-specific graph connecting accounts, devices, merchants, addresses, beneficiaries, and transaction events. Then join each new transaction to its account or entity node and include graph-derived risk as an additional feature.

### 12.5 Live Inference Adapter

After restoring the protected artifacts, implement a read-only live inference service that:

1. Loads the exact trained weights.
2. Loads the exact preprocessing state.
3. Validates feature dimension and ordering.
4. Builds the same sequence representation used during training.
5. Runs the autoencoder and Transformer.
6. Applies the saved fusion weights and threshold.
7. Falls back to frozen scores only when live inference is unavailable.
8. Logs model version and inference source.

### 12.6 Drift and Monitoring

Monitor:

- Score distribution shift.
- Fraud prevalence shift.
- Feature missingness.
- New-device rate.
- Challenge and block rates.
- Precision after labels mature.
- Population stability index.
- Model latency and failures.

---

## 13. Conclusion

FraudShieldAI demonstrates a layered architecture for fraud analysis and synthetic payment operations. The transaction branch combines feature-space anomaly detection and sequential behavioral modeling. The network branch adds graph-based investigation without fabricating cross-dataset identity mappings. The application branch converts these outputs into operational statuses, wallet updates, alerts, merchant workflows, analyst tools, and user-facing fraud warnings.

The most important design decision is the separation between scientific model evaluation and product simulation. The offline pipeline produces and evaluates model scores. The current wallet application consumes deterministic precomputed scores and adds a clearly labeled synthetic policy layer. This allows the project to remain runnable and safe while preserving the trained artifacts.

The reported evaluation results suggest that hybrid transaction scoring can provide useful discrimination on the documented held-out dataset, with a reported precision of 75.9%, recall of 60.8%, and F1-score of 67.5% at the selected threshold. These values should be regenerated and reconciled from a canonical artifact before formal publication. The application demonstrates how fraud signals can be delivered through a realistic payment experience, but it should not be described as a production banking system or live model deployment.

Future work should focus on strict temporal validation, calibrated risk probabilities, cost-sensitive thresholds, real entity-graph integration, live inference using the restored protected artifacts, stronger authentication, and post-deployment monitoring. With those additions, FraudShieldAI can progress from a validated research prototype and synthetic demonstration toward a more rigorous experimental platform.

---

## 14. Reproducibility Guide

### 14.1 Machine-Learning Pipeline

The intended order is:

```powershell
.\.venv\Scripts\python 01_data_prep.py
.\.venv\Scripts\python 02_train_autoencoder.py
.\.venv\Scripts\python 03_build_sequences.py
.\.venv\Scripts\python 04_train_transformer.py
.\.venv\Scripts\python 05_prepare_elliptic.py
.\.venv\Scripts\python 06_train_gnn.py
.\.venv\Scripts\python 07_hybrid_fusion.py
```

These commands require the raw datasets, protected artifacts, and the exact environment dependencies. They are included for research reproducibility only and should not be run casually against the current protected baseline.

### 14.2 Local Wallet Application

Backend:

```powershell
.\.venv\Scripts\python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

Frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Webapp:

```text
http://127.0.0.1:5173
```

### 14.3 Automated Webapp Tests

```powershell
.\.venv\Scripts\python -m pytest test_webapp.py -q
```

Expected current result:

```text
4 passed
```

---

## 15. Suggested Figures and Tables for the Final Paper

### Figures

1. Overall FraudShieldAI architecture.
2. Autoencoder encoder-decoder structure.
3. Transformer sequence and masking process.
4. Hybrid fusion decision path.
5. Elliptic GAT network-intelligence branch.
6. Score distributions for legitimate and fraudulent transactions.
7. Precision-recall curve.
8. Fusion threshold versus F1-score.
9. Confusion matrix at the selected threshold.
10. Synthetic wallet payment and fraud-warning workflow.
11. Merchant QR and cashback workflow.
12. Analyst dashboard and suspicious-transaction feed.

### Tables

1. Dataset statistics.
2. Model hyperparameters.
3. Component ablation results.
4. Fusion threshold metrics.
5. GNN metrics.
6. Latency percentiles.
7. Manual system test matrix.
8. Threats to validity.

---

## 16. Reference List Template

The final submission should replace this template with the citation style required by the target venue.

1. IEEE-CIS Fraud Detection dataset documentation and competition description.
2. Elliptic Bitcoin transaction graph dataset publication or official dataset documentation.
3. Rumelhart, Hinton, and Williams. Learning internal representations by error propagation. Foundational autoencoder/backpropagation reference.
4. Vaswani et al. Attention Is All You Need. Transformer architecture reference.
5. Veličković et al. Graph Attention Networks. GAT architecture reference.
6. A relevant survey on machine-learning-based financial fraud detection.
7. A relevant survey on graph neural networks for fraud and risk analysis.
8. A relevant reference on federated learning and secure distributed model training.
9. FastAPI, PyTorch, PyTorch Geometric, SQLAlchemy, React, and Vite official documentation.
10. Any source used to justify threshold optimization, probability calibration, cost-sensitive learning, or fraud-detection evaluation methodology.

---

## Publication Checklist

Before submission:

- [ ] Re-run the final ML pipeline from a clean environment.
- [ ] Restore and checksum all protected model artifacts.
- [ ] Recalculate every metric from one canonical result file.
- [ ] Resolve the 3,035 versus 3,036 fraud-count inconsistency.
- [ ] Verify that threshold selection does not use the final test labels.
- [ ] Add exact train/validation/test split definitions.
- [ ] Add exact hardware and software versions.
- [ ] Add component ablation results.
- [ ] Add precision-recall and calibration analysis.
- [ ] Add confidence intervals.
- [ ] Clarify that the webapp uses precomputed outputs.
- [ ] Remove demo credentials from any public production deployment.
- [ ] Review privacy, ethics, and security claims.
- [ ] Replace the reference template with verified bibliographic entries.
- [ ] Have a domain expert review the final fraud-detection claims.
