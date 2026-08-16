"""
FraudShieldAI Streamlit analytics dashboard.

Run:
    streamlit run 10_dashboard.py

This dashboard reads existing artifacts only. It does not train models,
overwrite weights, or fabricate transaction or graph relationships.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import f1_score
from torch_geometric.nn import GATConv

DATA_DIR = Path("data")
FUSION_RESULTS = Path("fusion_results.csv")
AUTOENCODER_EXAMPLES = Path("autoencoder_examples.csv")
TRANSFORMER_EXAMPLES = Path("transformer_examples.csv")
GNN_EXAMPLES = Path("gnn_examples.csv")
GNN_MODEL = Path("gnn_model.pt")
GNN_GRAPH = DATA_DIR / "elliptic_graph.pt"
SEQ_THRESHOLD_STEPS = np.linspace(0.1, 0.95, 34)

st.set_page_config(page_title="FraudShieldAI Analytics", layout="wide")


class GAT(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64, heads: int = 4, dropout: float = 0.3, num_classes: int = 2):
        super().__init__()
        self.gat1 = GATConv(input_dim, hidden_dim, heads=heads, dropout=dropout)
        self.gat2 = GATConv(hidden_dim * heads, hidden_dim, heads=1, concat=False, dropout=dropout)
        self.classifier = nn.Linear(hidden_dim, num_classes)
        self.dropout = dropout

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h = F.elu(self.gat1(x, edge_index))
        h = F.dropout(h, p=self.dropout, training=self.training)
        h = F.elu(self.gat2(h, edge_index))
        return self.classifier(h)


@st.cache_data(show_spinner=False)
def read_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_fusion() -> pd.DataFrame:
    if not FUSION_RESULTS.exists():
        raise FileNotFoundError("fusion_results.csv not found. Run the completed hybrid fusion phase first.")
    return pd.read_csv(FUSION_RESULTS)


@st.cache_data(show_spinner=False)
def fusion_threshold(fusion_df: pd.DataFrame) -> tuple[float, float]:
    labels = fusion_df["true_label"].to_numpy()
    scores = fusion_df["fused_score"].to_numpy()
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in SEQ_THRESHOLD_STEPS:
        f1 = f1_score(labels, (scores >= threshold).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = float(threshold)
    return best_threshold, best_f1


@st.cache_data(show_spinner=False)
def threshold_curve(fusion_df: pd.DataFrame) -> pd.DataFrame:
    labels = fusion_df["true_label"].to_numpy()
    scores = fusion_df["fused_score"].to_numpy()
    rows = []
    for threshold in SEQ_THRESHOLD_STEPS:
        preds = (scores >= threshold).astype(int)
        rows.append({
            "threshold": float(threshold),
            "flagged": int(preds.sum()),
            "f1": float(f1_score(labels, preds, zero_division=0)),
            "precision_at_threshold": float(((preds == 1) & (labels == 1)).sum() / max(preds.sum(), 1)),
        })
    return pd.DataFrame(rows)


@st.cache_resource(show_spinner=False)
def load_gnn_artifacts() -> dict[str, torch.Tensor] | None:
    if not GNN_GRAPH.exists() or not GNN_MODEL.exists():
        return None
    graph = torch.load(GNN_GRAPH, map_location="cpu", weights_only=False)
    model_state = torch.load(GNN_MODEL, map_location="cpu", weights_only=True)
    input_dim = int(model_state["gat1.lin.weight"].shape[1])
    model = GAT(input_dim=input_dim)
    model.load_state_dict(model_state)
    model.eval()
    return {
        "x": graph["x"],
        "edge_index": graph["edge_index"],
        "y": graph["y"],
        "timestep": graph["timestep"],
        "model": model,
    }


@st.cache_data(show_spinner=True)
def score_gnn_nodes() -> pd.DataFrame | None:
    artifacts = load_gnn_artifacts()
    if artifacts is None:
        return None
    with torch.no_grad():
        logits = artifacts["model"](artifacts["x"], artifacts["edge_index"])
        probs = F.softmax(logits, dim=1)[:, 1].cpu().numpy()
        preds = logits.argmax(dim=1).cpu().numpy()
    labels = artifacts["y"].cpu().numpy()
    timesteps = artifacts["timestep"].cpu().numpy()
    df = pd.DataFrame({
        "node_id": np.arange(len(labels)),
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
        ["Known illicit", "Suspicious prediction", "Known licit"],
        default="Unlabeled",
    )
    return df


def subgraph_for_node(node_id: int, hops: int, max_nodes: int) -> tuple[nx.Graph, pd.DataFrame]:
    artifacts = load_gnn_artifacts()
    predictions = score_gnn_nodes()
    if artifacts is None or predictions is None:
        raise RuntimeError("GNN graph/model artifacts are unavailable.")

    n_nodes = int(artifacts["x"].shape[0])
    if node_id < 0 or node_id >= n_nodes:
        raise ValueError(f"Node {node_id} is outside the Elliptic graph.")

    edge_index = artifacts["edge_index"].cpu().numpy()
    src, dst = edge_index
    selected = {int(node_id)}
    frontier = {int(node_id)}
    for _ in range(hops):
        mask = np.isin(src, list(frontier)) | np.isin(dst, list(frontier))
        neighbors = set(src[mask].astype(int).tolist()) | set(dst[mask].astype(int).tolist())
        selected |= neighbors
        frontier = neighbors
        if len(selected) >= max_nodes:
            break

    ranked_nodes = sorted(
        selected,
        key=lambda n: (n != node_id, -float(predictions.iloc[n]["predicted_prob"])),
    )[:max_nodes]
    selected_set = set(ranked_nodes)
    edge_mask = np.isin(src, ranked_nodes) & np.isin(dst, ranked_nodes)

    graph = nx.Graph()
    node_df = predictions.iloc[ranked_nodes].copy()
    for row in node_df.itertuples(index=False):
        graph.add_node(
            int(row.node_id),
            true_label=int(row.true_label),
            predicted_prob=float(row.predicted_prob),
            predicted_label=int(row.predicted_label),
            timestep=int(row.timestep),
            status=str(row.status),
        )
    for s, t in zip(src[edge_mask], dst[edge_mask]):
        s_int, t_int = int(s), int(t)
        if s_int in selected_set and t_int in selected_set:
            graph.add_edge(s_int, t_int)
    return graph, node_df


def plot_subgraph(graph: nx.Graph, center_node: int) -> go.Figure:
    if graph.number_of_nodes() == 0:
        return go.Figure()

    pos = nx.spring_layout(graph, seed=7, k=0.9 / max(graph.number_of_nodes() ** 0.5, 1))
    edge_x, edge_y = [], []
    for source, target in graph.edges():
        x0, y0 = pos[source]
        x1, y1 = pos[target]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(width=0.8, color="#6f7f86"),
        hoverinfo="none",
        showlegend=False,
    )

    colors = {
        "Known illicit": "#ff5c70",
        "Suspicious prediction": "#f5b642",
        "Known licit": "#28d17c",
        "Unlabeled": "#8ea1a8",
    }
    traces = [edge_trace]
    for status, color in colors.items():
        nodes = [n for n, data in graph.nodes(data=True) if data["status"] == status]
        if not nodes:
            continue
        traces.append(go.Scatter(
            x=[pos[n][0] for n in nodes],
            y=[pos[n][1] for n in nodes],
            mode="markers",
            name=status,
            marker=dict(
                size=[18 if n == center_node else 10 + graph.nodes[n]["predicted_prob"] * 10 for n in nodes],
                color=color,
                line=dict(width=[3 if n == center_node else 1 for n in nodes], color="#ffffff"),
            ),
            text=[
                (
                    f"node_id={n}<br>"
                    f"status={graph.nodes[n]['status']}<br>"
                    f"true_label={graph.nodes[n]['true_label']}<br>"
                    f"predicted_prob={graph.nodes[n]['predicted_prob']:.4f}<br>"
                    f"timestep={graph.nodes[n]['timestep']}"
                )
                for n in nodes
            ],
            hoverinfo="text",
        ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=30, b=10),
        plot_bgcolor="#101a1f",
        paper_bgcolor="#101a1f",
        font_color="#eef7f4",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
    )
    return fig


def metric_or_unavailable(value: Any, fmt: str = "{}") -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "Unavailable"
    return fmt.format(value)


st.title("FraudShieldAI Analytics")
st.caption("Research dashboard for completed model artifacts. No model training is performed here.")

fusion_df = load_fusion()
ae_examples = read_csv(AUTOENCODER_EXAMPLES)
tf_examples = read_csv(TRANSFORMER_EXAMPLES)
gnn_examples = read_csv(GNN_EXAMPLES)
best_threshold, best_f1 = fusion_threshold(fusion_df)
fusion_df = fusion_df.copy()
fusion_df["flagged_at_existing_threshold"] = fusion_df["fused_score"] >= best_threshold

st.header("Architecture")
left_arch, right_arch = st.columns(2)
with left_arch:
    st.subheader("Transaction Risk Engine")
    st.code("IEEE-CIS transactions\n  -> Autoencoder\n  -> Transformer\n  -> Hybrid Fusion\n  -> Transaction risk score", language="text")
    st.caption("The hybrid score is the numerical fusion used for transaction-level risk in fusion_results.csv.")
with right_arch:
    st.subheader("Network Intelligence")
    st.code("Elliptic graph\n  -> GNN/GAT\n  -> Suspicious Subgraph Analysis", language="text")
    st.caption("The GNN runs on the Elliptic graph and is not numerically included in the IEEE-CIS fusion.")

st.divider()

st.header("Dataset Overview")
overview_cols = st.columns(5)
overview_cols[0].metric("Fusion Transactions", f"{len(fusion_df):,}")
overview_cols[1].metric("Actual Fraud", f"{int(fusion_df['true_label'].sum()):,}")
overview_cols[2].metric("Fraud Rate", f"{fusion_df['true_label'].mean():.2%}")
overview_cols[3].metric("Existing Threshold", f"{best_threshold:.4f}")
overview_cols[4].metric("Best F1 at Threshold", f"{best_f1:.4f}")

gnn_artifacts = load_gnn_artifacts()
if gnn_artifacts is not None:
    graph_cols = st.columns(4)
    graph_cols[0].metric("Elliptic Nodes", f"{int(gnn_artifacts['x'].shape[0]):,}")
    graph_cols[1].metric("Elliptic Edges", f"{int(gnn_artifacts['edge_index'].shape[1]):,}")
    graph_cols[2].metric("Known Illicit Nodes", f"{int((gnn_artifacts['y'] == 1).sum()):,}")
    graph_cols[3].metric("Unlabeled Nodes", f"{int((gnn_artifacts['y'] == -1).sum()):,}")
else:
    st.warning("GNN graph/model artifacts are unavailable, so Network Intelligence sections cannot render.")

st.divider()

st.header("Hybrid Fusion Results")
fusion_cols = st.columns(4)
fusion_cols[0].metric("Transactions Flagged", f"{int(fusion_df['flagged_at_existing_threshold'].sum()):,}")
fusion_cols[1].metric("Average Fused Score", f"{fusion_df['fused_score'].mean():.4f}")
fusion_cols[2].metric("Average Autoencoder Score", f"{fusion_df['autoencoder_score'].mean():.4f}")
fusion_cols[3].metric("Average Transformer Score", f"{fusion_df['transformer_score'].mean():.4f}")

score_left, score_right = st.columns(2)
with score_left:
    label_names = fusion_df["true_label"].map({0: "Legitimate", 1: "Fraud"})
    fig = px.histogram(
        fusion_df,
        x="fused_score",
        color=label_names,
        nbins=60,
        barmode="overlay",
        opacity=0.7,
        color_discrete_map={"Legitimate": "#28d17c", "Fraud": "#ff5c70"},
    )
    fig.add_vline(x=best_threshold, line_dash="dash", line_color="#f5b642", annotation_text="existing threshold")
    fig.update_layout(title="Score Distributions", xaxis_title="Fused score", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

with score_right:
    sample = fusion_df.sample(min(4000, len(fusion_df)), random_state=7)
    fig = px.scatter(
        sample,
        x="autoencoder_score",
        y="transformer_score",
        color=sample["true_label"].map({0: "Legitimate", 1: "Fraud"}),
        size="fused_score",
        opacity=0.55,
        color_discrete_map={"Legitimate": "#28d17c", "Fraud": "#ff5c70"},
    )
    fig.update_layout(title="Model Contribution Comparison", xaxis_title="Autoencoder", yaxis_title="Transformer")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Threshold Analysis")
curve = threshold_curve(fusion_df)
threshold_chart = go.Figure()
threshold_chart.add_trace(go.Scatter(x=curve["threshold"], y=curve["f1"], mode="lines+markers", name="F1"))
threshold_chart.add_trace(go.Scatter(x=curve["threshold"], y=curve["precision_at_threshold"], mode="lines+markers", name="Precision among flagged"))
threshold_chart.add_vline(x=best_threshold, line_dash="dash", line_color="#f5b642")
threshold_chart.update_layout(xaxis_title="Threshold", yaxis_title="Metric", height=360)
st.plotly_chart(threshold_chart, use_container_width=True)
st.dataframe(curve.sort_values("f1", ascending=False).head(10), use_container_width=True)

st.divider()

st.header("Autoencoder Results")
ae_cols = st.columns(2)
with ae_cols[0]:
    st.image("autoencoder_results.png", caption="Saved autoencoder result plot", use_container_width=True)
with ae_cols[1]:
    if ae_examples is not None:
        st.subheader("Example Predictions")
        st.dataframe(ae_examples, use_container_width=True)
    else:
        st.info("autoencoder_examples.csv is unavailable.")

st.header("Transformer Results")
tf_cols = st.columns(2)
with tf_cols[0]:
    st.image("transformer_loss.png", caption="Saved transformer training loss", use_container_width=True)
with tf_cols[1]:
    if tf_examples is not None:
        st.subheader("Example Predictions")
        st.dataframe(tf_examples, use_container_width=True)
    else:
        st.info("transformer_examples.csv is unavailable.")

st.divider()

st.header("GNN Results")
gnn_cols = st.columns(2)
with gnn_cols[0]:
    st.image("gnn_loss.png", caption="Saved GAT training loss", use_container_width=True)
with gnn_cols[1]:
    if gnn_examples is not None:
        st.subheader("Existing GNN Example Predictions")
        st.dataframe(gnn_examples, use_container_width=True)
    else:
        st.info("gnn_examples.csv is unavailable.")

st.subheader("GNN Network Intelligence")
st.caption("Suspicious Subgraph Analysis uses actual Elliptic graph edges and frozen GNN predictions. It is separate from IEEE-CIS fusion.")

gnn_predictions = score_gnn_nodes()
if gnn_predictions is not None:
    suspicious = gnn_predictions[
        (gnn_predictions["predicted_label"] == 1) | (gnn_predictions["true_label"] == 1)
    ].sort_values("predicted_prob", ascending=False)

    gnn_metric_cols = st.columns(4)
    gnn_metric_cols[0].metric("Suspicious / Illicit Nodes", f"{len(suspicious):,}")
    gnn_metric_cols[1].metric("Predicted Illicit", f"{int((gnn_predictions['predicted_label'] == 1).sum()):,}")
    gnn_metric_cols[2].metric("Known Illicit", f"{int((gnn_predictions['true_label'] == 1).sum()):,}")
    gnn_metric_cols[3].metric("Average Suspicious Prob.", f"{suspicious['predicted_prob'].mean():.4f}")

    st.dataframe(
        suspicious[["node_id", "true_label", "predicted_prob", "predicted_label", "timestep", "status"]].head(50),
        use_container_width=True,
    )

    controls = st.columns([2, 1, 1])
    default_node = int(suspicious.iloc[0]["node_id"]) if not suspicious.empty else 0
    selected_node = controls[0].selectbox(
        "Select suspicious node",
        suspicious["node_id"].head(100).astype(int).tolist(),
        index=0,
    )
    hops = controls[1].selectbox("Neighborhood", [1, 2], index=0)
    max_nodes = controls[2].slider("Max nodes", min_value=20, max_value=180, value=90, step=10)

    try:
        graph, node_df = subgraph_for_node(int(selected_node or default_node), hops=int(hops), max_nodes=int(max_nodes))
        subgraph_cols = st.columns(3)
        subgraph_cols[0].metric("Subgraph Nodes", f"{graph.number_of_nodes():,}")
        subgraph_cols[1].metric("Subgraph Edges", f"{graph.number_of_edges():,}")
        subgraph_cols[2].metric("Center Node", str(int(selected_node)))
        st.plotly_chart(plot_subgraph(graph, int(selected_node)), use_container_width=True)
        st.dataframe(
            node_df[["node_id", "true_label", "predicted_prob", "predicted_label", "timestep", "status"]]
            .sort_values("predicted_prob", ascending=False)
            .head(100),
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"Could not generate subgraph: {exc}")
else:
    st.info("GNN graph/model artifacts are unavailable, so suspicious subgraph analysis is disabled.")

st.divider()

st.header("Model Comparison")
comparison = pd.DataFrame([
    {"Model": "Autoencoder", "Dataset": "IEEE-CIS", "Output": "Reconstruction anomaly score", "Used in Hybrid Fusion": "Yes"},
    {"Model": "Transformer", "Dataset": "IEEE-CIS", "Output": "Behavioral fraud probability", "Used in Hybrid Fusion": "Yes"},
    {"Model": "Hybrid Fusion", "Dataset": "IEEE-CIS", "Output": "Transaction risk score", "Used in Hybrid Fusion": "Final score"},
    {"Model": "GNN/GAT", "Dataset": "Elliptic", "Output": "Network illicit probability", "Used in Hybrid Fusion": "No"},
])
st.dataframe(comparison, use_container_width=True)

st.divider()

st.header("Federated Learning Proof-of-Concept")
fl_cols = st.columns([1, 1])
with fl_cols[0]:
    st.code("Client A        Client B\n   |              |\nLocal Training  Local Training\n   \\              /\n        FedAvg\n          |\n    Global Model", language="text")
with fl_cols[1]:
    st.write("Existing implementation: `08_federated_stub.py`")
    st.write("Clients: 2")
    st.write("Rounds configured: 5")
    st.write("Local epochs per round: 3")
    st.write("Aggregation: manual FedAvg")
    st.info("No saved FL metrics file was found, so round losses/AUC values are labeled unavailable rather than invented.")

fl_metrics = pd.DataFrame([
    {"Metric": "Round loss history", "Value": "Unavailable - script prints to console only"},
    {"Metric": "Client A AUC", "Value": "Unavailable - no saved artifact"},
    {"Metric": "Client B AUC", "Value": "Unavailable - no saved artifact"},
    {"Metric": "Global model metric", "Value": "Unavailable - no saved artifact"},
])
st.dataframe(fl_metrics, use_container_width=True)

st.caption("Phase 3 complete: analytics and network intelligence use existing project artifacts only.")
