from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def load_customer_data() -> Dict[str, Dict]:
    customers_path = DATA_DIR / "customers.json"
    tx_path = DATA_DIR / "transactions.csv"

    customers = json.loads(customers_path.read_text(encoding="utf-8"))
    tx_df = pd.read_csv(tx_path)

    grouped: Dict[str, List[Dict]] = {
        cid: grp.sort_values("date").to_dict(orient="records")
        for cid, grp in tx_df.groupby("customer_id")
    }

    out: Dict[str, Dict] = {}
    for c in customers:
        txs = grouped.get(c["id"], [])
        record = dict(c)
        record["transaction_count"] = len(txs)
        record["transactions"] = txs
        out[c["id"]] = record

    return out
