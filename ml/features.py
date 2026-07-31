"""
Feature Engineering for CAN Bus IDS
--------------------------------------
Real dataset format:
    Timestamp  CAN_ID  Byte1  Byte2  Byte3  Byte4  Byte5  Byte6  Byte7  Byte8  [Label]

All heavy loops are O(n log n) via np.searchsorted.
"""

import numpy as np
import pandas as pd
from collections import defaultdict

BYTE_COLS = ['Byte1','Byte2','Byte3','Byte4','Byte5','Byte6','Byte7','Byte8']
LABEL_ALIASES = ["label","class","attack_type","category","type","target","flag"]


# ── Column finders ────────────────────────────────────────────────────────
def _find(df, aliases):
    lc = {c.lower(): c for c in df.columns}
    for a in aliases:
        if a in lc: return lc[a]
    return None

def find_label_col(df):
    return _find(df, LABEL_ALIASES)

def normalise_label(val, filename=""):
    v = str(val).strip().lower()
    if v in ('0','0.0'):     return "Benign"
    if v in ('1','1.0'):
        fn = filename.lower()
        if "masquerade" in fn: return "Masquerade"
        if "real"       in fn: return "Real Attack"
        if "suspension" in fn: return "Suspension"
        return "Masquerade"
    if v in ('2','2.0'):     return "Real Attack"
    if v in ('3','3.0'):     return "Suspension"
    if any(x in v for x in ['benign','normal','safe']):        return "Benign"
    if any(x in v for x in ['masquerade','spoof','imperson']): return "Masquerade"
    if any(x in v for x in ['real','inject','fuzzy','rpm']):   return "Real Attack"
    if any(x in v for x in ['suspension','dos','gear']):       return "Suspension"
    if v == 'attack':
        fn = filename.lower()
        if "masquerade" in fn: return "Masquerade"
        if "real"       in fn: return "Real Attack"
        if "suspension" in fn: return "Suspension"
        return "Masquerade"
    return "Benign"


# ── Main feature extractor ────────────────────────────────────────────────
def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    df  = df.copy().reset_index(drop=True)
    n   = len(df)

    ts_col = _find(df, ['timestamp','time','ts','time_s'])
    id_col = _find(df, ['can_id','id','canid','arbitration_id','frame_id'])
    lc     = {c.lower(): c for c in df.columns}
    byte_cols = [lc[b] for b in ['byte1','byte2','byte3','byte4',
                                  'byte5','byte6','byte7','byte8'] if b in lc]
    has_bytes = len(byte_cols) == 8

    # Timestamps
    if ts_col:
        ts = pd.to_numeric(df[ts_col], errors='coerce').ffill().fillna(0).values.astype(float)
    else:
        ts = np.arange(n, dtype=float) * 0.001

    # CAN IDs
    if id_col:
        ids = pd.to_numeric(df[id_col], errors='coerce').fillna(0).astype(int).values
    else:
        ids = np.zeros(n, dtype=int)

    # Byte matrix
    if has_bytes:
        bmat = df[byte_cols].apply(pd.to_numeric, errors='coerce').fillna(0).values.astype(float)
    else:
        bmat = np.zeros((n, 8), dtype=float)

    # ── Temporal features ─────────────────────────────────────────────
    global_iat     = np.empty(n); global_iat[0] = 0
    global_iat[1:] = np.clip(np.diff(ts), 0, 10)

    per_id_iat = _per_id_iat(ids, ts)
    id_freq    = _id_freq(ids, ts, half_win=0.5)
    global_rate= _global_rate(ts, half_win=0.5)

    # ── Structural features ───────────────────────────────────────────
    consec     = _consecutive_same_id(ids)
    id_ent     = _rolling_entropy(ids, win=20)

    # ── Byte features ─────────────────────────────────────────────────
    byte_mean  = bmat.mean(1)
    byte_std   = bmat.std(1)
    byte_min   = bmat.min(1)
    byte_max   = bmat.max(1)
    byte_range = byte_max - byte_min
    byte_sum   = bmat.sum(1)
    unique_b   = np.array([len(np.unique(r)) for r in bmat], dtype=float)
    zero_ratio = (bmat == 0).mean(1)
    ff_ratio   = (bmat == 255).mean(1)
    odd_id     = (ids > 0x7FF).astype(float)

    return pd.DataFrame({
        'can_id':             ids.astype(float),
        'inter_arrival_time': per_id_iat,
        'global_iat':         global_iat,
        'id_freq_1s':         id_freq,
        'global_rate':        global_rate,
        'byte_mean':          byte_mean,
        'byte_std':           byte_std,
        'byte_min':           byte_min,
        'byte_max':           byte_max,
        'byte_range':         byte_range,
        'unique_bytes':       unique_b,
        'zero_ratio':         zero_ratio,
        'ff_ratio':           ff_ratio,
        'consecutive_same_id':consec.astype(float),
        'id_entropy':         id_ent,
        'byte_sum':           byte_sum,
        'odd_id':             odd_id,
    }).fillna(0)


# ── Fast helpers (all O(n log n)) ─────────────────────────────────────────

def _per_id_iat(ids, ts):
    """Per-ID inter-arrival time."""
    iat = np.zeros(len(ids))
    last = {}
    for i, (cid, t) in enumerate(zip(ids, ts)):
        if cid in last:
            iat[i] = min(t - last[cid], 10.0)
        last[cid] = t
    return iat


def _id_freq(ids, ts, half_win=0.5):
    """Per-ID message count in ±half_win window. O(n log n)."""
    freq   = np.zeros(len(ids))
    groups = defaultdict(list)
    for i, cid in enumerate(ids):
        groups[cid].append(i)
    for cid, idxs in groups.items():
        arr     = np.asarray(idxs)
        t_arr   = ts[arr]
        t_sort  = np.sort(t_arr)
        lo = np.searchsorted(t_sort, t_arr - half_win, side='left')
        hi = np.searchsorted(t_sort, t_arr + half_win, side='right')
        freq[arr] = hi - lo
    return freq


def _global_rate(ts, half_win=0.5):
    """Total messages in ±half_win window. O(n log n)."""
    t_sort = np.sort(ts)
    lo = np.searchsorted(t_sort, ts - half_win, side='left')
    hi = np.searchsorted(t_sort, ts + half_win, side='right')
    return (hi - lo).astype(float)


def _consecutive_same_id(ids):
    """Count of consecutive identical CAN IDs."""
    consec = np.ones(len(ids), dtype=int)
    for i in range(1, len(ids)):
        consec[i] = consec[i-1] + 1 if ids[i] == ids[i-1] else 1
    return consec


def _rolling_entropy(ids, win=20):
    """Rolling Shannon entropy of CAN IDs in window of size win."""
    ent = np.zeros(len(ids))
    for i in range(len(ids)):
        s = max(0, i - win + 1)
        window = ids[s:i+1]
        _, cnts = np.unique(window, return_counts=True)
        p = cnts / cnts.sum()
        ent[i] = float(-np.sum(p * np.log2(p + 1e-12))) if len(p) > 1 else 0.0
    return ent
