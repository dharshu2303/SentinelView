import json
from pathlib import Path

import pandas as pd

from src.rules_engine import RulesEngine


def load_customer_transactions(customer_id: str):
    root = Path(__file__).resolve().parents[1]
    tx = pd.read_csv(root / "data" / "transactions.csv")
    subset = tx[tx["customer_id"] == customer_id].copy()
    return subset.to_dict(orient="records")


def triggered_rule_ids(results):
    return {r["rule_id"] for r in results if r["triggered"]}


def test_clean_customers_have_no_flags():
    engine = RulesEngine()
    for customer_id in ["C001", "C002"]:
        findings = engine.analyze(customer_id, load_customer_transactions(customer_id))
        assert triggered_rule_ids(findings) == set()


def test_large_transfer_only_customer():
    engine = RulesEngine()
    findings = engine.analyze("C003", load_customer_transactions("C003"))
    assert triggered_rule_ids(findings) == {"R1"}


def test_new_payee_burst_only_customer():
    engine = RulesEngine()
    findings = engine.analyze("C004", load_customer_transactions("C004"))
    assert triggered_rule_ids(findings) == {"R2"}


def test_odd_hours_only_customer():
    engine = RulesEngine()
    findings = engine.analyze("C005", load_customer_transactions("C005"))
    assert triggered_rule_ids(findings) == {"R3"}


def test_pattern_break_only_customer():
    engine = RulesEngine()
    findings = engine.analyze("C006", load_customer_transactions("C006"))
    assert triggered_rule_ids(findings) == {"R4"}


def test_multi_rule_customer_has_overlapping_findings():
    engine = RulesEngine()
    findings = engine.analyze("C007", load_customer_transactions("C007"))
    assert triggered_rule_ids(findings) >= {"R1", "R2", "R4"}
