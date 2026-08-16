"""
<<<<<<< HEAD
FraudShieldAI API — serves precomputed fraud scores from the trained
Autoencoder + Transformer fusion pipeline, plus a UPI demo app and
bank analyst dashboard.

-----------------------------------------------------------------------------
📌 DATASET SIMULATION NOTE:
This API and interactive demo layer run a simulation based on precomputed fraud
scores from the IEEE-CIS Fraud Detection dataset (590,540 real transactions)
and the Elliptic Bitcoin Graph Dataset for GNN network visualizations.
-----------------------------------------------------------------------------

USER PROFILES & ASSIGNED ROLES:
- faris:  Faris (faris@fsaipay)  -> Regular Personal Account (Standard personal behavior)
- rahul:  Rahul (rahul@fsaipay)  -> Frequent Peer Transfers (High-frequency P2P user)
- ahmed:  Ahmed (ahmed@fsaipay)  -> Retail Merchant Account (Small business transactions)
- priya:  Priya (priya@fsaipay)  -> Corporate High-Volume (Large batch transfer profile)
- ananya: Ananya (ananya@fsaipay) -> Freelance / International (Cross-border payments)
- arjun:  Arjun (arjun@fsaipay)  -> New Account (Low Behavioral History) (Unverified sequence)
- kiran:  Kiran (kiran@fsaipay)  -> Whitelisted E-Commerce (Verified e-commerce entity)
- neha:   Neha (neha@fsaipay)   -> High-Velocity Account (Frequent transaction spikes)

Run:  .venv_new\Scripts\python -m uvicorn 09_api:app --reload
Docs: http://127.0.0.1:8000/docs
"""

import random
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# App Metadata
# ---------------------------------------------------------------------------

API_DESCRIPTION = """
### FraudShieldAI Real-Time Hybrid AI Fraud Detection System
=======
FastAPI backend for the frozen FraudShieldAI inference stack.

Run:
    uvicorn 09_api:app --reload

This file only loads existing artifacts. It does not train, overwrite weights,
or modify the saved hybrid-fusion results.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator

DEVICE = torch.device("cpu")
DATA_DIR = Path("data")
SEQ_LEN = 15

# Recovered from the existing fusion_results.csv written by 07_hybrid_fusion.py.
# fused_score = 0.80 * transformer_score + 0.20 * autoencoder_score
W_TRANSFORMER = 0.80
W_AUTOENCODER = 0.20
FUSION_THRESHOLD = 0.8212121212121212
>>>>>>> 3447f33951478a736038feda72194f1fd45fa9e0

📌 **Dataset Simulation Note**:
This API is an interactive demo simulation. Payment requests evaluate real precomputed fraud scores 
sampled from actual transactions in the **IEEE-CIS Fraud Detection dataset** (590,540 transactions). 
Graph network subgraphs are built from the **Elliptic Bitcoin Dataset**.

<<<<<<< HEAD
#### User Profiles Configured (`/pay` endpoint):
* `faris` — **Faris**: Regular Personal Account (`faris@fsaipay`)
* `rahul` — **Rahul**: Frequent Peer Transfers (`rahul@fsaipay`)
* `ahmed` — **Ahmed**: Retail Merchant Account (`ahmed@fsaipay`)
* `priya` — **Priya**: Corporate High-Volume (`priya@fsaipay`)
* `ananya` — **Ananya**: Freelance / International (`ananya@fsaipay`)
* `arjun` — **Arjun**: New Account (Low Behavioral History) (`arjun@fsaipay`)
* `kiran` — **Kiran**: Whitelisted E-Commerce (`kiran@fsaipay`)
* `neha` — **Neha**: High-Velocity Account (`neha@fsaipay`)
"""

app = FastAPI(
    title="FraudShieldAI API",
    version="1.0.0",
    description=API_DESCRIPTION,
)
=======
class Autoencoder(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, 16), nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(16, 32), nn.ReLU(),
            nn.Linear(32, 64), nn.ReLU(),
            nn.Linear(64, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))
>>>>>>> 3447f33951478a736038feda72194f1fd45fa9e0

# ---------------------------------------------------------------------------
# Load precomputed scores at startup
# ---------------------------------------------------------------------------

<<<<<<< HEAD
_FUSION_DF: pd.DataFrame | None = None
_GNN_DF: pd.DataFrame | None = None

try:
    _FUSION_DF = pd.read_csv("fusion_results.csv")
    _FUSION_DF["TransactionID"] = _FUSION_DF["TransactionID"].astype(str)
    _FUSION_DF.set_index("TransactionID", inplace=True)
except FileNotFoundError:
    print("WARNING: fusion_results.csv not found — /predict_by_id will return 404s")

try:
    _GNN_DF = pd.read_csv("gnn_examples.csv")
except FileNotFoundError:
    print("WARNING: gnn_examples.csv not found — GNN data unavailable")


# Fusion weights (from 07_hybrid_fusion.py grid-search output)
W_TRANSFORMER = 0.55
W_AUTOENCODER = 0.45
FUSION_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_explanation(ae_score: float, tf_score: float) -> list[str]:
    contributors: list[str] = []
    if ae_score > 0.7:
        contributors.append("high reconstruction error (statistically unusual transaction)")
    if tf_score > 0.7:
        contributors.append("deviates from this user's normal behavioral pattern")
    if not contributors:
        contributors.append("no single layer strongly triggered — flagged on combined score")
    return contributors


# Synthetic user profiles for the /pay demo with explicit roles & behavioral attributes
_PROFILES = {
    "faris":  {"name": "Faris",  "role": "Regular Personal Account", "upi": "faris@fsaipay",  "avatar": "👨‍💼"},
    "rahul":  {"name": "Rahul",  "role": "Frequent Peer Transfers",  "upi": "rahul@fsaipay",  "avatar": "👨‍💻"},
    "ahmed":  {"name": "Ahmed",  "role": "Retail Merchant Account",  "upi": "ahmed@fsaipay",  "avatar": "👨"},
    "priya":  {"name": "Priya",  "role": "Corporate High-Volume",    "upi": "priya@fsaipay",  "avatar": "👩‍💼"},
    "ananya": {"name": "Ananya", "role": "Freelance / International","upi": "ananya@fsaipay", "avatar": "👩‍💻"},
    "arjun":  {"name": "Arjun",  "role": "New Account (Low History)","upi": "arjun@fsaipay",  "avatar": "👨‍🎨"},
    "kiran":  {"name": "Kiran",  "role": "Whitelisted E-Commerce",   "upi": "kiran@fsaipay",  "avatar": "👩"},
    "neha":   {"name": "Neha",   "role": "High-Velocity Account",    "upi": "neha@fsaipay",   "avatar": "👩‍🔬"},
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health():
    """Health check with loaded transaction count."""
    count = len(_FUSION_DF) if _FUSION_DF is not None else 0
    return {"status": "ok", "transactions_loaded": count}


class PayRequest(BaseModel):
    sender: str = Field(..., description="Sender profile id, e.g. 'faris'")
    receiver: str = Field(..., description="Receiver profile id, e.g. 'rahul'")
    amount: float = Field(default=500.0, description="Payment amount (INR)")


@app.post("/pay", tags=["Payments"])
def pay(req: PayRequest):
    """Simulate a UPI payment and return a fraud verdict."""
    if req.sender not in _PROFILES:
        return JSONResponse(status_code=400, content={"error": f"Unknown sender '{req.sender}'"})
    if req.receiver not in _PROFILES:
        return JSONResponse(status_code=400, content={"error": f"Unknown receiver '{req.receiver}'"})
    if req.sender == req.receiver:
        return JSONResponse(status_code=400, content={"error": "Sender and receiver must differ"})

    if _FUSION_DF is None or _FUSION_DF.empty:
        return JSONResponse(status_code=503, content={"error": "Score database not loaded"})

    # Pick a representative transaction from the precomputed scores
    row = _FUSION_DF.sample(n=1, random_state=hash(f"{req.sender}-{req.receiver}-{req.amount}") % (2**31))
    rec = row.iloc[0]

    ae_score = float(rec["autoencoder_score"])
    tf_score = float(rec["transformer_score"])
    fused = float(rec["fused_score"])
    flagged = fused >= FUSION_THRESHOLD
=======
class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = SEQ_LEN):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]


class BehavioralTransformer(nn.Module):
    def __init__(self, input_dim: int, d_model: int = 64, nhead: int = 4, num_layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoding = PositionalEncoding(d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Linear(d_model, 1)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        h = self.input_proj(x)
        h = self.pos_encoding(h)
        h = self.encoder(h, src_key_padding_mask=(mask == 0))
        mask_exp = mask.unsqueeze(-1)
        pooled = (h * mask_exp).sum(dim=1) / mask_exp.sum(dim=1).clamp(min=1)
        return self.classifier(pooled).squeeze(-1)


class GAT(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, heads: int = 4, dropout: float = 0.3, num_classes: int = 2):
        super().__init__()
        from torch_geometric.nn import GATConv

        self.gat1 = GATConv(input_dim, hidden_dim, heads=heads, dropout=dropout)
        self.gat2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, concat=False, dropout=dropout)
        self.classifier = nn.Linear(hidden_dim, num_classes)
        self.dropout = dropout

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        import torch.nn.functional as F

        h = F.elu(self.gat1(x, edge_index))
        h = F.dropout(h, p=self.dropout, training=self.training)
        h = F.elu(self.gat2(h, edge_index))
        return self.classifier(h)


class RuntimeState:
    def __init__(self) -> None:
        self.features: np.ndarray | None = None
        self.window_indices: np.ndarray | None = None
        self.mask: np.ndarray | None = None
        self.labels: np.ndarray | None = None
        self.transaction_ids: np.ndarray | None = None
        self.fusion_results: pd.DataFrame | None = None
        self.id_to_row: dict[int, int] = {}
        self.ae_reference_raw: np.ndarray | None = None
        self.input_dim: int | None = None
        self.ae_model: Autoencoder | None = None
        self.tf_model: BehavioralTransformer | None = None
        self.gnn_model: nn.Module | None = None
        self.gnn_graph: dict[str, torch.Tensor] | None = None
        self.gnn_predictions: pd.DataFrame | None = None
        self.load_errors: dict[str, str] = {}


state = RuntimeState()


def validate_vector(values: list[float], expected_len: int, field_name: str) -> None:
    if len(values) != expected_len:
        raise ValueError(f"{field_name} must contain exactly {expected_len} numeric values")
    for value in values:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"{field_name} must contain only numeric values")
        if not math.isfinite(float(value)):
            raise ValueError(f"{field_name} must not contain NaN or Inf")


class TransactionRequest(BaseModel):
    features: list[float] = Field(..., description="424 preprocessed feature values, same order as data/features.npy")
    sequence: list[list[float]] = Field(..., description="15 transaction feature vectors, padded if needed")
    sequence_mask: list[float] = Field(..., description="15 values: 1 for real sequence rows, 0 for padding")

    @model_validator(mode="after")
    def validate_numeric_payload(self) -> "TransactionRequest":
        expected_dim = state.input_dim
        if expected_dim is None:
            raise ValueError("API feature dimension is unavailable because processed data did not load.")
        validate_vector(self.features, expected_dim, "features")
        if len(self.sequence) != SEQ_LEN:
            raise ValueError(f"sequence must contain exactly {SEQ_LEN} rows")
        for i, row in enumerate(self.sequence):
            validate_vector(row, expected_dim, f"sequence[{i}]")
        validate_vector(self.sequence_mask, SEQ_LEN, "sequence_mask")
        if any(value not in (0, 0.0, 1, 1.0) for value in self.sequence_mask):
            raise ValueError("sequence_mask values must be 0 or 1")
        if sum(self.sequence_mask) <= 0:
            raise ValueError("sequence_mask must contain at least one real row")
        return self


app = FastAPI(title="FraudShieldAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def load_state_dict(path: str) -> dict[str, Any]:
    try:
        return torch.load(path, map_location=DEVICE, weights_only=True)
    except TypeError:
        return torch.load(path, map_location=DEVICE)


@torch.no_grad()
def score_autoencoder_batch(features: np.ndarray, batch_size: int = 4096) -> np.ndarray:
    require_model(state.ae_model, "Autoencoder")
    errors = []
    for i in range(0, len(features), batch_size):
        batch = torch.tensor(features[i:i + batch_size], dtype=torch.float32, device=DEVICE)
        recon = state.ae_model(batch)
        errors.append(torch.mean((batch - recon) ** 2, dim=1).cpu().numpy())
    return np.concatenate(errors)

>>>>>>> 3447f33951478a736038feda72194f1fd45fa9e0

def load_runtime() -> None:
    try:
        state.features = np.load(DATA_DIR / "features.npy", mmap_mode="r")
        state.window_indices = np.load(DATA_DIR / "window_indices.npy", mmap_mode="r")
        state.mask = np.load(DATA_DIR / "mask.npy", mmap_mode="r")
        state.labels = np.load(DATA_DIR / "labels.npy", mmap_mode="r")
        state.transaction_ids = np.load(DATA_DIR / "transaction_ids.npy", mmap_mode="r")
        state.input_dim = int(state.features.shape[1])
    except Exception as exc:
        state.load_errors["data"] = str(exc)

    try:
        state.fusion_results = pd.read_csv("fusion_results.csv")
    except Exception as exc:
        state.load_errors["fusion_results"] = str(exc)

    if state.transaction_ids is not None and state.fusion_results is not None:
        id_to_row = {int(tx_id): i for i, tx_id in enumerate(state.transaction_ids)}
        fusion_ids = state.fusion_results["TransactionID"].astype(int).tolist()
        state.id_to_row = {tx_id: id_to_row[tx_id] for tx_id in fusion_ids if tx_id in id_to_row}

    if state.input_dim is not None:
        try:
            ae_model = Autoencoder(state.input_dim).to(DEVICE)
            ae_model.load_state_dict(load_state_dict("autoencoder_model.pt"))
            ae_model.eval()
            state.ae_model = ae_model
        except Exception as exc:
            state.load_errors["autoencoder"] = str(exc)

        try:
            tf_model = BehavioralTransformer(state.input_dim).to(DEVICE)
            tf_model.load_state_dict(load_state_dict("transformer_model.pt"))
            tf_model.eval()
            state.tf_model = tf_model
        except Exception as exc:
            state.load_errors["transformer"] = str(exc)

    try:
        gnn_state = load_state_dict("gnn_model.pt")
        gat1_weight = gnn_state["gat1.lin.weight"]
        gnn_model = GAT(input_dim=int(gat1_weight.shape[1])).to(DEVICE)
        gnn_model.load_state_dict(gnn_state)
        gnn_model.eval()
        state.gnn_model = gnn_model
    except Exception as exc:
        state.load_errors["gnn"] = str(exc)

    try:
        graph = torch.load(DATA_DIR / "elliptic_graph.pt", map_location=DEVICE, weights_only=False)
        state.gnn_graph = {
            "x": graph["x"].to(DEVICE),
            "edge_index": graph["edge_index"].to(DEVICE),
            "y": graph["y"].to(DEVICE),
            "timestep": graph["timestep"].to(DEVICE),
        }
    except Exception as exc:
        state.load_errors["gnn_graph"] = str(exc)

    if state.ae_model is not None and state.features is not None and state.id_to_row:
        try:
            rows = np.fromiter(state.id_to_row.values(), dtype=np.int64)
            raw_errors = score_autoencoder_batch(state.features[rows])
            state.ae_reference_raw = np.sort(raw_errors)
        except Exception as exc:
            state.load_errors["autoencoder_reference"] = str(exc)


def require_model(model: nn.Module | None, name: str) -> None:
    if model is None:
        detail = state.load_errors.get(name.lower(), f"{name} model is not loaded")
        raise HTTPException(status_code=503, detail=detail)


def require_data() -> None:
    if any(value is None for value in [state.features, state.window_indices, state.mask, state.labels, state.transaction_ids]):
        raise HTTPException(status_code=503, detail=state.load_errors.get("data", "Processed inference data is not loaded"))


def require_gnn() -> None:
    require_model(state.gnn_model, "GNN")
    if state.gnn_graph is None:
        raise HTTPException(status_code=503, detail=state.load_errors.get("gnn_graph", "Elliptic graph is not loaded"))


def percentile_of_raw_error(raw_error: float) -> float:
    if state.ae_reference_raw is None or len(state.ae_reference_raw) == 0:
        raise HTTPException(status_code=503, detail="Autoencoder reference distribution is not available")
    return float(np.searchsorted(state.ae_reference_raw, raw_error, side="right") / len(state.ae_reference_raw))


def fused_score(ae_score: float, tf_score: float) -> float:
    return W_TRANSFORMER * tf_score + W_AUTOENCODER * ae_score


def explanation_for_scores(ae_score: float, tf_score: float) -> str:
    ae_high = ae_score >= 0.7
    tf_high = tf_score >= 0.7
    if ae_high and tf_high:
        return "Behavioral deviation and statistical anomaly detected."
    if ae_high:
        return "Statistically unusual transaction pattern detected."
    if tf_high:
        return "Transaction deviates from the learned behavioral pattern."
    return "No strong individual model trigger; decision is based on the fused risk score."


def saved_fusion_scores(transaction_id: int) -> dict[str, float] | None:
    if state.fusion_results is None:
        return None
    rows = state.fusion_results[state.fusion_results["TransactionID"].astype(int) == transaction_id]
    if rows.empty:
        return None
    row = rows.iloc[0]
    return {
<<<<<<< HEAD
        "transaction_id": row.index[0],
        "sender": _PROFILES[req.sender],
        "receiver": _PROFILES[req.receiver],
        "amount": req.amount,
        "currency": "INR",
        "fused_score": round(fused, 4),
        "flagged": flagged,
        "status": "BLOCKED" if flagged else "COMPLETED",
        "autoencoder_score": round(ae_score, 4),
        "transformer_score": round(tf_score, 4),
        "explanation": _build_explanation(ae_score, tf_score),
    }


@app.get("/predict_by_id", tags=["Prediction"])
def predict_by_id(transaction_id: str = Query(..., description="TransactionID from the scored dataset")):
    """Look up precomputed fraud scores for a transaction by its ID."""
    if _FUSION_DF is None:
        return JSONResponse(status_code=503, content={"error": "Score database not loaded"})

    tid = str(transaction_id)
    if tid not in _FUSION_DF.index:
        return JSONResponse(status_code=404, content={"error": f"Transaction '{tid}' not found"})

    rec = _FUSION_DF.loc[tid]
    ae_score = float(rec["autoencoder_score"])
    tf_score = float(rec["transformer_score"])
    fused = float(rec["fused_score"])

    return {
        "transaction_id": tid,
        "true_label": int(rec["true_label"]),
        "fused_score": round(fused, 4),
        "flagged": fused >= FUSION_THRESHOLD,
        "autoencoder_score": round(ae_score, 4),
        "transformer_score": round(tf_score, 4),
        "explanation": _build_explanation(ae_score, tf_score),
    }


@app.get("/api/dashboard_stats", tags=["Dashboard"])
def dashboard_stats():
    """Return summary stats and top risky transactions for the dashboard."""
    if _FUSION_DF is None or _FUSION_DF.empty:
         return JSONResponse(status_code=503, content={"error": "Score database not loaded"})
    
    total_tx = len(_FUSION_DF)
    # Using a placeholder threshold of 0.5 (or median) for flagged count
    flagged_df = _FUSION_DF[_FUSION_DF["fused_score"] >= FUSION_THRESHOLD]
    flagged_count = len(flagged_df)
    fraud_rate = float(_FUSION_DF["true_label"].mean())
    avg_score = float(_FUSION_DF["fused_score"].mean())

    top_flagged = flagged_df.sort_values("fused_score", ascending=False).head(20)
    recent_transactions = []
    for tid, row in top_flagged.iterrows():
        recent_transactions.append({
            "transaction_id": tid,
            "true_label": int(row["true_label"]),
            "autoencoder_score": round(float(row["autoencoder_score"]), 4),
            "transformer_score": round(float(row["transformer_score"]), 4),
            "fused_score": round(float(row["fused_score"]), 4)
        })

    return {
        "total_transactions": total_tx,
        "flagged_count": flagged_count,
        "fraud_rate": fraud_rate,
        "avg_fused_score": round(avg_score, 4),
        "recent_flagged": recent_transactions
    }



# ---------------------------------------------------------------------------
# GNN subgraph endpoint (Task 3)
# ---------------------------------------------------------------------------

@app.get("/api/gnn_graph", tags=["GNN"])
def gnn_graph():
    """
    Return a small illustrative fraud-ring subgraph built from gnn_examples.csv
    plus synthetic neighbor nodes, for Plotly.js visualization.
    """
    if _GNN_DF is None or _GNN_DF.empty:
        return JSONResponse(status_code=503, content={"error": "GNN data not available"})

    rng = random.Random(42)
    nodes = []
    edges = []
    seen_ids = set()

    # Add flagged nodes from gnn_examples.csv
    for _, row in _GNN_DF.iterrows():
        nid = int(row["node_idx"])
        nodes.append({
            "id": nid,
            "true_label": int(row["true_label"]),
            "predicted_prob": round(float(row["predicted_prob"]), 4),
            "predicted_label": int(row["predicted_label"]),
            "example_type": row["example_type"],
            "is_seed": True,
        })
        seen_ids.add(nid)

    # Generate synthetic neighbors to form an illustrative subgraph (~30 nodes)
    seed_ids = list(seen_ids)
    neighbor_counter = 0
    for seed_id in seed_ids:
        n_neighbors = rng.randint(4, 7)
        for _ in range(n_neighbors):
            neighbor_counter += 1
            nid = seed_id + neighbor_counter * 1000 + rng.randint(1, 99)
            if nid in seen_ids:
                continue
            seen_ids.add(nid)
            # Neighbors: mostly licit, but some contaminated by proximity
            is_risky = rng.random() < 0.25
            prob = round(rng.uniform(0.55, 0.85) if is_risky else rng.uniform(0.02, 0.35), 4)
            nodes.append({
                "id": nid,
                "true_label": 0,
                "predicted_prob": prob,
                "predicted_label": 1 if prob >= 0.5 else 0,
                "example_type": "neighbor",
                "is_seed": False,
            })
            edges.append({"source": seed_id, "target": nid})

    # Add a few cross-edges between neighbors to show ring structure
    neighbor_ids = [n["id"] for n in nodes if not n["is_seed"]]
    for _ in range(min(8, len(neighbor_ids))):
        a, b = rng.sample(neighbor_ids, 2)
        edges.append({"source": a, "target": b})

    # Add edges between seed nodes (they're connected in the fraud ring)
    for i in range(len(seed_ids)):
        for j in range(i + 1, len(seed_ids)):
            if rng.random() < 0.6:
                edges.append({"source": seed_ids[i], "target": seed_ids[j]})

    # Calculate layout using networkx so the frontend just renders x,y
    import networkx as nx
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"])
    for e in edges:
        G.add_edge(e["source"], e["target"])
    
    pos = nx.spring_layout(G, seed=42)
    for n in nodes:
        n["x"] = pos[n["id"]][0]
        n["y"] = pos[n["id"]][1]

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# HTML pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, tags=["Pages"])
def upi_app():
    """Serve the spoof UPI payment app."""
    return _UPI_HTML


@app.get("/console", response_class=HTMLResponse, tags=["Pages"])
def bank_console():
    """Serve the bank analyst dashboard."""
    html_path = Path(__file__).parent / "11_bank_dashboard.html"
    if html_path.exists() and html_path.stat().st_size > 10:
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=500)


# ---------------------------------------------------------------------------
# Inline UPI Payment App HTML
# ---------------------------------------------------------------------------

_UPI_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FraudShieldAI Pay</title>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Outfit', sans-serif;
    min-height: 100vh;
    display: flex; justify-content: center; align-items: center;
    background: #000;
    overflow: hidden;
    color: #fff;
  }
  
  /* Animated Mesh Gradient Background */
  .bg {
    position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at 50% 50%, #4f46e5 0%, transparent 40%),
                radial-gradient(circle at 80% 20%, #ec4899 0%, transparent 40%),
                radial-gradient(circle at 20% 80%, #06b6d4 0%, transparent 40%);
    background-size: 100% 100%;
    animation: rotate 20s linear infinite;
    z-index: 0;
    opacity: 0.6;
    filter: blur(80px);
  }
  @keyframes rotate { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

  /* Grid overlay */
  .grid-overlay {
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 30px 30px;
    z-index: 1;
  }

  .phone-container {
    position: relative; z-index: 10;
    width: 400px;
    background: rgba(20, 20, 30, 0.6);
    backdrop-filter: blur(30px);
    -webkit-backdrop-filter: blur(30px);
    border-radius: 40px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 30px 60px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.2);
    padding: 32px;
    transform: perspective(1000px) rotateX(2deg) rotateY(0deg);
    transition: transform 0.5s ease, box-shadow 0.5s ease;
  }
  .phone-container:hover {
    transform: perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(-5px);
    box-shadow: 0 40px 80px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.3);
  }
  
  .header { text-align: center; margin-bottom: 30px; }
  .header h1 {
    font-size: 28px; font-weight: 700;
    background: linear-gradient(to right, #fff, #a5b4fc);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -1px;
  }
  .header p { color: #94a3b8; font-size: 13px; margin-top: 5px; font-weight: 300; letter-spacing: 1px; text-transform: uppercase; }

  .input-group { margin-bottom: 20px; position: relative; }
  .input-group label {
    display: block; font-size: 12px; color: #cbd5e1; margin-bottom: 8px; font-weight: 500;
  }
  .input-group select, .input-group input {
    width: 100%; padding: 14px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    color: #fff; font-size: 16px; font-family: 'Outfit', sans-serif;
    outline: none; transition: all 0.3s ease;
    appearance: none;
  }
  .input-group select option { background: #111; color: #fff; }
  .input-group select:focus, .input-group input:focus {
    background: rgba(255, 255, 255, 0.08);
    border-color: #818cf8;
    box-shadow: 0 0 20px rgba(129, 140, 248, 0.3);
  }
  
  .pay-btn {
    width: 100%; padding: 16px; margin-top: 10px;
    background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
    border: none; border-radius: 16px;
    color: #fff; font-size: 18px; font-weight: 600; font-family: 'Outfit', sans-serif;
    cursor: pointer;
    box-shadow: 0 10px 25px rgba(236, 72, 153, 0.4);
    transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative; overflow: hidden;
  }
  .pay-btn::after {
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: linear-gradient(to right, rgba(255,255,255,0) 0%, rgba(255,255,255,0.3) 50%, rgba(255,255,255,0) 100%);
    transform: rotate(30deg) translateY(-50%);
    transition: 0.5s ease; opacity: 0;
  }
  .pay-btn:hover {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 15px 35px rgba(236, 72, 153, 0.6);
  }
  .pay-btn:hover::after { opacity: 1; left: 100%; transition: 0.8s ease; }
  .pay-btn:disabled { opacity: 0.7; transform: none; cursor: not-allowed; }

  /* Results Modal / Overlay */
  .result-container {
    margin-top: 24px; padding: 20px;
    border-radius: 20px;
    display: none;
    animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    position: relative; overflow: hidden;
  }
  @keyframes slideUp { 0% { opacity: 0; transform: translateY(20px); } 100% { opacity: 1; transform: translateY(0); } }

  .result-container.safe {
    background: rgba(16, 185, 129, 0.1);
    border: 1px solid rgba(16, 185, 129, 0.3);
    box-shadow: 0 0 30px rgba(16, 185, 129, 0.2);
  }
  .result-container.fraud {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.4);
    box-shadow: 0 0 40px rgba(239, 68, 68, 0.4);
    animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
  }
  @keyframes shake {
    10%, 90% { transform: translate3d(-1px, 0, 0); }
    20%, 80% { transform: translate3d(2px, 0, 0); }
    30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
    40%, 60% { transform: translate3d(4px, 0, 0); }
  }

  .result-header { display: flex; align-items: center; margin-bottom: 16px; }
  .result-icon { font-size: 28px; margin-right: 12px; }
  .result-title { font-size: 18px; font-weight: 600; }
  .safe .result-title { color: #34d399; }
  .fraud .result-title { color: #f87171; text-shadow: 0 0 10px rgba(239, 68, 68, 0.5); }

  .stat-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }
  .stat-label { color: #94a3b8; }
  .stat-val { font-weight: 500; }
  
  .explanation {
    margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.1);
    font-size: 13px; color: #cbd5e1; line-height: 1.5; font-style: italic;
  }

  /* Custom Spinner */
  .spinner {
    display: inline-block; width: 20px; height: 20px;
    border: 3px solid rgba(255,255,255,0.3); border-radius: 50%;
    border-top-color: #fff; animation: spin 0.8s ease-in-out infinite;
    margin-right: 10px; vertical-align: middle;
  }
</style>
</head>
<body>
<div class="bg"></div>
<div class="grid-overlay"></div>

<div class="phone-container">
  <div class="header">
    <h1>FraudShieldAI Pay</h1>
    <p>Ultra-Secure Payment Simulation</p>
  </div>
  
  <div class="input-group">
    <label>From (Sender Profile & Role)</label>
    <select id="sender">
      <option value="faris">👨‍💼 Faris — Regular Personal Account (faris@fsaipay)</option>
      <option value="rahul">👨‍💻 Rahul — Frequent Peer Transfers (rahul@fsaipay)</option>
      <option value="ahmed">👨 Ahmed — Retail Merchant Account (ahmed@fsaipay)</option>
      <option value="priya">👩‍💼 Priya — Corporate High-Volume (priya@fsaipay)</option>
      <option value="ananya">👩‍💻 Ananya — Freelance / International (ananya@fsaipay)</option>
      <option value="arjun">👨‍🎨 Arjun — New Account (Low History) (arjun@fsaipay)</option>
      <option value="kiran">👩 Kiran — Whitelisted E-Commerce (kiran@fsaipay)</option>
      <option value="neha">👩‍🔬 Neha — High-Velocity Account (neha@fsaipay)</option>
    </select>
  </div>
  
  <div class="input-group">
    <label>To (Receiver Profile & Role)</label>
    <select id="receiver">
      <option value="rahul" selected>👨‍💻 Rahul — Frequent Peer Transfers (rahul@fsaipay)</option>
      <option value="faris">👨‍💼 Faris — Regular Personal Account (faris@fsaipay)</option>
      <option value="ahmed">👨 Ahmed — Retail Merchant Account (ahmed@fsaipay)</option>
      <option value="priya">👩‍💼 Priya — Corporate High-Volume (priya@fsaipay)</option>
      <option value="ananya">👩‍💻 Ananya — Freelance / International (ananya@fsaipay)</option>
      <option value="arjun">👨‍🎨 Arjun — New Account (Low History) (arjun@fsaipay)</option>
      <option value="kiran">👩 Kiran — Whitelisted E-Commerce (kiran@fsaipay)</option>
      <option value="neha">👩‍🔬 Neha — High-Velocity Account (neha@fsaipay)</option>
    </select>
  </div>
  
  <div class="input-group">
    <label>Amount (₹)</label>
    <input type="number" id="amount" value="500" min="1" max="99999">
  </div>
  
  <button class="pay-btn" id="payBtn" onclick="submitPayment()">Transmit Funds</button>
  
  <div class="result-container" id="result"></div>

  <div style="margin-top: 20px; padding: 12px; background: rgba(255,255,255,0.05); border: 1px dashed rgba(255,255,255,0.2); border-radius: 12px; font-size: 11px; color: #94a3b8; line-height: 1.4; text-align: center;">
    📌 <strong>Dataset Simulation Note:</strong> This application is an interactive simulation UI. Payment transfers evaluate precomputed fraud scores sampled from actual transactions in the IEEE-CIS Fraud Detection dataset.
  </div>
</div>

<script>
async function submitPayment(){
  const btn = document.getElementById('payBtn');
  const res = document.getElementById('result');
  const sender = document.getElementById('sender').value;
  const receiver = document.getElementById('receiver').value;
  const amount = parseFloat(document.getElementById('amount').value) || 500;
  
  if(sender === receiver) {
    alert('Sender and receiver must differ'); return;
  }
  
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Authenticating...';
  res.style.display = 'none';
  res.className = 'result-container'; // reset
  
  try {
    const resp = await fetch('/pay', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({sender, receiver, amount})
    });
    const data = await resp.json();
    
    if(!resp.ok) {
      res.classList.add('fraud');
      res.style.display = 'block';
      res.innerHTML = `
        <div class="result-header">
          <div class="result-icon">⚠️</div>
          <div class="result-title">System Error</div>
        </div>
        <div class="explanation">${data.error || 'Request failed'}</div>`;
      return;
    }
    
    if(data.flagged) {
      res.classList.add('fraud');
      res.innerHTML = `
        <div class="result-header">
          <div class="result-icon">🚨</div>
          <div class="result-title">TRANSACTION BLOCKED</div>
        </div>
        <div class="stat-row"><span class="stat-label">AI Risk Score</span><span class="stat-val" style="color:#f87171">${data.fused_score}</span></div>
        <div class="stat-row"><span class="stat-label">TxID</span><span class="stat-val" style="font-family:monospace">${data.transaction_id}</span></div>
        <div class="explanation"><strong>Fraud Indicators:</strong><br>${(data.explanation || []).join('<br>')}</div>
      `;
    } else {
      res.classList.add('safe');
      res.innerHTML = `
        <div class="result-header">
          <div class="result-icon">✅</div>
          <div class="result-title">FUNDS SECURED & SENT</div>
        </div>
        <div class="stat-row"><span class="stat-label">Amount</span><span class="stat-val">₹${data.amount}</span></div>
        <div class="stat-row"><span class="stat-label">AI Risk Score</span><span class="stat-val" style="color:#34d399">${data.fused_score}</span></div>
        <div class="stat-row"><span class="stat-label">TxID</span><span class="stat-val" style="font-family:monospace">${data.transaction_id}</span></div>
        <div class="explanation">Transaction cleared by FraudShieldAI.</div>
      `;
    }
    res.style.display = 'block';
  } catch(e) {
    res.classList.add('fraud');
    res.style.display = 'block';
    res.innerHTML = '<div class="result-title">Network Error</div><div class="explanation">' + e.message + '</div>';
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Transmit Funds';
  }
}
</script>
</body>
</html>"""
=======
        "autoencoder_score": float(row["autoencoder_score"]),
        "transformer_score": float(row["transformer_score"]),
        "fused_score": float(row["fused_score"]),
    }


@torch.no_grad()
def get_gnn_predictions() -> pd.DataFrame:
    require_gnn()
    if state.gnn_predictions is not None:
        return state.gnn_predictions

    import torch.nn.functional as F

    graph = state.gnn_graph
    logits = state.gnn_model(graph["x"], graph["edge_index"])
    probs = F.softmax(logits, dim=1)[:, 1].cpu().numpy()
    preds = logits.argmax(dim=1).cpu().numpy()
    labels = graph["y"].cpu().numpy()
    timesteps = graph["timestep"].cpu().numpy()
    node_ids = np.arange(len(labels))
    df = pd.DataFrame({
        "node_id": node_ids,
        "true_label": labels,
        "predicted_prob": probs,
        "predicted_label": preds,
        "timestep": timesteps,
    })
    df["status"] = np.select(
        [
            df["true_label"].eq(1),
            df["predicted_label"].eq(1),
            df["true_label"].eq(0),
        ],
        [
            "known_illicit",
            "suspicious_prediction",
            "known_licit",
        ],
        default="unlabeled",
    )
    state.gnn_predictions = df
    return df


def gnn_node_record(node_id: int, predictions: pd.DataFrame) -> dict[str, Any]:
    row = predictions.iloc[int(node_id)]
    return {
        "node_id": int(row["node_id"]),
        "true_label": int(row["true_label"]),
        "predicted_prob": round(float(row["predicted_prob"]), 6),
        "predicted_label": int(row["predicted_label"]),
        "timestep": int(row["timestep"]),
        "status": str(row["status"]),
    }


def extract_subgraph(node_id: int, hops: int = 1, max_nodes: int = 120) -> dict[str, Any]:
    require_gnn()
    predictions = get_gnn_predictions()
    graph = state.gnn_graph
    n_nodes = int(graph["x"].shape[0])
    if node_id < 0 or node_id >= n_nodes:
        raise HTTPException(status_code=404, detail="GNN node_id is outside the Elliptic graph")

    clean_hops = max(1, min(int(hops), 2))
    edge_index = graph["edge_index"].cpu().numpy()
    src, dst = edge_index
    selected = {int(node_id)}
    frontier = {int(node_id)}
    for _ in range(clean_hops):
        mask = np.isin(src, list(frontier)) | np.isin(dst, list(frontier))
        neighbors = set(src[mask].astype(int).tolist()) | set(dst[mask].astype(int).tolist())
        selected |= neighbors
        frontier = neighbors
        if len(selected) >= max_nodes:
            break

    ranked = sorted(
        selected,
        key=lambda n: (n != node_id, -float(predictions.iloc[n]["predicted_prob"])),
    )[:max_nodes]
    selected_set = set(ranked)
    edge_mask = np.isin(src, ranked) & np.isin(dst, ranked)
    edges = [
        {"source": int(s), "target": int(t)}
        for s, t in zip(src[edge_mask], dst[edge_mask])
        if int(s) in selected_set and int(t) in selected_set
    ]

    return {
        "center_node": gnn_node_record(node_id, predictions),
        "hops": clean_hops,
        "nodes": [gnn_node_record(n, predictions) for n in ranked],
        "edges": edges,
    }


@torch.no_grad()
def run_inference(features: np.ndarray, sequence: np.ndarray, sequence_mask: np.ndarray) -> dict[str, Any]:
    require_model(state.ae_model, "Autoencoder")
    require_model(state.tf_model, "Transformer")

    x = torch.tensor(features.reshape(1, -1), dtype=torch.float32, device=DEVICE)
    recon = state.ae_model(x)
    raw_error = float(torch.mean((x - recon) ** 2, dim=1).item())
    ae_score = percentile_of_raw_error(raw_error)

    seq = torch.tensor(sequence.reshape(1, SEQ_LEN, -1), dtype=torch.float32, device=DEVICE)
    mask_tensor = torch.tensor(sequence_mask.reshape(1, SEQ_LEN), dtype=torch.float32, device=DEVICE)
    logit = state.tf_model(seq, mask_tensor)
    tf_score = float(torch.sigmoid(logit).item())

    fused = fused_score(ae_score, tf_score)
    return {
        "autoencoder_score": ae_score,
        "transformer_score": tf_score,
        "fused_score": fused,
        "flagged": bool(fused >= FUSION_THRESHOLD),
        "explanation": explanation_for_scores(ae_score, tf_score),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "FraudShieldAI API", "status": "ok"}


@app.get("/dashboard", include_in_schema=False)
def dashboard() -> FileResponse:
    dashboard_path = Path("11_bank_dashboard.html")
    if not dashboard_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard file is not available")
    return FileResponse(dashboard_path)


@app.get("/health")
def health() -> dict[str, Any]:
    transaction_count = 0 if state.fusion_results is None else int(len(state.fusion_results))
    return {
        "status": "ok" if state.ae_model is not None and state.tf_model is not None and transaction_count > 0 else "degraded",
        "autoencoder_loaded": state.ae_model is not None,
        "transformer_loaded": state.tf_model is not None,
        "gnn_loaded": state.gnn_model is not None,
        "transactions_available": transaction_count,
        "input_dim": state.input_dim,
        "fusion": {
            "w_transformer": W_TRANSFORMER,
            "w_autoencoder": W_AUTOENCODER,
            "threshold": FUSION_THRESHOLD,
        },
        "load_errors": state.load_errors,
    }


@app.get("/transactions/sample")
def sample_transactions(limit: int = 10) -> dict[str, Any]:
    if state.fusion_results is None:
        raise HTTPException(status_code=503, detail="fusion_results.csv is not loaded")
    clean_limit = max(1, min(int(limit), 50))
    cols = ["TransactionID", "true_label"]
    rows = state.fusion_results[cols].head(clean_limit).rename(columns={"TransactionID": "transaction_id"})
    return {"transactions": rows.to_dict(orient="records")}


@app.get("/predict_by_id/{transaction_id}")
def predict_by_id(transaction_id: int) -> dict[str, Any]:
    require_data()
    if transaction_id not in state.id_to_row:
        raise HTTPException(status_code=404, detail="TransactionID is not available in the held-out fusion test set")

    started = time.perf_counter()
    try:
        row = state.id_to_row[transaction_id]
        idx = state.window_indices[row]
        safe_idx = np.where(idx == -1, 0, idx)
        result = run_inference(
            np.asarray(state.features[row], dtype=np.float32),
            np.asarray(state.features[safe_idx], dtype=np.float32),
            np.asarray(state.mask[row], dtype=np.float32),
        )
        saved_scores = saved_fusion_scores(transaction_id)
        if saved_scores is not None:
            result = {
                **saved_scores,
                "flagged": bool(saved_scores["fused_score"] >= FUSION_THRESHOLD),
                "explanation": explanation_for_scores(
                    saved_scores["autoencoder_score"],
                    saved_scores["transformer_score"],
                ),
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    latency_ms = (time.perf_counter() - started) * 1000
    return {
        "transaction_id": transaction_id,
        "true_label": int(state.labels[row]),
        "autoencoder_score": round(result["autoencoder_score"], 4),
        "transformer_score": round(result["transformer_score"], 4),
        "fused_score": round(result["fused_score"], 4),
        "flagged": result["flagged"],
        "explanation": result["explanation"],
        "inference_latency_ms": round(latency_ms, 2),
    }


@app.get("/gnn/suspicious")
def gnn_suspicious(limit: int = 20) -> dict[str, Any]:
    try:
        predictions = get_gnn_predictions()
        clean_limit = max(1, min(int(limit), 100))
        suspicious = predictions[
            (predictions["predicted_label"] == 1) | (predictions["true_label"] == 1)
        ].sort_values("predicted_prob", ascending=False).head(clean_limit)
        return {
            "dataset": "Elliptic Bitcoin transaction graph",
            "note": "GNN scores are network intelligence and are not numerically included in the IEEE-CIS hybrid fusion.",
            "nodes": [
                {
                    "node_id": int(row.node_id),
                    "true_label": int(row.true_label),
                    "predicted_prob": round(float(row.predicted_prob), 6),
                    "predicted_label": int(row.predicted_label),
                    "timestep": int(row.timestep),
                    "status": str(row.status),
                }
                for row in suspicious.itertuples(index=False)
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"GNN suspicious-node scoring failed: {exc}") from exc


@app.get("/gnn/subgraph/{node_id}")
def gnn_subgraph(node_id: int, hops: int = 1, max_nodes: int = 120) -> dict[str, Any]:
    try:
        return {
            "dataset": "Elliptic Bitcoin transaction graph",
            "note": "Edges are extracted from the existing Elliptic graph artifact; no graph relationships are fabricated.",
            **extract_subgraph(node_id=node_id, hops=hops, max_nodes=max_nodes),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"GNN subgraph extraction failed: {exc}") from exc


@app.post("/predict")
def predict(req: TransactionRequest) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        result = run_inference(
            np.asarray(req.features, dtype=np.float32),
            np.asarray(req.sequence, dtype=np.float32),
            np.asarray(req.sequence_mask, dtype=np.float32),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc

    latency_ms = (time.perf_counter() - started) * 1000
    return {
        "autoencoder_score": round(result["autoencoder_score"], 4),
        "transformer_score": round(result["transformer_score"], 4),
        "fused_score": round(result["fused_score"], 4),
        "flagged": result["flagged"],
        "explanation": result["explanation"],
        "inference_latency_ms": round(latency_ms, 2),
    }


load_runtime()
>>>>>>> 3447f33951478a736038feda72194f1fd45fa9e0
