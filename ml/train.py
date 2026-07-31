"""
CAN Bus IDS — Model Training Script
--------------------------------------
Trains on YOUR real dataset (Benign + Masquerade CSV files).

Usage — train on the uploaded files directly:
    python ml/train.py --auto

Or on a specific file:
    python ml/train.py --data path/to/file.csv --label Label

Label normalisation handled automatically:
    0, "Benign", "Normal"             → Benign
    1, "Attack", "Masquerade", ...    → Masquerade  (if filename hints)
    "Real Attack", "Fuzzy", ...       → Real Attack
    "Suspension", "DoS", ...          → Suspension
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import glob
import argparse
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

from ml.features import extract_features

MODEL_DIR   = os.path.join("ml", "model")
MODEL_PATH  = os.path.join(MODEL_DIR, "canids_model.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "canids_scaler.joblib")
REPORT_PATH = os.path.join(MODEL_DIR, "canids_report.txt")
LABEL_PATH  = os.path.join(MODEL_DIR, "canids_labels.joblib")

os.makedirs(MODEL_DIR, exist_ok=True)

LABEL_ALIASES = ["label","class","attack_type","category","type","target","flag"]


def find_label_col(df: pd.DataFrame) -> str | None:
    lc = {c.lower(): c for c in df.columns}
    for a in LABEL_ALIASES:
        if a in lc: return lc[a]
    return None


def normalise_label(val, filename: str = "") -> str:
    """Map any raw label value to one of: Benign / Masquerade / Real Attack / Suspension."""
    v = str(val).strip().lower()
    # Numeric labels
    if v in ('0', '0.0'):    return "Benign"
    if v in ('1', '1.0'):
        # If filename says masquerade, treat 1 as masquerade; else generic attack
        if "masquerade" in filename.lower(): return "Masquerade"
        if "real" in filename.lower():       return "Real Attack"
        if "suspension" in filename.lower(): return "Suspension"
        return "Masquerade"   # default
    if v in ('2', '2.0'):    return "Real Attack"
    if v in ('3', '3.0'):    return "Suspension"
    # String labels
    if any(x in v for x in ['benign','normal','0','safe']):     return "Benign"
    if any(x in v for x in ['masquerade','spoof','impersonat']): return "Masquerade"
    if any(x in v for x in ['real','inject','fuzzy','rpm']):    return "Real Attack"
    if any(x in v for x in ['suspension','dos','gear','speed']): return "Suspension"
    if v == 'attack':
        # Context from filename
        fn = filename.lower()
        if "masquerade" in fn: return "Masquerade"
        if "real"       in fn: return "Real Attack"
        if "suspension" in fn: return "Suspension"
        return "Masquerade"
    return "Benign"


def load_uploads() -> pd.DataFrame:
    """Load all CSVs from static/uploads/ and combine them."""
    files = sorted(glob.glob(os.path.join("static","uploads","*.csv")))
    if not files:
        raise FileNotFoundError("No CSV files found in static/uploads/")
    dfs = []
    for f in files:
        print(f"  Loading: {os.path.basename(f)}")
        df = pd.read_csv(f, low_memory=False)
        label_col = find_label_col(df)
        if label_col is None:
            print(f"  [WARN] No label column found in {os.path.basename(f)}, skipping.")
            continue
        fname = os.path.basename(f)
        df["_label"] = df[label_col].apply(lambda x: normalise_label(x, fname))
        dfs.append(df)
        print(f"  Labels: {df['_label'].value_counts().to_dict()}")
    if not dfs:
        raise ValueError("No labelled CSV files found.")
    combined = pd.concat(dfs, ignore_index=True)
    return combined


def train(data_path: str = None, label_col_override: str = None, auto: bool = False):
    print("\n" + "="*50)
    print("  CAN Bus IDS — Model Training")
    print("="*50 + "\n")

    # 1. Load data
    if auto or data_path is None:
        print("[1/6] Loading all CSVs from static/uploads/...")
        df = load_uploads()
    else:
        print(f"[1/6] Loading: {data_path}")
        df = pd.read_csv(data_path, low_memory=False)
        fname = os.path.basename(data_path)
        label_col = label_col_override or find_label_col(df)
        if label_col is None:
            raise ValueError("No label column found. Pass --label <column_name>")
        df["_label"] = df[label_col].apply(lambda x: normalise_label(x, fname))

    print(f"\n[2/6] Dataset: {len(df):,} rows")
    print("Label distribution:")
    vc = df["_label"].value_counts()
    for k,v in vc.items():
        print(f"  {k:20s}: {v:,}  ({v/len(df)*100:.1f}%)")

    # 2. Sample for balance and speed (max 150k rows per class)
    MAX_PER_CLASS = 150_000
    parts = []
    for lbl in df["_label"].unique():
        part = df[df["_label"] == lbl]
        if len(part) > MAX_PER_CLASS:
            part = part.sample(MAX_PER_CLASS, random_state=42)
        parts.append(part)
    df_bal = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=42)
    print(f"\n[3/6] Balanced sample: {len(df_bal):,} rows")
    print("Balanced distribution:")
    for k,v in df_bal["_label"].value_counts().items():
        print(f"  {k:20s}: {v:,}")

    # 3. Extract features in chunks (memory-safe)
    print("\n[4/6] Extracting features...")
    CHUNK = 50_000
    feat_parts = []
    for start in range(0, len(df_bal), CHUNK):
        chunk = df_bal.iloc[start:start+CHUNK]
        feat_parts.append(extract_features(chunk.drop(columns=["_label"])))
        print(f"  processed {min(start+CHUNK, len(df_bal)):,}/{len(df_bal):,}", end="\r")
    X_df = pd.concat(feat_parts, ignore_index=True)
    y    = df_bal["_label"].values
    print(f"\n  Features: {X_df.shape[1]} columns")
    print(f"  Feature names: {list(X_df.columns)}")

    # 4. Scale
    print("\n[5/6] Training Random Forest (200 trees)...")
    scaler  = StandardScaler()
    X       = scaler.fit_transform(X_df.values)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_leaf=1,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # 5. Evaluate
    y_pred = model.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    labels_present = sorted(set(y))
    report = classification_report(y_test, y_pred, target_names=labels_present)

    print(f"\n  ✓ Test Accuracy : {acc*100:.2f}%")
    print("\n  Classification Report:")
    print(report)

    # Cross-validation (quick 3-fold)
    cv     = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)
    print(f"  3-Fold CV: {scores.mean()*100:.2f}% ± {scores.std()*100:.2f}%")

    # 6. Save
    print("\n[6/6] Saving model...")
    joblib.dump(model,          MODEL_PATH)
    joblib.dump(scaler,         SCALER_PATH)
    joblib.dump(labels_present, LABEL_PATH)
    print(f"  ✓ Model  → {MODEL_PATH}")
    print(f"  ✓ Scaler → {SCALER_PATH}")

    with open(REPORT_PATH, "w") as f:
        f.write(f"Test Accuracy: {acc*100:.2f}%\n")
        f.write(f"CV Accuracy  : {scores.mean()*100:.2f}% ± {scores.std()*100:.2f}%\n\n")
        f.write(report)
    print(f"  ✓ Report → {REPORT_PATH}")
    print("\n  Training complete!\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data",  default=None, help="Path to CSV file")
    p.add_argument("--label", default=None, help="Label column name")
    p.add_argument("--auto",  action="store_true",
                   help="Auto-load all CSVs from static/uploads/")
    args = p.parse_args()
    train(data_path=args.data, label_col_override=args.label, auto=args.auto)
