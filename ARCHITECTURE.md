# FraudShieldAI: System Architecture

## High-Level System Design

```
┌──────────────────────────────────────────────────────────────────┐
│                          INPUT LAYER                             │
├──────────────────────────────────────────────────────────────────┤
│ IEEE-CIS Transaction Data        Elliptic Bitcoin Network         │
│ • 104,284 test transactions      • 203,769 nodes                  │
│ • 424 features each              • 468,710 edges                  │
│ • 2.91% fraud rate               • Network structure              │
└────────┬────────────────────────────────────────────────────────┬┘
         │                                                          │
         ▼                                                          ▼
┌──────────────────────────┐                    ┌──────────────────┐
│ TRANSACTION RISK ENGINE  │                    │ NETWORK          │
│                          │                    │ INTELLIGENCE     │
│ Feature Space Analysis   │                    │                  │
│ (Individual Behavior)    │                    │ Topology Analysis│
│                          │                    │ (Network Edges)  │
└────────┬────────┬────────┘                    └────────┬─────────┘
         │        │                                      │
         │        │ Parallel Processing                  │
         │        │                                      │
         ▼        ▼                                      ▼
    ┌────────────────┐                          ┌──────────────┐
    │  AUTOENCODER   │                          │  GNN (GAT)   │
    │  (20% Weight)  │                          │  (Separate)  │
    │                │                          │              │
    │ Anomaly via    │                          │ Node-level   │
    │ Reconstruction │                          │ fraud scores │
    │ Error          │                          │              │
    └────────┬───────┘                          └──────┬───────┘
             │                                         │
             ▼                                         ▼
       ┌──────────────┐                         ┌────────────────┐
       │AE Score:     │                         │GNN Scores:     │
       │Percentile(0-1)                         │Per-node (0-1)  │
       └──────┬───────┘                         │                │
              │                                 └────────┬───────┘
              │                                         │
         │────────────────────────────────────────────┘
         │ Fusion Only (TXN Score)
         ▼
    ┌──────────────┐
    │ TRANSFORMER  │
    │  (80% Weight)│
    │              │
    │ Behavioral   │
    │ Sequence     │
    │ Analysis     │
    └──────┬───────┘
           │
           ▼
      ┌──────────┐
      │TF Score: │
      │ Sigmoid  │
      │ (0-1)    │
      └────┬─────┘
           │
           ▼
      ┌────────────────────────────┐
      │ FUSION PREDICTION          │
      │                            │
      │ fused = 0.80*TF + 0.20*AE │
      │ is_flagged = fused >= 0.82│
      └────┬───────────────────────┘
           │
           ▼
      ┌──────────────────┐
      │  PREDICTIONS     │
      │  (104,284 TXNs)  │
      │  +  GNN Scores   │
      │  (203k Nodes)    │
      └────┬─────────────┘
           │
      ┌────┴───────────────────┐
      │                        │
      ▼                        ▼
   ┌──────────┐           ┌──────────────┐
   │ FastAPI  │           │ Dashboards   │
   │ Backend  │           │              │
   │ (7 API   │           │ • HTML UI    │
   │  routes) │           │ • Streamlit  │
   └────┬─────┘           └──────┬───────┘
        │                        │
        └────────────┬───────────┘
                     │
                     ▼
              ┌────────────────┐
              │  END USERS     │
              │                │
              │ Bank Analysts  │
              │ Risk Officers  │
              │ API Consumers  │
              └────────────────┘
```

---

## Detailed Component Architecture

### 1. Transaction Risk Engine

#### A. Autoencoder (Reconstruction-Based Anomaly Detection)

**Purpose**: Detect anomalous feature combinations that deviate from normal transaction patterns

**Architecture**:
```
Input (424 features)
    ↓
Linear(424 → 64) + ReLU
    ↓
Linear(64 → 32) + ReLU
    ↓
Linear(32 → 16) + ReLU
    ↓ [BOTTLENECK - 16-dim encoding]
    ↓
Linear(16 → 32) + ReLU
    ↓
Linear(32 → 64) + ReLU
    ↓
Linear(64 → 424)
    ↓
Output (424 reconstructed features)
```

**Training Logic**:
1. Train on normal transactions only (neg=0 from training set)
2. Minimize MSE between input and reconstruction: `loss = MSE(x, decoder(encoder(x)))`
3. Normal transactions → low reconstruction error
4. Fraudulent transactions → high reconstruction error (abnormal patterns)

**Inference Logic**:
```python
# For each test transaction:
reconstruction_error = MSE(transaction_features, reconstructed_features)

# Build reference distribution from all test transactions
reference_distribution = sort([error for each test transaction])

# Convert to percentile score (0-1)
ae_score = percentile_rank(reconstruction_error, reference_distribution)
```

**Why Separate from Fusion?**
- Captures feature-space anomalies (what's being transacted)
- Complements behavioral model (when/how it's being transacted)
- Only 20% weight (feature anomalies are weak signals alone)
- Examples: Unusual transaction amounts, rare feature combinations

---

#### B. Transformer (Behavioral Sequence Analysis)

**Purpose**: Analyze transaction sequences to detect behavioral deviations

**Architecture**:
```
Sequence of 15 transactions (time-ordered history)
    ↓
Linear Projection: (15, 424) → (15, 64)
    ↓
Positional Encoding: Add sinusoidal position information
    ↓ [Now: 15 positions, each 64-dim with position info]
    ↓
Transformer Encoder Layer 1 (4-head attention, d_ff=256)
    ├─ Self-Attention: Learn which previous txns matter for current
    ├─ Feed-Forward: Non-linear feature transformation
    └─ Layer Norm + Residual Connections
    ↓
Transformer Encoder Layer 2 (4-head attention, d_ff=256)
    ├─ Self-Attention: Refined patterns across sequence
    ├─ Feed-Forward: Further transformation
    └─ Layer Norm + Residual Connections
    ↓ [Now: Contextual encoding of full sequence]
    ↓
Sequence Pooling: (15, 64) → (64,)
    - Average pool with masking (handles variable lengths)
    - Only active sequence positions contribute
    ↓
Linear Classifier: (64,) → (1,)
    ↓
Sigmoid: Map to (0, 1) probability
    ↓
Output: tf_score ∈ [0, 1] (fraud probability)
```

**Key Concepts**:

1. **Positional Encoding** (Sinusoidal):
   ```python
   pe[t, 2i] = sin(t / 10000^(2i/d))
   pe[t, 2i+1] = cos(t / 10000^(2i/d))
   ```
   - Enables model to learn relative position importance
   - Supports variable-length sequences (up to 15)
   - Uniquely encodes each position

2. **Multi-Head Attention** (4 heads):
   ```
   Attention(Q, K, V) = softmax(QK^T / √d_k) V
   ```
   - Head 1: Captures transfer patterns
   - Head 2: Captures temporal dependencies
   - Head 3: Captures amount changes
   - Head 4: Captures feature changes
   - Output: Concatenate all heads

3. **Masking**:
   - Transactions at <15-step history: Masked
   - Only real historical transactions contribute
   - Prevents "looking forward" in time

**Training Logic**:
```python
# For each transaction (with 15-step history):
sequence = [tx[t-14], tx[t-13], ..., tx[t]]
mask = [1, 1, ..., 1] or [0, 0, 1, ..., 1]  (1=valid, 0=padding)
sequence_encoding = transformer(sequence, mask)
fraud_logit = classifier(sequence_encoding)
loss = BCE(sigmoid(fraud_logit), true_label)
```

**Why Transformer?**
- Captures sequential dependencies (how behavior changes)
- Attention reveals important features per position
- Positional encoding encodes temporal structure
- 80% weight (strongest fraud signal is behavioral deviation)

---

#### C. Fusion Strategy

**Why Two Models?**
1. **Autoencoder** detects static anomalies (unusual values)
2. **Transformer** detects dynamic anomalies (unusual sequences)
3. **Combined** catches both feature AND behavioral fraud

**Fusion Formula**:
```
fused_score = 0.80 * transformer_score + 0.20 * autoencoder_score

is_flagged = {
    TRUE   if fused_score >= threshold (0.8212)
    FALSE  otherwise
}
```

**Weight Justification**:
- **80% Transformer**: Behavioral patterns dominate fraud signals
  - Fraudsters adapt to individual systems (change features)
  - But behavioral patterns are consistent and detectable
- **20% Autoencoder**: Catches feature-space novelty
  - Unusual combinations even with normal values
  - Complements behavioral model
  - Low weight avoids false positives from rare but legitimate transactions

**Threshold Selection**:
- Tested 100 thresholds (0.5 to 1.0)
- Selected 0.8212 (optimal F1-score on validation set)
- Balances precision (75.9%) and recall (60.8%)

---

### 2. Network Intelligence (GNN)

**Purpose**: Identify suspicious Bitcoin transaction participants based on network topology

**Why Separate from Fusion?**
- Different modality (graph structure vs. transaction features)
- Different scale (203k nodes vs. 104k transactions)
- Different prediction target (network participant vs. individual txn)
- Can be combined later (e.g., if txn connects to high-risk node)

#### Graph Attention Network (GAT) Architecture

```
Input: Elliptic Bitcoin Network
├─ Nodes: 203,769 (transaction participants)
├─ Edges: 468,710 (transaction relationships)
└─ Features: 166 per node
    ↓
GAT Layer 1: Graph Attention
├─ Input: (N, 166)
├─ Attention Heads: 4
│  ├─ Head 1: Focuses on temporal patterns
│  ├─ Head 2: Focuses on transaction volume
│  ├─ Head 3: Focuses on mixing patterns
│  └─ Head 4: Focuses on anomalies
├─ Aggregation: Concatenate heads
└─ Output: (N, 64) per head, (N, 256) total
    ↓
GAT Layer 2: Graph Attention (Refined)
├─ Input: (N, 256)
├─ Attention Heads: 1 (single head in output layer)
├─ Learns refined fraud indicators
└─ Output: (N, 2) logits [legitimate_score, fraud_score]
    ↓
Softmax: Convert logits to probabilities
├─ P(legitimate) = softmax(logits)[0]
├─ P(fraud) = softmax(logits)[1]
└─ Output: 203,769 fraud scores ∈ [0, 1]
```

**Attention Mechanism** (per head):
```
For each node i and its neighbors N(i):
    1. Compute attention weights: a_ij = softmax(LeakyReLU(w^T[h_i || h_j]))
       - || is concatenation
       - w is learned weight vector
    2. Aggregate neighbor features: h'_i = σ(Σ_j a_ij W h_j)
       - σ is activation function (ReLU)
       - W is learned transformation matrix
    3. Result: Each node considers weighted sum of neighbor features
```

**Why Attention?**
- Different neighbors have different importance
- Learns which network patterns indicate fraud
- More powerful than simple averaging

**Training Process**:
```python
# Using ~20,000 labeled nodes (10% of graph)
for each batch of labeled nodes:
    predictions = gnn(features, edges)
    loss = cross_entropy(predictions, labels) + reconstruction_loss
    backward_pass()
    update_weights()

# Inference: Apply to all 203,769 nodes
predictions = gnn(all_features, all_edges)
```

**Output**: Per-node fraud probability

---

### 3. Prediction Pipeline

**Complete Flow for Single Transaction**:

```
Input: Transaction ID (e.g., 3301550)
    ↓
Step 1: Load Transaction Features
├─ Features: 424-dim vector
├─ History: Previous 14 transactions
└─ Mask: Which positions are valid
    ↓
Step 2: Autoencoder Scoring
├─ Forward through encoder: features → 16-dim
├─ Forward through decoder: 16-dim → reconstructed features
├─ Compute MSE: ||features - reconstructed||^2
├─ Compute percentile: rank in reference distribution
└─ Output: ae_score ∈ [0, 1]
    ↓
Step 3: Transformer Scoring
├─ Embed sequence: (15, 424) → (15, 64)
├─ Add positional encoding
├─ Forward through 2 encoder layers
├─ Pool over sequence with masking
├─ Linear classifier → logit
├─ Sigmoid → probability
└─ Output: tf_score ∈ [0, 1]
    ↓
Step 4: Fusion Calculation
├─ fused_score = 0.80 * tf_score + 0.20 * ae_score
├─ Check threshold: fused_score >= 0.8212
└─ Output: flagged ∈ {TRUE, FALSE}
    ↓
Step 5: GNN Lookup (Optional)
├─ If transaction node in graph:
│  └─ Retrieve pre-computed GNN fraud score
├─ Output: gnn_score ∈ [0, 1]
└─ Could be used for further context
    ↓
Step 6: Generate Explanation
├─ If ae_score > 0.7: "Unusual transaction features"
├─ If tf_score > 0.7: "Suspicious behavioral pattern"
├─ If both high: "Multiple fraud indicators"
├─ If both low: "No strong indicators"
└─ Output: explanation_text
    ↓
Output: {
    transaction_id: 3301550,
    autoencoder_score: 0.1439,
    transformer_score: 0.4498,
    fused_score: 0.3886,
    flagged: false,
    gnn_score: 0.23,
    explanation: "No strong individual model trigger..."
}
```

**Latency Breakdown** (benchmark results):
- Autoencoder: 2.0 ms
- Transformer: 3.5 ms
- Fusion: <0.1 ms
- Response serialization: 1.0 ms
- **Total: ~6.5 ms average**

---

## 4. API Layer (FastAPI)

```
┌─────────────────────────────────────────────────────────┐
│              FastAPI Application (09_api.py)            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Initialization:                                         │
│ ├─ Load autoencoder_model.pt → ae_model                │
│ ├─ Load transformer_model.pt → tf_model                │
│ ├─ Load gnn_model.pt → gnn_model                        │
│ ├─ Load fusion_results.csv → 104k predictions           │
│ ├─ Load elliptic_graph.pt → 203k node graph             │
│ └─ Build ID→row mappings for fast lookup                │
│                                                         │
│ Endpoints:                                              │
│ ├─ GET / → {"message": "FraudShield API"}             │
│ ├─ GET /health → {"status": "ok"}                      │
│ ├─ GET /transactions/sample → Random 15 TXNs           │
│ ├─ GET /predict_by_id/{id} → Score + Details          │
│ ├─ POST /predict → Same as /predict_by_id              │
│ ├─ GET /gnn/suspicious → Top 100 fraud nodes           │
│ └─ GET /gnn/subgraph/{id} → Node's neighborhood       │
│                                                         │
│ Response Format:                                        │
│ {                                                       │
│   "transaction_id": int,                                │
│   "autoencoder_score": float,                           │
│   "transformer_score": float,                           │
│   "fused_score": float,                                 │
│   "flagged": bool,                                      │
│   "explanation": str,                                   │
│   "latency_ms": float                                   │
│ }                                                       │
└─────────────────────────────────────────────────────────┘
```

**Concurrency Model**:
- Async request handling (FastAPI default)
- Pre-loaded models (shared across requests)
- In-memory caching of results
- Supports ~1000s requests/min on standard hardware

---

## 5. Frontend Layer

### A. HTML Dashboard (11_bank_dashboard.html)

```
┌──────────────────────────────────────────────┐
│         HTML Dashboard (Browser)             │
├──────────────────────────────────────────────┤
│                                              │
│  Metrics Panel (Top)                         │
│  ├─ Transactions Scored: 104,284             │
│  ├─ High-Risk Alerts: 1,847                  │
│  ├─ Average Risk Score: 0.245                │
│  └─ Avg Latency: 6.99ms                      │
│                                              │
│  Transaction Loader (Left)                   │
│  ├─ Button: Load & Analyze (15 samples)      │
│  ├─ Fetches: /transactions/sample?limit=15   │
│  └─ Display: Transaction ID list             │
│                                              │
│  Risk Gauge (Center)                         │
│  ├─ D3.js gauge visualization                │
│  ├─ Scale: SAFE → MODERATE → HIGH            │
│  └─ Updates: On analysis                     │
│                                              │
│  Analysis Results (Right)                    │
│  ├─ Transaction Table                        │
│  │  ├─ TXN ID                                │
│  │  ├─ AE Score                              │
│  │  ├─ TF Score                              │
│  │  ├─ Fused Score                           │
│  │  ├─ Risk Level                            │
│  │  ├─ True Label (Ground Truth)             │
│  │  └─ Latency                               │
│  └─ Color Coding: Green/Yellow/Red           │
│                                              │
│  Live Analysis Area (Bottom)                 │
│  ├─ Selected transaction details             │
│  ├─ Explanation text                         │
│  └─ Prediction confidence                    │
│                                              │
└──────────────────────────────────────────────┘
```

**Data Flow**:
```
Click "Load & Analyze" → GET /transactions/sample 
    ↓
Display transaction IDs
    ↓
Click on transaction ID
    ↓
GET /predict_by_id/{id} → Score details
    ↓
Update gauge, table, explanation
```

### B. Streamlit Dashboard (10_dashboard.py)

```
┌────────────────────────────────────────┐
│     Streamlit Analytics Dashboard      │
├────────────────────────────────────────┤
│                                        │
│ Section 1: Architecture                │
│ ├─ System diagram                      │
│ ├─ Component roles                     │
│ └─ Data flow visualization             │
│                                        │
│ Section 2: Dataset Statistics          │
│ ├─ Transaction count: 104,284          │
│ ├─ Features: 424 dimensions            │
│ ├─ Fraud rate: 2.91%                   │
│ └─ Class distribution                  │
│                                        │
│ Section 3: Hybrid Fusion Results       │
│ ├─ Score histogram (legitimate)        │
│ ├─ Score histogram (fraud)             │
│ ├─ Threshold visualization (0.8212)    │
│ └─ Confusion matrix                    │
│                                        │
│ Section 4: Autoencoder Analysis        │
│ ├─ Reconstruction error distribution   │
│ ├─ Training loss curve                 │
│ └─ Sample reconstructions              │
│                                        │
│ Section 5: Transformer Analysis        │
│ ├─ Sequence predictions                │
│ ├─ Training history                    │
│ └─ Attention weight visualization      │
│                                        │
│ Section 6: GNN Results                 │
│ ├─ Node count: 203,769                 │
│ ├─ Edge count: 468,710                 │
│ ├─ Subgraph selector (interactive)     │
│ ├─ Selected subgraph visualization     │
│ └─ Node fraud scores                   │
│                                        │
│ Section 7: Model Comparison            │
│ ├─ ROC curves (all models)             │
│ ├─ Precision-Recall curves             │
│ ├─ F1-score comparison                 │
│ └─ Confusion matrices                  │
│                                        │
│ Section 8: Federated Learning          │
│ ├─ Distributed training simulation     │
│ ├─ Accuracy convergence                │
│ ├─ Aggregation strategy (median)       │
│ └─ Privacy preservation                │
│                                        │
└────────────────────────────────────────┘
```

**Data Loading**:
```python
# Cached loading (Streamlit optimization)
@st.cache_data
def load_fusion_data():
    df = pd.read_csv("fusion_results.csv")
    return df

# Interactive features
subgraph_node_id = st.slider("Select node", 0, 203769)
subgraph = extract_subgraph(graph, node_id)
st.plotly_chart(plot_subgraph(subgraph))
```

---

## 6. Data & Model Management

### Model Storage & Loading

```
Model Files (Pre-trained, Read-only)
├── autoencoder_model.pt (239.4 KB)
│   ├─ encoder: Linear layers (424→64→32→16)
│   ├─ decoder: Linear layers (16→64→32→424)
│   └─ No training during Phase 4
│
├── transformer_model.pt (511.4 KB)
│   ├─ input_proj: Linear(424→64)
│   ├─ pos_encoding: PositionalEncoding(d=64, max_len=15)
│   ├─ encoder: TransformerEncoder (2 layers, 4 heads)
│   ├─ classifier: Linear(64→1)
│   └─ No training during Phase 4
│
└── gnn_model.pt (237.4 KB)
    ├─ gat1: GATConv(166→64, heads=4)
    ├─ gat2: GATConv(256→64, heads=1)
    ├─ output: Linear(64→2)
    └─ No training during Phase 4
```

### Result Caching

```
Cached Results (Pre-computed)
├── fusion_results.csv (104,284 rows)
│   ├─ TransactionID
│   ├─ true_label
│   ├─ autoencoder_score
│   ├─ transformer_score
│   └─ fused_score
│
├── autoencoder_examples.csv (sample predictions)
├── transformer_examples.csv (sample predictions)
└── gnn_examples.csv (sample node predictions)
```

**Why Pre-compute?**
- Eliminates inference latency on each request
- API returns cached results instantly
- Only 6.99ms for model-based scoring when requested
- Reproducibility: Same results across all runs

---

## 7. Deployment Architecture

### Standalone Mode (Current)
```
┌─────────────────────────────────────┐
│   Single Machine Deployment         │
├─────────────────────────────────────┤
│                                     │
│ Process 1: FastAPI Server           │
│ ├─ Port: 8000                       │
│ ├─ Models in memory                 │
│ └─ Processes requests               │
│                                     │
│ Process 2: Streamlit Server         │
│ ├─ Port: 8501                       │
│ ├─ Data cached in memory            │
│ └─ Serves analytics dashboard       │
│                                     │
│ Browser:                            │
│ ├─ HTML dashboard (file://)         │
│ ├─ Calls API on localhost:8000      │
│ └─ Streamlit on localhost:8501      │
│                                     │
└─────────────────────────────────────┘
```

### Production Architecture (Conceptual)
```
┌──────────────────────────────────────────────┐
│         Load Balancer (NGINX)                │
└────────────────┬─────────────────────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
        ▼        ▼        ▼
    ┌────────┬────────┬────────┐
    │ FastAPI1│FastAPI2│FastAPI3│ (3 replicas)
    │ :8000  │ :8001  │ :8002  │
    ├────────┼────────┼────────┤
    │Models in memory (shared cache)
    └────────┬────────┬────────┘
             │        │
        ┌────┴────┬───┘
        │         │
        ▼         ▼
    ┌─────────┐ ┌──────────┐
    │Database │ │Redis     │ (optional caching)
    │(results)│ │(sessions)│
    └─────────┘ └──────────┘
```

---

## 8. Key Design Decisions

### Why Separate Models?

| Model | Modality | Focus | Weight | Why Separate |
|-------|----------|-------|--------|--------------|
| Autoencoder | Features | Anomalies | 20% | Weak signal alone |
| Transformer | Sequences | Behavior | 80% | Primary signal |
| GNN | Graph | Network | Separate | Different scale/target |

### Why This Fusion Strategy?

1. **Weighted Average** (vs. voting)
   - Preserves probability calibration
   - Smooth gradation in risk score
   - Easier threshold optimization

2. **80/20 Split** (vs. equal)
   - Behavioral fraud is most common
   - Feature anomalies occur in legitimate transactions
   - Empirically optimal on validation set

3. **Static Threshold** (vs. adaptive)
   - Reproducibility: Same decision for same inputs
   - Compliance: Predictable behavior for auditing
   - Operational: Simple to explain and adjust

### Why Transformer Over LSTM?

| Aspect | Transformer | LSTM |
|--------|-------------|------|
| Parallelization | ✅ All positions simultaneous | ❌ Sequential |
| Long-range dependencies | ✅ Direct via attention | ⚠️ Gradient issues |
| Interpretability | ✅ Attention weights visible | ❌ Hidden state opaque |
| Training time | ✅ Faster (parallel) | ❌ Slower (sequential) |
| Modern implementations | ✅ Optimized libraries | ⚠️ Less optimized |

### Why GNN For Network?

| Aspect | GNN | Other Options |
|--------|-----|----------------|
| Node relationships | ✅ Explicit via edges | ❌ Treat independently |
| Neighborhood context | ✅ Multi-hop aggregation | ❌ No local context |
| Scalability | ✅ O(n + m) complexity | ⚠️ O(n²) alternatives |
| Explainability | ✅ Neighbor importance via attention | ❌ Black box |

---

## 9. Data Flow Diagrams

### Training Data Flow (Phases 1-3)
```
IEEE-CIS Raw Data (590,540 TXNs)
    ↓ [Phase 1: data_prep]
Features (590,540 x 424)
    ├─→ [Phase 2: autoencoder] → autoencoder_model.pt
    ├─→ [Phase 3: transformer] → transformer_model.pt
    └─→ [Phase 5: elliptic_prep] →─────┐
                                        ↓
                              Elliptic Graph
                                        ↓
                          [Phase 6: gnn] →gnn_model.pt
```

### Inference Data Flow (Phase 4+)
```
Test Transaction (424 features)
    ├─→ Autoencoder → ae_score
    ├─→ Transformer → tf_score
    └─→ Fusion → fused_score → is_flagged
              ↓
        FastAPI /predict
              ↓
    HTML Dashboard
    Streamlit Dashboard
```

---

## 10. System Constraints & Trade-offs

### Performance vs Accuracy
- **Choice**: Latency <10ms takes priority
- **Trade-off**: Slightly lower accuracy possible with larger models
- **Rationale**: Fraud detection needs real-time response

### Model Complexity vs Interpretability
- **Choice**: Use attention-based models (medium complexity)
- **Trade-off**: More complex than linear models, less than ensemble
- **Rationale**: Attention weights provide some explainability

### Centralized vs Distributed
- **Choice**: Centralized for Phase 4, distributed for future
- **Trade-off**: Simpler architecture now, privacy concern later
- **Rationale**: Federated learning stub provided as PoC

---

## Summary

FraudShieldAI implements a **two-track** fraud detection architecture:

1. **Transaction Risk Engine** (Primary):
   - Autoencoder: Feature anomalies (20%)
   - Transformer: Behavioral deviations (80%)
   - Fused score for real-time individual transaction scoring

2. **Network Intelligence** (Supplementary):
   - GNN: Bitcoin transaction network topology
   - Separate predictions for network-level fraud indicators
   - Can be integrated with transaction scores for comprehensive risk

This design balances **accuracy, interpretability, and performance** while providing a foundation for distributed, privacy-preserving fraud detection systems.

---

*Architecture documentation for FraudShieldAI Phase 4 Completion*  
*Last Updated: Final Phase 4 Architecture Review*
