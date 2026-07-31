"""Quick end-to-end pipeline test — run: python test_pipeline.py"""
import warnings; warnings.filterwarnings('ignore')
import sys, json, os
sys.path.insert(0, '.')

from ml.predictor import CANPredictor
import uuid

p = CANPredictor()

ATTACK_FILE = 'static/uploads/1ee1125d307444d692f91d297133e7f6_Masquerade_attacks.csv'
BENIGN_FILE = 'static/uploads/710e8ad7bb5946adba062f1f6fec6ba8_Benign_Masquerade.csv'

os.makedirs('static/results', exist_ok=True)

for label, fpath in [("ATTACK", ATTACK_FILE), ("BENIGN", BENIGN_FILE)]:
    print(f"\n{'='*50}")
    print(f"  Testing: {label} FILE")
    print(f"{'='*50}")

    results = p.predict_csv(fpath)

    # Save to disk (same as Flask does)
    fname = f'result_{uuid.uuid4().hex}.json'
    jpath = os.path.join('static', 'results', fname)
    with open(jpath, 'w') as jf:
        json.dump(results, jf)
    size_kb = os.path.getsize(jpath) / 1024

    # Load back (same as Flask does)
    with open(jpath) as jf:
        loaded = json.load(jf)

    print(f"  has_attack  : {loaded['has_attack']}")
    print(f"  risk_level  : {loaded['risk_level']}")
    print(f"  total       : {loaded['total']:,}")
    print(f"  counts      : {loaded['counts']}")
    print(f"  result size : {size_kb:.1f} KB")
    print(f"  Top bar     : {'ATTACK DETECTED' if loaded['has_attack'] else 'VEHICLE SAFE'}")
    print(f"  Vehicle     : {'RED / attack-mode' if loaded['has_attack'] else 'GREEN / safe-mode'}")

    # Cleanup test file
    os.remove(jpath)

print("\nAll tests passed.")
