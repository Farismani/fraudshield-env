"""
Day 1: Data preparation for IEEE-CIS Fraud Detection dataset.
Run this first. Produces data/processed_transactions.csv used by every
downstream model (Autoencoder, Transformer).

Expects: data/train_transaction.csv, data/train_identity.csv
(from `kaggle competitions download -c ieee-fraud-detection`)
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

DATA_DIR = "data"

def load_and_merge():
    print("Loading raw files...")
    txn = pd.read_csv(f"{DATA_DIR}/train_transaction.csv")
    identity = pd.read_csv(f"{DATA_DIR}/train_identity.csv")
    df = txn.merge(identity, on="TransactionID", how="left")
    print(f"Merged shape: {df.shape}")
    return df


def basic_eda(df):
    fraud_rate = df["isFraud"].mean()
    print(f"Fraud rate: {fraud_rate:.4%}  (class imbalance — keep this in mind for every model's metrics)")
    missing_pct = df.isna().mean().sort_values(ascending=False)
    print("\nTop 10 columns by missing %:")
    print(missing_pct.head(10))


def preprocess(df, max_missing_frac=0.95):
    # Keep TransactionID, TransactionDT, isFraud, and columns useful for a
    # pseudo user-ID (needed later for the Transformer's per-user sequences).
    id_cols = ["TransactionID", "TransactionDT", "isFraud", "card1", "card2", "addr1"]

    # Build the proxy user ID BEFORE dropping/altering card1/card2/addr1
    user_id = (
        df["card1"].astype(str) + "_" +
        df["card2"].fillna(-1).astype(str) + "_" +
        df["addr1"].fillna(-1).astype(str)
    )

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in id_cols]
    categorical_cols = df.select_dtypes(include=["object"]).columns.tolist()

    # Drop columns that are almost entirely missing (e.g. id_07, id_08 are
    # >99% NaN here) — their median is NaN, which silently poisons every
    # downstream row with NaN and breaks training. Better to drop them.
    missing_frac = df[numeric_cols].isna().mean()
    dropped = missing_frac[missing_frac > max_missing_frac].index.tolist()
    if dropped:
        print(f"Dropping {len(dropped)} numeric columns >{max_missing_frac:.0%} missing: {dropped[:10]}{'...' if len(dropped) > 10 else ''}")
    numeric_cols = [c for c in numeric_cols if c not in dropped]

    # Fill missing values (median is now guaranteed non-NaN for kept columns)
    medians = df[numeric_cols].median()
    df.loc[:, numeric_cols] = df[numeric_cols].fillna(medians)

    df.loc[:, categorical_cols] = df[categorical_cols].fillna("missing")
    for col in categorical_cols:
        df[col] = df[col].astype("category").cat.codes

    # Replace any remaining inf/-inf (can appear from ratio-like raw features)
    df.loc[:, numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    df.loc[:, numeric_cols] = df[numeric_cols].fillna(0)  # final safety net

    # Scale numerics
    scaler = StandardScaler()
    df.loc[:, numeric_cols] = scaler.fit_transform(df[numeric_cols])

    # card1/card2/addr1 are excluded from numeric_cols (reserved for user_id)
    # but they DO remain in the final feature set below and can contain NaN
    # (e.g. addr1, card2) — fill them explicitly so nothing slips through.
    id_feature_cols = ["card1", "card2", "addr1"]
    df.loc[:, id_feature_cols] = df[id_feature_cols].fillna(-1)

    df["user_id"] = user_id

    keep_cols = id_cols + categorical_cols + numeric_cols + ["user_id"]
    keep_cols = list(dict.fromkeys(keep_cols))  # dedupe, preserve order
    result = df[keep_cols].copy()  # de-fragment, silences the PerformanceWarning too

    # Final sanity check — should never fire, but fail loudly instead of
    # silently training on NaNs if it ever does
    n_nan = result[numeric_cols + id_feature_cols].isna().sum().sum()
    assert n_nan == 0, f"{n_nan} NaNs remain after preprocessing — check raw data"

    return result


if __name__ == "__main__":
    df = load_and_merge()
    basic_eda(df)
    processed = preprocess(df)
    processed = processed.sort_values("TransactionDT").reset_index(drop=True)
    out_path = f"{DATA_DIR}/processed_transactions.csv"
    processed.to_csv(out_path, index=False)
    print(f"\nSaved processed data to {out_path}  shape={processed.shape}")