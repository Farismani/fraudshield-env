"""
Day 3: Build per-user transaction sequences for the Behavioral Transformer.

Instead of materializing every (sequence_length x num_features) window upfront
(which would need ~15GB RAM for this dataset), this script saves:
  - features.npy        : (num_rows, num_features) scaled feature matrix
  - window_indices.npy  : (num_rows, seq_len) row-indices for each window, -1 = pad
  - mask.npy            : (num_rows, seq_len) 1 = real transaction, 0 = pad
  - labels.npy          : (num_rows,) isFraud for the LAST transaction in each window
  - transaction_ids.npy : (num_rows,) original TransactionID, for tracing examples later
  - user_ids.npy        : (num_rows,) proxy user id, needed for a user-level train/test split

04_train_transformer.py gathers each window on the fly from features.npy using
window_indices.npy — no giant array is ever built.

Run after 01_data_prep.py.
"""

import pandas as pd
import numpy as np

DATA_DIR = "data"
SEQ_LEN = 15  # number of transactions per sequence (including the current one)


def build_sequences():
    df = pd.read_csv(f"{DATA_DIR}/processed_transactions.csv")
    df = df.sort_values(["user_id", "TransactionDT"]).reset_index(drop=True)

    drop_cols = ["TransactionID", "TransactionDT", "isFraud", "user_id"]
    feature_cols = [c for c in df.columns if c not in drop_cols]

    features = df[feature_cols].values.astype(np.float32)
    labels = df["isFraud"].values.astype(np.int64)
    transaction_ids = df["TransactionID"].values
    user_ids = df["user_id"].values

    n = len(df)
    window_indices = np.full((n, SEQ_LEN), -1, dtype=np.int64)
    mask = np.zeros((n, SEQ_LEN), dtype=np.float32)

    print(f"Building sequences for {n} transactions across {df['user_id'].nunique()} users...")

    # Since df is sorted by (user_id, TransactionDT), each user's rows are
    # contiguous — we can build windows with simple slicing per user group.
    start = 0
    user_vals = df["user_id"].values
    for end in range(1, n + 1):
        if end == n or user_vals[end] != user_vals[start]:
            # rows [start, end) belong to one user, already time-sorted
            group_len = end - start
            for i in range(group_len):
                global_idx = start + i
                win_start = max(0, i - SEQ_LEN + 1)
                win_len = i - win_start + 1
                # place the real indices right-aligned in the window (padding on the left)
                window_indices[global_idx, SEQ_LEN - win_len:] = np.arange(start + win_start, start + i + 1)
                mask[global_idx, SEQ_LEN - win_len:] = 1.0
            start = end
        if end % 100000 == 0:
            print(f"  processed {end}/{n} rows")

    np.save(f"{DATA_DIR}/features.npy", features)
    np.save(f"{DATA_DIR}/window_indices.npy", window_indices)
    np.save(f"{DATA_DIR}/mask.npy", mask)
    np.save(f"{DATA_DIR}/labels.npy", labels)
    np.save(f"{DATA_DIR}/transaction_ids.npy", transaction_ids)
    np.save(f"{DATA_DIR}/user_ids.npy", user_ids)

    print(f"\nSaved: features {features.shape}, window_indices {window_indices.shape}, "
          f"mask {mask.shape}, labels {labels.shape}")
    print(f"Avg real (non-pad) transactions per window: {mask.sum(axis=1).mean():.2f} / {SEQ_LEN}")


if __name__ == "__main__":
    build_sequences()