"""
Day 5b: Graph Attention Network (GAT) — detects fraud rings and mule accounts
by learning from transaction graph structure, not just individual features.

Run after 05_prepare_elliptic.py.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv
from sklearn.metrics import (precision_score, recall_score, f1_score,
                              roc_auc_score, confusion_matrix)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DATA_DIR = "data"
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Elliptic's standard time-based split: first 34 timesteps = train, remaining = test.
# This is more realistic than a random split — the model is evaluated on transactions
# that happened AFTER everything it trained on, just like in production.
TRAIN_MAX_TIMESTEP = 34


class GAT(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, heads=4, dropout=0.3, num_classes=2):
        super().__init__()
        self.gat1 = GATConv(input_dim, hidden_dim, heads=heads, dropout=dropout)
        self.gat2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, concat=False, dropout=dropout)
        self.classifier = nn.Linear(hidden_dim, num_classes)
        self.dropout = dropout

    def forward(self, x, edge_index):
        h = F.elu(self.gat1(x, edge_index))
        h = F.dropout(h, p=self.dropout, training=self.training)
        h = F.elu(self.gat2(h, edge_index))
        return self.classifier(h)


def load_graph():
    graph = torch.load(f"{DATA_DIR}/elliptic_graph.pt", weights_only=False)
    return graph["x"], graph["edge_index"], graph["y"], graph["timestep"]


def build_masks(y, timestep):
    labeled = y != -1
    train_mask = labeled & (timestep <= TRAIN_MAX_TIMESTEP)
    test_mask = labeled & (timestep > TRAIN_MAX_TIMESTEP)
    return train_mask, test_mask


def train(model, x, edge_index, y, train_mask, epochs=100, lr=5e-4):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)

    # Class weights to counter illicit-vs-licit imbalance within the labeled set
    n_pos = (y[train_mask] == 1).sum().item()
    n_neg = (y[train_mask] == 0).sum().item()
    class_weights = torch.tensor([1.0, n_neg / max(n_pos, 1)], dtype=torch.float32).to(DEVICE)
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)

    losses = []
    for epoch in range(epochs):
        model.train()
        optimizer.zero_grad()
        out = model(x, edge_index)
        loss = loss_fn(out[train_mask], y[train_mask])
        loss.backward()
        optimizer.step()
        losses.append(loss.item())
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{epochs}  loss={loss.item():.5f}")

    return losses


@torch.no_grad()
def evaluate(model, x, edge_index, y, mask):
    model.eval()
    out = model(x, edge_index)
    probs = F.softmax(out, dim=1)[:, 1]  # probability of illicit
    preds = out.argmax(dim=1)

    y_true = y[mask].cpu().numpy()
    y_pred = preds[mask].cpu().numpy()
    y_prob = probs[mask].cpu().numpy()

    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    auc = roc_auc_score(y_true, y_prob)
    cm = confusion_matrix(y_true, y_pred)

    return precision, recall, f1, auc, cm, y_prob, y_true


def plot_loss(losses):
    plt.figure(figsize=(7, 4))
    plt.plot(range(1, len(losses) + 1), losses, color="#0f3460", linewidth=1.5)
    plt.xlabel("Epoch")
    plt.ylabel("Training loss (weighted cross-entropy)")
    plt.title("GAT — Training Loss")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("gnn_loss.png", dpi=150)
    print("Saved gnn_loss.png")


if __name__ == "__main__":
    x, edge_index, y, timestep = load_graph()
    x, edge_index, y = x.to(DEVICE), edge_index.to(DEVICE), y.to(DEVICE)
    train_mask, test_mask = build_masks(y, timestep)
    train_mask, test_mask = train_mask.to(DEVICE), test_mask.to(DEVICE)

    print(f"Train nodes: {train_mask.sum().item()}, Test nodes: {test_mask.sum().item()}")
    print(f"Train illicit rate: {(y[train_mask] == 1).float().mean().item():.4%}")
    print(f"Test illicit rate: {(y[test_mask] == 1).float().mean().item():.4%}")

    model = GAT(input_dim=x.shape[1]).to(DEVICE)
    losses = train(model, x, edge_index, y, train_mask, epochs=200, lr=5e-4)
    plot_loss(losses)

    precision, recall, f1, auc, cm, probs, labels = evaluate(model, x, edge_index, y, test_mask)
    print(f"\n--- Test Evaluation (time-based split, timestep > {TRAIN_MAX_TIMESTEP}) ---")
    print(f"Precision: {precision:.4f}  Recall: {recall:.4f}  F1: {f1:.4f}  AUC-ROC: {auc:.4f}")
    print(f"Confusion matrix:\n{cm}")

    torch.save(model.state_dict(), "gnn_model.pt")
    print("Saved model weights to gnn_model.pt")

    # Save example predictions (true positive / false positive), same pattern as the Transformer
    test_idx = test_mask.nonzero(as_tuple=True)[0].cpu().numpy()
    df = pd.DataFrame({"node_idx": test_idx, "true_label": labels, "predicted_prob": probs})
    df["predicted_label"] = (df["predicted_prob"] >= 0.5).astype(int)
    tp = df[(df.true_label == 1) & (df.predicted_label == 1)].sort_values("predicted_prob", ascending=False)
    fp = df[(df.true_label == 0) & (df.predicted_label == 1)].sort_values("predicted_prob", ascending=False)
    examples = pd.concat([tp.head(2).assign(example_type="true_positive"),
                           fp.head(2).assign(example_type="false_positive")])
    examples.to_csv("gnn_examples.csv", index=False)
    print(f"\nSaved {len(examples)} example predictions to gnn_examples.csv")
    print(examples.to_string(index=False))