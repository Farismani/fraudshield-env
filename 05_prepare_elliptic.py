"""
Day 5a: Prepare the Elliptic Bitcoin dataset as a graph for the GNN.

Expects (from `kaggle datasets download -d ellipticco/elliptic-data-set`,
unzipped into data/elliptic_bitcoin_dataset/):
  - elliptic_txs_features.csv   (no header: txId, timestep, 165 features)
  - elliptic_txs_classes.csv    (header: txId, class — '1'=illicit, '2'=licit, 'unknown')
  - elliptic_txs_edgelist.csv   (header: txId1, txId2)

Produces data/elliptic_graph.pt — a saved PyTorch Geometric Data object with:
  - x            : node features (203k nodes x 165 features)
  - edge_index   : graph edges
  - y            : labels (1=illicit, 0=licit, -1=unknown/unlabeled)
  - timestep     : time step per node (1-49) — used for a time-based split
"""

import pandas as pd
import numpy as np
import torch

DATA_DIR = "data/elliptic_bitcoin_dataset"
OUT_DIR = "data"


def load_elliptic():
    # Features file has no header: col0=txId, col1=timestep, col2..166=165 features
    feat_cols = ["txId", "timestep"] + [f"feat_{i}" for i in range(165)]
    features = pd.read_csv(f"{DATA_DIR}/elliptic_txs_features.csv", header=None, names=feat_cols)

    classes = pd.read_csv(f"{DATA_DIR}/elliptic_txs_classes.csv")
    edges = pd.read_csv(f"{DATA_DIR}/elliptic_txs_edgelist.csv")

    print(f"Features: {features.shape}, Classes: {classes.shape}, Edges: {edges.shape}")
    return features, classes, edges


def build_graph(features, classes, edges):
    # Map class labels: '1' (illicit) -> 1, '2' (licit) -> 0, 'unknown' -> -1
    label_map = {"1": 1, "2": 0, "unknown": -1}
    classes["label"] = classes["class"].astype(str).map(label_map)

    df = features.merge(classes[["txId", "label"]], on="txId", how="left")
    df["label"] = df["label"].fillna(-1).astype(int)

    # Build node index mapping (txId -> contiguous integer index)
    tx_to_idx = {tx: i for i, tx in enumerate(df["txId"].values)}

    feature_cols = [c for c in df.columns if c.startswith("feat_")]
    x = torch.tensor(df[feature_cols].values, dtype=torch.float32)
    y = torch.tensor(df["label"].values, dtype=torch.long)
    timestep = torch.tensor(df["timestep"].values, dtype=torch.long)

    # Build edge_index, dropping any edge referencing a txId not in the feature set
    valid_edges = edges[edges["txId1"].isin(tx_to_idx) & edges["txId2"].isin(tx_to_idx)]
    src = valid_edges["txId1"].map(tx_to_idx).values
    dst = valid_edges["txId2"].map(tx_to_idx).values
    edge_index = torch.tensor(np.stack([src, dst]), dtype=torch.long)
    # Make the graph undirected (helps message passing — Elliptic edges are directional but
    # fraud relationships are informative in both directions for detection purposes)
    edge_index = torch.cat([edge_index, edge_index.flip(0)], dim=1)

    n_labeled = (y != -1).sum().item()
    n_illicit = (y == 1).sum().item()
    n_licit = (y == 0).sum().item()
    print(f"\nNodes: {x.shape[0]}, Features/node: {x.shape[1]}, Edges (directed, incl. reverse): {edge_index.shape[1]}")
    print(f"Labeled nodes: {n_labeled} ({n_illicit} illicit, {n_licit} licit), "
          f"Unlabeled: {x.shape[0] - n_labeled}")
    print(f"Illicit rate among labeled nodes: {n_illicit / n_labeled:.4%}")
    print(f"Timestep range: {timestep.min().item()} to {timestep.max().item()}")

    return {"x": x, "edge_index": edge_index, "y": y, "timestep": timestep}


if __name__ == "__main__":
    features, classes, edges = load_elliptic()
    graph = build_graph(features, classes, edges)
    torch.save(graph, f"{OUT_DIR}/elliptic_graph.pt")
    print(f"\nSaved graph to {OUT_DIR}/elliptic_graph.pt")