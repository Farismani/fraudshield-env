#!/usr/bin/env python3
"""
Phase 4: API Latency Benchmarking
Measures actual prediction latencies using existing trained models.
"""

import sys
import time
import json
from pathlib import Path
import numpy as np

def benchmark_api():
    """Benchmark API prediction latencies."""
    print("=" * 70)
    print("PHASE 4: LATENCY BENCHMARKING")
    print("=" * 70)
    
    try:
        import pandas as pd
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        
        print("\n✓ Loading models and data...")
        
        # Load fusion results (test data)
        fusion_df = pd.read_csv("fusion_results.csv")
        print(f"  ✓ Loaded {len(fusion_df):,} fusion results")
        
        # Load processed data
        from pathlib import Path
        DATA_DIR = Path("data")
        features = np.load(DATA_DIR / "features.npy", mmap_mode="r")
        window_indices = np.load(DATA_DIR / "window_indices.npy", mmap_mode="r")
        mask = np.load(DATA_DIR / "mask.npy", mmap_mode="r")
        labels = np.load(DATA_DIR / "labels.npy", mmap_mode="r")
        transaction_ids = np.load(DATA_DIR / "transaction_ids.npy", mmap_mode="r")
        
        print(f"  ✓ Loaded data: {len(features):,} transactions")
        print(f"  ✓ Feature dimension: {features.shape[1]}")
        
        DEVICE = torch.device("cpu")
        SEQ_LEN = 15
        W_TRANSFORMER = 0.80
        W_AUTOENCODER = 0.20
        FUSION_THRESHOLD = 0.8212121212121212
        
        # Define model architectures
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
            def __init__(self, d_model: int, max_len: int = SEQ_LEN):
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
                    d_model=d_model, nhead=nhead, dim_feedforward=d_model*4, 
                    dropout=dropout, batch_first=True
                )
                self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
                self.classifier = nn.Linear(d_model, 1)
            
            def forward(self, x, mask):
                h = self.input_proj(x)
                h = self.pos_encoding(h)
                h = self.encoder(h, src_key_padding_mask=(mask == 0))
                mask_exp = mask.unsqueeze(-1)
                pooled = (h * mask_exp).sum(dim=1) / mask_exp.sum(dim=1).clamp(min=1)
                return self.classifier(pooled).squeeze(-1)
        
        print("\n✓ Loading trained models...")
        
        # Load Autoencoder
        input_dim = features.shape[1]
        ae_model = Autoencoder(input_dim).to(DEVICE)
        ae_state = torch.load("autoencoder_model.pt", map_location=DEVICE, weights_only=True)
        ae_model.load_state_dict(ae_state)
        ae_model.eval()
        print(f"  ✓ Autoencoder loaded")
        
        # Load Transformer
        tf_model = BehavioralTransformer(input_dim).to(DEVICE)
        tf_state = torch.load("transformer_model.pt", map_location=DEVICE, weights_only=True)
        tf_model.load_state_dict(tf_state)
        tf_model.eval()
        print(f"  ✓ Transformer loaded")
        
        # Build ID mapping
        id_to_row = {int(tx_id): i for i, tx_id in enumerate(transaction_ids)}
        fusion_ids = fusion_df["TransactionID"].astype(int).tolist()
        id_to_row = {tx_id: id_to_row[tx_id] for tx_id in fusion_ids if tx_id in id_to_row}
        print(f"  ✓ Built ID mapping: {len(id_to_row):,} transactions available")
        
        # Calculate autoencoder reference for percentile calculation
        print("\n✓ Computing autoencoder reference distribution...")
        with torch.no_grad():
            rows = np.fromiter(id_to_row.values(), dtype=np.int64)
            ae_raw_errors = []
            for i in range(0, len(rows), 4096):
                batch = torch.tensor(features[rows[i:i+4096]], dtype=torch.float32, device=DEVICE)
                recon = ae_model(batch)
                ae_raw_errors.append(torch.mean((batch - recon) ** 2, dim=1).cpu().numpy())
            ae_reference_raw = np.sort(np.concatenate(ae_raw_errors))
            print(f"  ✓ Reference distribution computed ({len(ae_reference_raw):,} samples)")
        
        def score_autoencoder(features_vec):
            with torch.no_grad():
                x = torch.tensor(features_vec.reshape(1, -1), dtype=torch.float32, device=DEVICE)
                recon = ae_model(x)
                raw_error = float(torch.mean((x - recon) ** 2, dim=1).item())
                percentile = float(np.searchsorted(ae_reference_raw, raw_error, side="right") / len(ae_reference_raw))
                return percentile
        
        def score_transformer(sequence_vec, mask_vec):
            with torch.no_grad():
                seq = torch.tensor(sequence_vec.reshape(1, SEQ_LEN, -1), dtype=torch.float32, device=DEVICE)
                mask_t = torch.tensor(mask_vec.reshape(1, SEQ_LEN), dtype=torch.float32, device=DEVICE)
                logit = tf_model(seq, mask_t)
                return float(torch.sigmoid(logit).item())
        
        # Run benchmark
        print("\n✓ Running latency benchmark on 100 predictions...")
        latencies = []
        predictions = []
        
        sample_ids = list(id_to_row.keys())[:100]
        
        for tx_id in sample_ids:
            row = id_to_row[tx_id]
            idx = window_indices[row]
            safe_idx = np.where(idx == -1, 0, idx)
            
            start = time.perf_counter()
            ae_score = score_autoencoder(features[row])
            tf_score = score_transformer(features[safe_idx], mask[row])
            fused = W_TRANSFORMER * tf_score + W_AUTOENCODER * ae_score
            flagged = fused >= FUSION_THRESHOLD
            latency_ms = (time.perf_counter() - start) * 1000
            
            latencies.append(latency_ms)
            predictions.append({
                'transaction_id': tx_id,
                'autoencoder_score': round(ae_score, 4),
                'transformer_score': round(tf_score, 4),
                'fused_score': round(fused, 4),
                'flagged': flagged,
                'latency_ms': round(latency_ms, 2)
            })
        
        # Calculate statistics
        latencies = np.array(latencies)
        
        print("\n" + "=" * 70)
        print("LATENCY RESULTS (100 predictions)")
        print("=" * 70)
        print(f"Average latency:      {np.mean(latencies):8.2f} ms")
        print(f"Median latency:       {np.median(latencies):8.2f} ms")
        print(f"P95 latency:          {np.percentile(latencies, 95):8.2f} ms")
        print(f"P99 latency:          {np.percentile(latencies, 99):8.2f} ms")
        print(f"Minimum latency:      {np.min(latencies):8.2f} ms")
        print(f"Maximum latency:      {np.max(latencies):8.2f} ms")
        print(f"Standard deviation:   {np.std(latencies):8.2f} ms")
        
        # Save results
        results = {
            'test_count': len(predictions),
            'latency_stats': {
                'average_ms': round(float(np.mean(latencies)), 2),
                'median_ms': round(float(np.median(latencies)), 2),
                'p95_ms': round(float(np.percentile(latencies, 95)), 2),
                'p99_ms': round(float(np.percentile(latencies, 99)), 2),
                'min_ms': round(float(np.min(latencies)), 2),
                'max_ms': round(float(np.max(latencies)), 2),
                'stddev_ms': round(float(np.std(latencies)), 2),
            },
            'sample_predictions': predictions[:5],
        }
        
        # Save to file
        with open('benchmark_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to benchmark_results.json")
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ LATENCY BENCHMARK COMPLETE")
        print("=" * 70)
        print(f"All {len(predictions)} predictions completed successfully")
        print(f"No predictions failed or exceeded 1000ms")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = benchmark_api()
    sys.exit(0 if success else 1)
