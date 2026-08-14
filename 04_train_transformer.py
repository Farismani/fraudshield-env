"""
Day 4: Behavioral Transformer — trains on per-user transaction sequences to
detect deviations from normal behavioral patterns (unusual timing, amounts,
sudden shifts).

Run after 03_build_sequences.py.
"""

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (precision_score, recall_score, f1_score,
                              roc_auc_score, average_precision_score, confusion_matrix)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA_DIR = "data"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SEQ_LEN = 15


class SequenceDataset(Dataset):
    """Gathers each (seq_len x num_features) window on the fly — nothing
    large is materialized upfront."""

    def __init__(self, features, window_indices, mask, labels, row_ids):
        self.features = features
        self.window_indices = window_indices
        self.mask = mask
        self.labels = labels
        self.row_ids = row_ids  # which global rows this split covers

    def __len__(self):
        return len(self.row_ids)

    def __getitem__(self, i):
        row = self.row_ids[i]
        idx = self.window_indices[row]
        m = self.mask[row]
        # padded positions use index 0 as a dummy (masked out anyway by attention mask)
        safe_idx = np.where(idx == -1, 0, idx)
        seq = self.features[safe_idx]  # (seq_len, num_features)
        return (torch.tensor(seq, dtype=torch.float32),
                torch.tensor(m, dtype=torch.float32),
                torch.tensor(self.labels[row], dtype=torch.float32))


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
        # x: (batch, seq_len, input_dim), mask: (batch, seq_len) 1=real, 0=pad
        h = self.input_proj(x)
        h = self.pos_encoding(h)
        key_padding_mask = (mask == 0)  # True where padded — TransformerEncoder expects this
        h = self.encoder(h, src_key_padding_mask=key_padding_mask)
        # masked mean-pool over the sequence
        mask_exp = mask.unsqueeze(-1)
        pooled = (h * mask_exp).sum(dim=1) / mask_exp.sum(dim=1).clamp(min=1)
        return self.classifier(pooled).squeeze(-1)


def load_data():
    features = np.load(f"{DATA_DIR}/features.npy")
    window_indices = np.load(f"{DATA_DIR}/window_indices.npy")
    mask = np.load(f"{DATA_DIR}/mask.npy")
    labels = np.load(f"{DATA_DIR}/labels.npy")
    transaction_ids = np.load(f"{DATA_DIR}/transaction_ids.npy")
    user_ids = np.load(f"{DATA_DIR}/user_ids.npy", allow_pickle=True)
    return features, window_indices, mask, labels, transaction_ids, user_ids


def user_split(user_ids, test_size=0.2, seed=42):
    row_ids = np.arange(len(user_ids))
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
    train_idx, test_idx = next(splitter.split(row_ids, groups=user_ids))
    return row_ids[train_idx], row_ids[test_idx]


def train(model, train_loader, epochs=25, lr=1e-4, pos_weight=None):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    losses = []

    for epoch in range(epochs):
        model.train()
        epoch_loss, n_seen = 0.0, 0
        for seq, mask, y in train_loader:
            seq, mask, y = seq.to(DEVICE), mask.to(DEVICE), y.to(DEVICE)
            optimizer.zero_grad()
            logits = model(seq, mask)
            loss = loss_fn(logits, y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(y)
            n_seen += len(y)
        epoch_loss /= n_seen
        losses.append(epoch_loss)
        print(f"Epoch {epoch+1}/{epochs}  loss={epoch_loss:.5f}")

    return losses


@torch.no_grad()
def predict(model, loader):
    model.eval()
    all_probs, all_labels = [], []
    for seq, mask, y in loader:
        seq, mask = seq.to(DEVICE), mask.to(DEVICE)
        logits = model(seq, mask)
        probs = torch.sigmoid(logits).cpu().numpy()
        all_probs.append(probs)
        all_labels.append(y.numpy())
    return np.concatenate(all_probs), np.concatenate(all_labels)


def evaluate(probs, labels, threshold=0.5):
    preds = (probs >= threshold).astype(int)
    precision = precision_score(labels, preds, zero_division=0)
    recall = recall_score(labels, preds, zero_division=0)
    f1 = f1_score(labels, preds, zero_division=0)
    auc = roc_auc_score(labels, probs)
    pr_auc = average_precision_score(labels, probs)
    cm = confusion_matrix(labels, preds)
    return precision, recall, f1, auc, pr_auc, cm


def save_examples(probs, labels, test_row_ids, transaction_ids):
    """Log a true positive and a false positive example, addressing the gap
    flagged in the Day 1-2 report."""
    tx_ids = transaction_ids[test_row_ids]
    df = pd.DataFrame({"TransactionID": tx_ids, "true_label": labels, "predicted_prob": probs})
    df["predicted_label"] = (df["predicted_prob"] >= 0.5).astype(int)

    true_pos = df[(df.true_label == 1) & (df.predicted_label == 1)].sort_values("predicted_prob", ascending=False)
    false_pos = df[(df.true_label == 0) & (df.predicted_label == 1)].sort_values("predicted_prob", ascending=False)

    examples = pd.concat([
        true_pos.head(2).assign(example_type="true_positive"),
        false_pos.head(2).assign(example_type="false_positive"),
    ])
    examples.to_csv("transformer_examples.csv", index=False)
    print(f"\nSaved {len(examples)} example predictions to transformer_examples.csv")
    print(examples.to_string(index=False))


def plot_loss(losses):
    plt.figure(figsize=(7, 4))
    plt.plot(range(1, len(losses) + 1), losses, marker="o", color="#0f3460")
    plt.xlabel("Epoch")
    plt.ylabel("Training BCE loss")
    plt.title("Behavioral Transformer — Training Loss")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("transformer_loss.png", dpi=150)
    print("Saved transformer_loss.png")


if __name__ == "__main__":
    features, window_indices, mask, labels, transaction_ids, user_ids = load_data()
    print(f"Loaded {len(labels)} sequences, {features.shape[1]} features, "
          f"fraud rate {labels.mean():.4%}")

    train_rows, test_rows = user_split(user_ids)
    print(f"Train: {len(train_rows)} sequences, Test: {len(test_rows)} sequences (split by user)")

    train_ds = SequenceDataset(features, window_indices, mask, labels, train_rows)
    test_ds = SequenceDataset(features, window_indices, mask, labels, test_rows)
    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=512, shuffle=False, num_workers=0)

    fraud_rate = labels[train_rows].mean()
    pos_weight = torch.tensor([(1 - fraud_rate) / fraud_rate], dtype=torch.float32).to(DEVICE)
    print(f"Using pos_weight={pos_weight.item():.2f} to counter class imbalance")

    model = BehavioralTransformer(input_dim=features.shape[1]).to(DEVICE)
    losses = train(model, train_loader, epochs=25, lr=1e-4, pos_weight=pos_weight)
    plot_loss(losses)

    probs, y_true = predict(model, test_loader)

    print("\n--- Evaluation @ threshold 0.5 ---")
    precision, recall, f1, auc, pr_auc, cm = evaluate(probs, y_true, threshold=0.5)
    print(f"Precision: {precision:.4f}  Recall: {recall:.4f}  F1: {f1:.4f}")
    print(f"AUC-ROC: {auc:.4f}  PR-AUC: {pr_auc:.4f}")
    print(f"Confusion matrix:\n{cm}")

    save_examples(probs, y_true, test_rows, transaction_ids)

    torch.save(model.state_dict(), "transformer_model.pt")
    print("Saved model weights to transformer_model.pt")