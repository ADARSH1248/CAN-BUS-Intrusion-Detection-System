"""
CAN Bus IDS — Predictor
--------------------------
Reproduces the EXACT feature engineering from Combined_CanBus.ipynb:

Input CSV columns: Timestamp, CAN_ID, Byte1, Byte2, Byte3, Byte4,
                   Byte5, Byte6, Byte7, Byte8  [, Label (ignored)]

Engineered features added (matching the notebook):
    PayloadSum    = sum(Byte1..8)
    PayloadMean   = mean(Byte1..8)
    PayloadStd    = std(Byte1..8)
    PayloadMax    = max(Byte1..8)
    PayloadMin    = min(Byte1..8)
    PayloadRange  = PayloadMax - PayloadMin
    ZeroBytes     = count of bytes == 0
    NonZeroBytes  = count of bytes != 0
    TimeDiff      = Timestamp.diff().fillna(0)

Final feature matrix X (19 columns, same order as notebook):
    Timestamp, CAN_ID, Byte1..8,
    PayloadSum, PayloadMean, PayloadStd, PayloadMax, PayloadMin,
    PayloadRange, ZeroBytes, NonZeroBytes, TimeDiff

Label map  (integers from the notebook):
    0 → Benign
    1 → Real Attack
    2 → Masquerade
    3 → Suspension
"""

import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────
MODEL_DIR   = os.path.join("ml", "model")
MODEL_PATH  = os.path.join(MODEL_DIR, "canids_model.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "canids_scaler.joblib")   # optional

# ── Label / Risk maps ─────────────────────────────────────────────────────
LABEL_MAP = {
    0: "Benign",
    1: "Real Attack",
    2: "Masquerade",
    3: "Suspension",
}
RISK_MAP = {
    "Benign":      "Low",
    "Masquerade":  "Medium",
    "Real Attack": "Critical",
    "Suspension":  "High",
}
STATUS_MAP = {
    "Benign":      "Normal",
    "Masquerade":  "Suspicious",
    "Real Attack": "Attack",
    "Suspension":  "Attack",
}

BYTE_COLS = ["Byte1", "Byte2", "Byte3", "Byte4",
             "Byte5", "Byte6", "Byte7", "Byte8"]

# Exact feature order the model was trained on
FEATURE_COLS = [
    "Timestamp", "CAN_ID",
    "Byte1", "Byte2", "Byte3", "Byte4",
    "Byte5", "Byte6", "Byte7", "Byte8",
    "PayloadSum", "PayloadMean", "PayloadStd",
    "PayloadMax", "PayloadMin", "PayloadRange",
    "ZeroBytes", "NonZeroBytes", "TimeDiff",
]


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reproduce the feature engineering from the notebook verbatim.
    Works on a copy; original df is unchanged.
    """
    d = df.copy()

    # Ensure byte columns are numeric
    for col in BYTE_COLS:
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors="coerce").fillna(0)

    payload = d[BYTE_COLS] if all(c in d.columns for c in BYTE_COLS) \
              else pd.DataFrame(np.zeros((len(d), 8)), columns=BYTE_COLS)

    d["PayloadSum"]   = payload.sum(axis=1)
    d["PayloadMean"]  = payload.mean(axis=1)
    d["PayloadStd"]   = payload.std(axis=1)
    d["PayloadMax"]   = payload.max(axis=1)
    d["PayloadMin"]   = payload.min(axis=1)
    d["PayloadRange"] = d["PayloadMax"] - d["PayloadMin"]
    d["ZeroBytes"]    = (payload == 0).sum(axis=1)
    d["NonZeroBytes"] = (payload != 0).sum(axis=1)
    d["TimeDiff"]     = pd.to_numeric(d.get("Timestamp", 0), errors="coerce") \
                          .diff().fillna(0)

    # Keep only the training feature columns that exist
    available = [c for c in FEATURE_COLS if c in d.columns]
    return d[available].fillna(0)


class CANPredictor:
    def __init__(self):
        self.model  = None
        self.scaler = None
        self._load()

    def _load(self):
        if os.path.exists(MODEL_PATH):
            self.model = joblib.load(MODEL_PATH)
            print(f"[IDS] ✓ Model loaded → {MODEL_PATH}")
            if os.path.exists(SCALER_PATH):
                self.scaler = joblib.load(SCALER_PATH)
                print(f"[IDS] ✓ Scaler loaded → {SCALER_PATH}")
        else:
            print(f"[IDS] ⚠  No model at {MODEL_PATH}")
            print("[IDS]    Copy your trained model there, or run: python ml/train.py --auto")

    def reload(self):
        self._load()

    # ─────────────────────────────────────────────────────────────────
    def predict_csv(self, filepath: str) -> dict:
        df = pd.read_csv(filepath, low_memory=False)

        # Drop the label column if present — we're doing inference
        for col in ["Label", "label", "class", "target"]:
            if col in df.columns:
                df = df.drop(columns=[col])

        # Cap rows for web performance
        if len(df) > 50_000:
            df = df.sample(50_000, random_state=42).reset_index(drop=True)
        else:
            df = df.reset_index(drop=True)

        features = _engineer_features(df)

        if self.model:
            raw_preds = self.model.predict(features.values
                                           if self.scaler is None
                                           else self.scaler.transform(features.values))
            # Map integer labels → string names
            labels = np.array([
                LABEL_MAP.get(int(p), str(p)) for p in raw_preds
            ])
        else:
            labels = self._heuristic(df, features)

        return self._build_results(df, labels)

    # ─────────────────────────────────────────────────────────────────
    def _heuristic(self, df, features):
        """Fallback when no model file exists."""
        n = len(features)
        labels = np.array(["Benign"] * n)
        td  = features["TimeDiff"].values   if "TimeDiff"   in features.columns else np.zeros(n)
        ps  = features["PayloadSum"].values  if "PayloadSum"  in features.columns else np.zeros(n)
        zb  = features["ZeroBytes"].values   if "ZeroBytes"   in features.columns else np.zeros(n)
        for i in range(n):
            if td[i] < 0.001 and zb[i] >= 6:
                labels[i] = "Suspension"
            elif td[i] < 0.002 and ps[i] > 1200:
                labels[i] = "Real Attack"
            elif td[i] < 0.003:
                labels[i] = "Masquerade"
        return labels

    # ─────────────────────────────────────────────────────────────────
    def _build_results(self, df, labels):
        total       = len(labels)
        all_classes = ["Benign", "Real Attack", "Masquerade", "Suspension"]
        counts      = {k: int(np.sum(labels == k)) for k in all_classes}
        has_attack  = any(labels != "Benign")

        id_col = next((c for c in df.columns
                       if c.lower() in ["can_id", "id", "canid"]), None)
        ts_col = next((c for c in df.columns
                       if c.lower() in ["timestamp", "time", "ts"]), None)

        # Up to 500 rows for the table, sorted by original index
        sample_size = min(500, total)
        idxs = np.sort(np.random.choice(total, sample_size, replace=False))

        rows = []
        for i in idxs:
            pred   = labels[i]
            ts_val = float(df.iloc[i][ts_col]) if ts_col else i * 0.001
            id_val = int(df.iloc[i][id_col])   if id_col else 0
            rows.append({
                "index":      int(i + 1),
                "timestamp":  f"{ts_val:.3f}",
                "can_id":     f"0x{id_val:03X}",
                "prediction": pred,
                "risk":       RISK_MAP.get(pred, "Low"),
                "status":     STATUS_MAP.get(pred, "Normal"),
            })

        # Timeline chart — 20 buckets
        n_buckets   = 20
        bucket_size = max(1, total // n_buckets)
        tl_labels   = [str(i * bucket_size) for i in range(n_buckets)]

        def series(target):
            return [
                int(np.sum(labels[i * bucket_size:(i + 1) * bucket_size] == target))
                for i in range(n_buckets)
            ]

        return {
            "total":        total,
            "counts":       counts,
            "has_attack":   has_attack,
            "risk_level":   "HIGH" if has_attack else "LOW",
            "rows":         rows,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "chart": {
                "pie":  [counts[k] for k in all_classes],
                "bar":  [counts[k] for k in all_classes],
                "area": {
                    "labels":      tl_labels,
                    "benign":      series("Benign"),
                    "masquerade":  series("Masquerade"),
                    "real_attack": series("Real Attack"),
                    "suspension":  series("Suspension"),
                },
            },
        }
