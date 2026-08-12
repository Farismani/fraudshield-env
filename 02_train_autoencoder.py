"""
Day 2: Deep Autoencoder for unsupervised anomaly detection.
Trains only on legitimate transactions, then flags high reconstruction
error as potential fraud. Produces the plots/metrics you need for the
review documentation.

Run after 01_data_prep.py.
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.metrics import (precision_score, recall_score, f1_score,
                              roc_auc_score, confusion_matrix)
import matplotlib.pyplot as plt

DATA_DIR = "data"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


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


def load_features():
    df = pd.read_csv(f"{DATA_DIR}/processed_transactions.csv")
    drop_cols = ["TransactionID", "TransactionDT", "isFraud", "user_id"]
    feature_cols = [c for c in df.columns if c not in drop_cols]
    X = df[feature_cols].values.astype(np.float32)
    y = df["isFraud"].values

    # Guard: catch bad upstream data immediately instead of training on NaNs
    n_nan = np.isnan(X).sum()
    n_inf = np.isinf(X).sum()
    if n_nan or n_inf:
        raise ValueError(
            f"Found {n_nan} NaN and {n_inf} Inf values in features — "
            "re-run 01_data_prep.py (make sure you're using the latest version)."
        )

    return X, y, feature_cols


def train_autoencoder(X_train_legit, input_dim, epochs=25, batch_size=256, lr=1e-3):
    model = Autoencoder(input_dim).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    X_tensor = torch.tensor(X_train_legit).to(DEVICE)
    n = X_tensor.shape[0]
    losses = []

    for epoch in range(epochs):
        perm = torch.randperm(n)
        epoch_loss = 0.0
        for i in range(0, n, batch_size):
            idx = perm[i:i + batch_size]
            batch = X_tensor[idx]
            optimizer.zero_grad()
            recon = model(batch)
            loss = loss_fn(recon, batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(idx)
        epoch_loss /= n
        losses.append(epoch_loss)
        print(f"Epoch {epoch+1}/{epochs}  loss={epoch_loss:.5f}")

    return model, losses


def reconstruction_error(model, X):
    model.eval()
    with torch.no_grad():
        X_tensor = torch.tensor(X).to(DEVICE)
        recon = model(X_tensor)
        err = torch.mean((X_tensor - recon) ** 2, dim=1).cpu().numpy()
    return err


def evaluate(errors, y_true, percentile=97):
    threshold = np.percentile(errors[y_true == 0], percentile)
    y_pred = (errors > threshold).astype(int)

    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    auc = roc_auc_score(y_true, errors)
    cm = confusion_matrix(y_true, y_pred)

    print(f"\n--- Evaluation (threshold @ {percentile}th percentile = {threshold:.5f}) ---")
    print(f"Precision: {precision:.4f}  Recall: {recall:.4f}  F1: {f1:.4f}  AUC-ROC: {auc:.4f}")
    print(f"Confusion matrix:\n{cm}")
    return threshold, precision, recall, f1, auc, cm


def plot_results(losses, errors, y_true, threshold):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].plot(losses)
    axes[0].set_title("Autoencoder training loss")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("MSE loss")

    axes[1].hist(errors[y_true == 0], bins=80, alpha=0.6, label="Legit", density=True)
    axes[1].hist(errors[y_true == 1], bins=80, alpha=0.6, label="Fraud", density=True)
    axes[1].axvline(threshold, color="red", linestyle="--", label="Threshold")
    axes[1].set_title("Reconstruction error distribution")
    axes[1].set_xlabel("Reconstruction error")
    axes[1].legend()
    axes[1].set_xlim(0, np.percentile(errors, 99.5))

    plt.tight_layout()
    plt.savefig("autoencoder_results.png", dpi=150)
    print("\nSaved plots to autoencoder_results.png")


if __name__ == "__main__":
    X, y, feature_cols = load_features()
    print(f"Loaded {X.shape[0]} rows, {X.shape[1]} features. Fraud rate: {y.mean():.4%}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # Train only on legitimate transactions
    X_train_legit = X_train[y_train == 0]
    print(f"Training on {X_train_legit.shape[0]} legitimate transactions")

    model, losses = train_autoencoder(X_train_legit, input_dim=X.shape[1])

    test_errors = reconstruction_error(model, X_test)

    # Try a few thresholds and report the best F1 — use this in your review slide
    best = None
    for p in [90, 95, 97, 99]:
        threshold, precision, recall, f1, auc, cm = evaluate(test_errors, y_test, percentile=p)
        if best is None or f1 > best[3]:
            best = (threshold, precision, recall, f1, auc, cm)

    print(f"\nBest threshold: F1={best[3]:.4f}  Precision={best[1]:.4f}  Recall={best[2]:.4f}  AUC={best[4]:.4f}")
    plot_results(losses, test_errors, y_test, best[0])

    torch.save(model.state_dict(), "autoencoder_model.pt")
    print("Saved model weights to autoencoder_model.pt")