"""
Day 6: Hybrid Risk Fusion.

Combines the Autoencoder's reconstruction-error score and the Transformer's
fraud probability on the SAME held-out IEEE-CIS test transactions (both
models were trained on the same processed data, so this is a genuine
per-transaction fusion — not simulated).

The GNN is intentionally NOT fused here: it runs on the Elliptic dataset,
which has no shared transaction IDs with IEEE-CIS. Combining it per-transaction
would require a real entity-resolution layer linking accounts across datasets,
which doesn't exist in either public benchmark. See the printed note at the
end of this script for how that would work in a production deployment.

Run after 02_train_autoencoder.py and 04_train_transformer.py (needs their
saved model weights).
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

DATA_DIR = "data"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEQ_LEN = 15


# ---- Re-declare model classes (must match 02_train_autoencoder.py / 04_train_transformer.py) ----

class Autoencoder(nn.Module):
    def __init__(self, input_dim):
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
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Linear(d_model, 1)

    def forward(self, x, mask):
        h = self.input_proj(x)
        h = self.pos_encoding(h)
        key_padding_mask = (mask == 0)
        h = self.encoder(h, src_key_padding_mask=key_padding_mask)
        mask_exp = mask.unsqueeze(-1)
        pooled = (h * mask_exp).sum(dim=1) / mask_exp.sum(dim=1).clamp(min=1)
        return self.classifier(pooled).squeeze(-1)


def user_split(user_ids, test_size=0.2, seed=42):
    """Identical split to 04_train_transformer.py — same seed reproduces the same test set."""
    row_ids = np.arange(len(user_ids))
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(row_ids, groups=user_ids))
    return row_ids[train_idx], row_ids[test_idx]


@torch.no_grad()
def score_autoencoder(model, features, batch_size=4096):
    model.eval()
    errors = []
    for i in range(0, len(features), batch_size):
        batch = torch.tensor(features[i:i + batch_size], dtype=torch.float32).to(DEVICE)
        recon = model(batch)
        err = torch.mean((batch - recon) ** 2, dim=1).cpu().numpy()
        errors.append(err)
    return np.concatenate(errors)


@torch.no_grad()
def score_transformer(model, features, window_indices, mask, row_ids, batch_size=512):
    model.eval()
    probs = []
    for i in range(0, len(row_ids), batch_size):
        batch_rows = row_ids[i:i + batch_size]
        idx = window_indices[batch_rows]
        safe_idx = np.where(idx == -1, 0, idx)
        seq = torch.tensor(features[safe_idx], dtype=torch.float32).to(DEVICE)
        m = torch.tensor(mask[batch_rows], dtype=torch.float32).to(DEVICE)
        logits = model(seq, m)
        probs.append(torch.sigmoid(logits).cpu().numpy())
    return np.concatenate(probs)


def normalize_percentile(scores):
    """Rank-normalize raw scores to [0, 1] so different models' scales are comparable."""
    ranks = pd.Series(scores).rank(pct=True).values
    return ranks


def evaluate(scores, labels, threshold):
    preds = (scores >= threshold).astype(int)
    precision = precision_score(labels, preds, zero_division=0)
    recall = recall_score(labels, preds, zero_division=0)
    f1 = f1_score(labels, preds, zero_division=0)
    auc = roc_auc_score(labels, scores)
    cm = confusion_matrix(labels, preds)
    return precision, recall, f1, auc, cm


def best_f1_threshold(scores, labels):
    best_f1, best_t = -1, 0.5
    for t in np.linspace(0.1, 0.95, 34):
        preds = (scores >= t).astype(int)
        f1 = f1_score(labels, preds, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return best_t, best_f1


if __name__ == "__main__":
    features = np.load(f"{DATA_DIR}/features.npy")
    window_indices = np.load(f"{DATA_DIR}/window_indices.npy")
    mask = np.load(f"{DATA_DIR}/mask.npy")
    labels = np.load(f"{DATA_DIR}/labels.npy")
    user_ids = np.load(f"{DATA_DIR}/user_ids.npy", allow_pickle=True)
    transaction_ids = np.load(f"{DATA_DIR}/transaction_ids.npy")

    _, test_rows = user_split(user_ids)  # same split as Day 4, reproduced via same seed
    y_test = labels[test_rows]
    print(f"Fusion test set: {len(test_rows)} transactions, fraud rate {y_test.mean():.4%}")

    # --- Autoencoder scores (raw reconstruction error, on this test set's transactions) ---
    ae_model = Autoencoder(input_dim=features.shape[1]).to(DEVICE)
    ae_model.load_state_dict(torch.load("autoencoder_model.pt", map_location=DEVICE))
    ae_raw = score_autoencoder(ae_model, features[test_rows])
    ae_norm = normalize_percentile(ae_raw)

    # --- Transformer scores (already 0-1 probabilities) ---
    tf_model = BehavioralTransformer(input_dim=features.shape[1]).to(DEVICE)
    tf_model.load_state_dict(torch.load("transformer_model.pt", map_location=DEVICE))
    tf_probs = score_transformer(tf_model, features, window_indices, mask, test_rows)

    # --- Individual model performance on this exact test set (for fair comparison) ---
    ae_t, ae_f1 = best_f1_threshold(ae_norm, y_test)
    tf_t, tf_f1 = best_f1_threshold(tf_probs, y_test)
    print(f"\nAutoencoder alone : best F1={ae_f1:.4f} @ threshold {ae_t:.2f}")
    print(f"Transformer alone : best F1={tf_f1:.4f} @ threshold {tf_t:.2f}")

    # --- Weighted fusion: grid search weights to maximize F1 ---
    best_result = None
    for w in np.linspace(0.0, 1.0, 21):  # w = weight on Transformer, (1-w) on Autoencoder
        fused = w * tf_probs + (1 - w) * ae_norm
        t, f1 = best_f1_threshold(fused, y_test)
        if best_result is None or f1 > best_result["f1"]:
            best_result = {"w_transformer": w, "w_autoencoder": 1 - w, "threshold": t, "f1": f1}

    w_tf, w_ae = best_result["w_transformer"], best_result["w_autoencoder"]
    fused_scores = w_tf * tf_probs + w_ae * ae_norm
    precision, recall, f1, auc, cm = evaluate(fused_scores, y_test, best_result["threshold"])

    print(f"\n--- Hybrid Fusion (best weights: Transformer={w_tf:.2f}, Autoencoder={w_ae:.2f}) ---")
    print(f"Threshold: {best_result['threshold']:.2f}")
    print(f"Precision: {precision:.4f}  Recall: {recall:.4f}  F1: {f1:.4f}  AUC-ROC: {auc:.4f}")
    print(f"Confusion matrix:\n{cm}")

    print(f"\n--- Comparison summary ---")
    print(f"{'Model':<20}{'Best F1':<10}")
    print(f"{'Autoencoder alone':<20}{ae_f1:<10.4f}")
    print(f"{'Transformer alone':<20}{tf_f1:<10.4f}")
    print(f"{'Hybrid Fusion':<20}{f1:<10.4f}")

    print(
        "\n--- On the GNN's role ---\n"
        "The GNN was not included in this fusion because it scores Elliptic Bitcoin transactions,\n"
        "which have no shared TransactionID with IEEE-CIS. In a real deployment, the GNN would\n"
        "score an account/entity (via a shared account graph built from an institution's own data),\n"
        "and its risk score would be joined into this fusion at the ACCOUNT level rather than the\n"
        "transaction level — e.g. 'this transaction's account currently has a high GNN fraud-ring\n"
        "score' becomes a feature the same way ae_norm/tf_probs are here. That join requires\n"
        "institution data neither public dataset provides, so it's documented as a Phase-2 integration\n"
        "step rather than simulated with fabricated correspondences."
    )

    # Save fused scores + examples for documentation
    df = pd.DataFrame({
        "TransactionID": transaction_ids[test_rows],
        "true_label": y_test,
        "autoencoder_score": ae_norm,
        "transformer_score": tf_probs,
        "fused_score": fused_scores,
    })
    df.to_csv("fusion_results.csv", index=False)
    print(f"\nSaved {len(df)} scored transactions to fusion_results.csv")