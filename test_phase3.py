#!/usr/bin/env python3
"""
Phase 3 Testing Script
Tests GNN visualization, Streamlit dashboard, and API endpoints.
"""

import sys
import subprocess
import time
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported."""
    print("✓ Testing imports...")
    try:
        import streamlit
        import torch
        import torch.nn as nn
        from torch_geometric.nn import GATConv
        import networkx as nx
        import plotly.graph_objects as go
        import plotly.express as px
        import pandas as pd
        import numpy as np
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False

def test_files_exist():
    """Test that all required artifact files exist."""
    print("\n✓ Testing artifact files...")
    required_files = [
        Path("fusion_results.csv"),
        Path("autoencoder_model.pt"),
        Path("transformer_model.pt"),
        Path("gnn_model.pt"),
        Path("data/elliptic_graph.pt"),
        Path("autoencoder_results.png"),
        Path("transformer_loss.png"),
        Path("gnn_loss.png"),
        Path("09_api.py"),
        Path("10_dashboard.py"),
        Path("11_bank_dashboard.html"),
    ]
    
    all_exist = True
    for f in required_files:
        if f.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} missing")
            all_exist = False
    return all_exist

def test_fusion_results():
    """Test that fusion results contain expected data."""
    print("\n✓ Testing fusion results...")
    try:
        import pandas as pd
        fusion_df = pd.read_csv("fusion_results.csv")
        print(f"  ✓ Loaded {len(fusion_df)} fusion results")
        print(f"  ✓ Columns: {', '.join(fusion_df.columns)}")
        print(f"  ✓ Fraud rate: {fusion_df['true_label'].mean():.2%}")
        print(f"  ✓ Autoencoder score range: [{fusion_df['autoencoder_score'].min():.4f}, {fusion_df['autoencoder_score'].max():.4f}]")
        print(f"  ✓ Transformer score range: [{fusion_df['transformer_score'].min():.4f}, {fusion_df['transformer_score'].max():.4f}]")
        print(f"  ✓ Fused score range: [{fusion_df['fused_score'].min():.4f}, {fusion_df['fused_score'].max():.4f}]")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_gnn_artifacts():
    """Test that GNN artifacts can be loaded."""
    print("\n✓ Testing GNN artifacts...")
    try:
        import torch
        from pathlib import Path
        
        # Load graph
        graph = torch.load(Path("data/elliptic_graph.pt"), map_location="cpu", weights_only=False)
        print(f"  ✓ Loaded Elliptic graph with {graph['x'].shape[0]:,} nodes")
        print(f"  ✓ Graph edges: {graph['edge_index'].shape[1]:,}")
        print(f"  ✓ Node features: {graph['x'].shape[1]}")
        print(f"  ✓ Known illicit nodes: {(graph['y'] == 1).sum().item():,}")
        
        # Load model
        model_state = torch.load(Path("gnn_model.pt"), map_location="cpu", weights_only=True)
        print(f"  ✓ Loaded GNN model state dict with {len(model_state)} parameters")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_api_syntax():
    """Test that API code compiles."""
    print("\n✓ Testing API syntax...")
    try:
        import py_compile
        py_compile.compile("09_api.py", doraise=True)
        print("  ✓ API code compiles successfully")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_dashboard_syntax():
    """Test that dashboard code compiles."""
    print("\n✓ Testing dashboard syntax...")
    try:
        import py_compile
        py_compile.compile("10_dashboard.py", doraise=True)
        print("  ✓ Dashboard code compiles successfully")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("FRAUDSHIELDAI PHASE 3 TESTING")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Files", test_files_exist),
        ("Fusion Results", test_fusion_results),
        ("GNN Artifacts", test_gnn_artifacts),
        ("API Syntax", test_api_syntax),
        ("Dashboard Syntax", test_dashboard_syntax),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result for _, result in results)
    print("=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
        print("\nNext steps:")
        print("1. Start FastAPI: uvicorn 09_api:app --reload")
        print("2. Start Streamlit: streamlit run 10_dashboard.py")
        print("3. Test GNN endpoints: http://127.0.0.1:8000/gnn/suspicious")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
