"""
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

📌 **Dataset Simulation Note**:
This API is an interactive demo simulation. Payment requests evaluate real precomputed fraud scores 
sampled from actual transactions in the **IEEE-CIS Fraud Detection dataset** (590,540 transactions). 
Graph network subgraphs are built from the **Elliptic Bitcoin Dataset**.

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

# ---------------------------------------------------------------------------
# Load precomputed scores at startup
# ---------------------------------------------------------------------------

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

    return {
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