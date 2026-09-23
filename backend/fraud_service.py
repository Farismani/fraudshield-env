"""Read-only fraud scoring adapter for the payment demo.

This module only reads the frozen fusion result artifact. It never trains,
changes, or writes model files. Live model inference is intentionally kept
outside this adapter until the protected model artifacts are restored.
"""

from __future__ import annotations

import hashlib
import csv
from pathlib import Path

FUSION_THRESHOLD = 0.8212121212121212


class ReadOnlyFraudService:
    """Provide deterministic scores from the existing frozen result table."""

    def __init__(self, result_path: Path = Path("fusion_results.csv")) -> None:
        self.result_path = result_path
        self._results: list[dict[str, str]] | None = None

    def _load(self) -> list[dict[str, str]] | None:
        if self._results is None:
            try:
                with self.result_path.open("r", newline="", encoding="utf-8") as handle:
                    self._results = list(csv.DictReader(handle))
            except FileNotFoundError:
                return None
        return self._results

    def score_hint(self, sender_id: str, receiver_id: str, amount: float) -> dict | None:
        """Return a stable, read-only precomputed score for this demo payment."""
        results = self._load()
        if not results:
            return None

        key = f"{sender_id}|{receiver_id}|{amount:.2f}".encode("utf-8")
        row_index = int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % len(results)
        row = results[row_index]
        fused_score = float(row["fused_score"])
        return {
            "source": "precomputed_fusion_results",
            "transaction_id": str(row["TransactionID"]),
            "autoencoder_score": round(float(row["autoencoder_score"]), 4),
            "transformer_score": round(float(row["transformer_score"]), 4),
            "fused_score": round(fused_score, 4),
            "flagged": fused_score >= FUSION_THRESHOLD,
        }


fraud_service = ReadOnlyFraudService()
