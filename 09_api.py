"""
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
