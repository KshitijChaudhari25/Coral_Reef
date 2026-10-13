"""Manual smoke test against the running API: python backend/test_predict.py."""
import json
import urllib.request
from test_api import BASELINE

if __name__ == '__main__':
    request = urllib.request.Request(
        'http://127.0.0.1:8000/predict', data=json.dumps(BASELINE).encode(),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.load(response)
    print(json.dumps({key: result[key] for key in ('risk_label', 'confidence', 'probabilities')}, indent=2, ensure_ascii=False))
