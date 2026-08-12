"""
Day 7b: Streamlit dashboard — visualizes fused fraud scores, model comparison,
and (if available) GNN fraud-ring structure.

Run: streamlit run 10_dashboard.py

Reads fusion_results.csv (from 07_hybrid_fusion.py) and gnn_examples.csv
(from 06_train_gnn.py) if present — no live API call needed for the
review demo, though it could be pointed at 09_api.py's /predict endpoint
for a live version later.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="FraudShieldAI Dashboard", layout="wide")

st.title("🛡️ FraudShieldAI — Fraud Intelligence Dashboard")
st.caption("Real-time fraud risk monitoring — Behavioral Transformer + Autoencoder + GNN")

# ---- Load data ----
try:
    fusion_df = pd.read_csv("fusion_results.csv")
except FileNotFoundError:
    st.error("fusion_results.csv not found — run 07_hybrid_fusion.py first.")
    st.stop()

try:
    gnn_df = pd.read_csv("gnn_examples.csv")
except FileNotFoundError:
    gnn_df = None

# ---- Top metrics row ----
col1, col2, col3, col4 = st.columns(4)
total_tx = len(fusion_df)
flagged = (fusion_df["fused_score"] >= fusion_df["fused_score"].median()).sum()  # placeholder threshold for display
actual_fraud = fusion_df["true_label"].sum()
fraud_rate = fusion_df["true_label"].mean()

col1.metric("Transactions scored", f"{total_tx:,}")
col2.metric("Actual fraud in set", f"{actual_fraud:,}")
col3.metric("Fraud rate", f"{fraud_rate:.2%}")
col4.metric("Avg. fused score", f"{fusion_df['fused_score'].mean():.3f}")

st.divider()

# ---- Score distribution ----
left, right = st.columns(2)

with left:
    st.subheader("Fused Risk Score Distribution")
    fig = px.histogram(
        fusion_df, x="fused_score", color=fusion_df["true_label"].map({0: "Legitimate", 1: "Fraud"}),
        nbins=50, opacity=0.7, barmode="overlay",
        color_discrete_map={"Legitimate": "#0f3460", "Fraud": "#e94560"},
    )
    fig.update_layout(xaxis_title="Fused fraud risk score", yaxis_title="Count", legend_title="Actual label")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Model Contribution Comparison")
    sample = fusion_df.sample(min(2000, len(fusion_df)), random_state=1)
    fig2 = px.scatter(
        sample, x="autoencoder_score", y="transformer_score", color=sample["true_label"].map({0: "Legitimate", 1: "Fraud"}),
        color_discrete_map={"Legitimate": "#0f3460", "Fraud": "#e94560"}, opacity=0.6,
    )
    fig2.update_layout(xaxis_title="Autoencoder score", yaxis_title="Transformer score", legend_title="Actual label")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ---- Live transaction feed (top riskiest) ----
st.subheader("🚨 Highest-Risk Transactions")
threshold = st.slider("Flag threshold (fused score)", 0.0, 1.0, float(fusion_df["fused_score"].quantile(0.95)), 0.01)
flagged_df = fusion_df[fusion_df["fused_score"] >= threshold].sort_values("fused_score", ascending=False)
st.write(f"{len(flagged_df)} transactions flagged at this threshold "
         f"({(flagged_df['true_label'] == 1).sum()} are actual fraud)")
st.dataframe(
    flagged_df[["TransactionID", "true_label", "autoencoder_score", "transformer_score", "fused_score"]].head(50),
    use_container_width=True,
)

st.divider()

# ---- GNN fraud-ring examples, if available ----
if gnn_df is not None:
    st.subheader("🕸️ GNN — Flagged Account/Transaction Nodes (Elliptic graph)")
    st.dataframe(gnn_df, use_container_width=True)
    st.caption(
        "These node-level predictions come from the graph model and are not directly joined to the "
        "IEEE-CIS transactions above — see the project report for why (different datasets, no shared "
        "transaction IDs). In production, both would be joined at the account level."
    )
else:
    st.info("Run 06_train_gnn.py to populate the GNN section of this dashboard.")

st.divider()
st.caption("FraudShieldAI — Phase-1 demo dashboard. Fusion currently combines Autoencoder + Transformer only.")