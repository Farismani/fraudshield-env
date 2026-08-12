"""
Day 7a: FastAPI backend — single /predict endpoint that runs a transaction
through the Autoencoder and Transformer, applies the Fusion weights found in
07_hybrid_fusion.py, and returns a score + explanation.

Run: uvicorn 09_api:app --reload
Then open http://127.0.0.1:8000/docs for interactive API docs.

Note: this serves the Autoencoder + Transformer fusion (the two models that
share IEEE-CIS transactions). The GNN's account-level score would join in
here as an additional input in a real deployment — see 07_hybrid_fusion.py's
closing note for why it isn't fabricated into this same request path.
"""

import numpy as np
import torch
import torch.nn as nn
from fastapi import FastAPI
from pydantic import BaseModel, Field

DEVICE = torch.device("cpu")
SEQ_LEN = 15

# --- Fusion weights: paste the values 07_hybrid_fusion.py printed as "best weights" ---
W_TRANSFORMER = 0.55  # placeholder — replace with your actual best_result["w_transformer"]
W_AUTOENCODER = 0.45  # placeholder — replace with your actual best_result["w_autoencoder"]
FUSION_THRESHOLD = 0.5  # placeholder — replace with your actual best_result["threshold"]


class Autoencoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.encoder = nn.Sequential(nn.Linear(input_dim, 64), nn.ReLU(), nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU())
        self.decoder = nn.Sequential(nn.Linear(16, 32), nn.ReLU(), nn.Linear(32, 64), nn.ReLU(), nn.Linear(64, input_dim))

    def forward(self, x):
        return self.decoder(self.encoder(x))


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=SEQ_LEN):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, :x.size(1)]


class BehavioralTransformer(nn.Module):
    def __init__(self, input_dim, d_model=64, nhead=4, num_layers=2, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoding = PositionalEncoding(d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4, dropout=dropout, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Linear(d_model, 1)

    def forward(self, x, mask):
        h = self.input_proj(x)
        h = self.pos_encoding(h)
        h = self.encoder(h, src_key_padding_mask=(mask == 0))
        mask_exp = mask.unsqueeze(-1)
        pooled = (h * mask_exp).sum(dim=1) / mask_exp.sum(dim=1).clamp(min=1)
        return self.classifier(pooled).squeeze(-1)


app = FastAPI(title="FraudShieldAI API")

INPUT_DIM = 424  # must match your Day 1 processed feature count

_ae_model = Autoencoder(INPUT_DIM)
_ae_model.load_state_dict(torch.load("autoencoder_model.pt", map_location=DEVICE))
_ae_model.eval()

_tf_model = BehavioralTransformer(INPUT_DIM)
_tf_model.load_state_dict(torch.load("transformer_model.pt", map_location=DEVICE))
_tf_model.eval()

# In-memory reconstruction-error reference distribution for percentile normalization.
# Loaded once at startup from the fusion script's saved output, if available.
try:
    import pandas as pd
    _ref = pd.read_csv("fusion_results.csv")
    _AE_REFERENCE = np.sort(_ref["autoencoder_score"].values)  # already percentile-ranked 0-1
except FileNotFoundError:
    _AE_REFERENCE = None


class TransactionRequest(BaseModel):
    features: list[float] = Field(..., description="424 preprocessed feature values, same order as Day 1 output")
    sequence: list[list[float]] = Field(..., description="Up to 15 prior transactions (this one last), each 424 features")
    sequence_mask: list[float] = Field(..., description="1 for real, 0 for padding, length 15, aligned with `sequence`")


def percentile_of_new_error(raw_error: float) -> float:
    if _AE_REFERENCE is None:
        return 0.5  # fallback if no reference distribution is available yet
    return float(np.searchsorted(_AE_REFERENCE, raw_error) / len(_AE_REFERENCE))


@app.post("/predict")
def predict(req: TransactionRequest):
    x = torch.tensor([req.features], dtype=torch.float32)
    with torch.no_grad():
        recon = _ae_model(x)
        raw_error = torch.mean((x - recon) ** 2, dim=1).item()
    ae_score = percentile_of_new_error(raw_error)

    seq = torch.tensor([req.sequence], dtype=torch.float32)
    mask = torch.tensor([req.sequence_mask], dtype=torch.float32)
    with torch.no_grad():
        logit = _tf_model(seq, mask)
        tf_score = torch.sigmoid(logit).item()

    fused = W_TRANSFORMER * tf_score + W_AUTOENCODER * ae_score
    flagged = fused >= FUSION_THRESHOLD

    contributors = []
    if ae_score > 0.7:
        contributors.append("high reconstruction error (statistically unusual transaction)")
    if tf_score > 0.7:
        contributors.append("deviates from this user's normal behavioral pattern")
    if not contributors:
        contributors.append("no single layer strongly triggered — flagged on combined score")

    return {
        "fused_score": round(fused, 4),
        "flagged": flagged,
        "autoencoder_score": round(ae_score, 4),
        "transformer_score": round(tf_score, 4),
        "explanation": contributors,
    }


@app.get("/health")
def health():
    return {"status": "ok"}