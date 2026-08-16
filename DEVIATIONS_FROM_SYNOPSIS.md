# Deviations from Synopsis

This document lists the deliberate deviations taken from the original project synopsis during the implementation of the FraudShieldAI application/demo layer.

1. **Federated Learning Implementation**: The Federated Learning component was implemented as a manual FedAvg routine in pure PyTorch instead of using the Flower library. This was due to a Ray dependency incompatibility with the Python version used in the project environment.

2. **Fraud-Ring Visualization (GNN)**: The graph visualization (Task 3) is an illustrative visualization rendering a subset/subgraph (~30 nodes, centered around flagged illicit nodes) rather than the full 200,000+ node Elliptic graph. This is for rendering-performance reasons, ensuring the bank dashboard remains responsive.
