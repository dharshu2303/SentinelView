from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Dict, List, Tuple

import pandas as pd

BASE_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _is_writable_dir(directory: Path) -> bool:
    if not directory.exists():
        return False
    try:
        test_file = directory / ".write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return True
    except (OSError, PermissionError):
        return False


def get_runtime_data_dir() -> Path:
    """
    Return the active runtime data directory.
    If the base directory is read-only (such as on Vercel / AWS Lambda /var/task),
    initializes and returns a writable copy in /tmp/sentinelview_data.
    """
    if _is_writable_dir(BASE_DATA_DIR):
        return BASE_DATA_DIR

    tmp_dir = Path(tempfile.gettempdir()) / "sentinelview_data"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tx_dest = tmp_dir / "transactions.csv"
    cust_dest = tmp_dir / "customers.json"

    tx_src = BASE_DATA_DIR / "transactions.csv"
    cust_src = BASE_DATA_DIR / "customers.json"

    if not tx_dest.exists() and tx_src.exists():
        shutil.copy2(tx_src, tx_dest)
    if not cust_dest.exists() and cust_src.exists():
        shutil.copy2(cust_src, cust_dest)

    return tmp_dir


def get_runtime_data_paths() -> Tuple[Path, Path]:
    """Return (customers_path, transactions_path) pointing to writable runtime storage."""
    active_dir = get_runtime_data_dir()
    return active_dir / "customers.json", active_dir / "transactions.csv"


# Backward compatibility
DATA_DIR = BASE_DATA_DIR


def load_customer_data() -> Dict[str, Dict]:
    customers_path, tx_path = get_runtime_data_paths()

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

