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
    for customer_id in ["CUST002", "CUST004", "CUST005"]:
        txs = load_customer_transactions(customer_id)
        assert len(txs) > 0
        findings = engine.analyze(customer_id, txs)
        assert triggered_rule_ids(findings) == set(), f"Expected no flags for {customer_id}"


def test_multi_rule_customer_priya_sharma():
    engine = RulesEngine()
    txs = load_customer_transactions("CUST001")
    findings = engine.analyze("CUST001", txs)
    triggered = triggered_rule_ids(findings)
    assert "R1" in triggered
    assert "R2" in triggered
    assert "R3" in triggered


def test_new_payee_burst_only_customer():
    engine = RulesEngine()
    findings = engine.analyze("CUST003", load_customer_transactions("CUST003"))
    assert triggered_rule_ids(findings) == {"R2"}


def test_odd_hours_only_customer():
    engine = RulesEngine()
    findings = engine.analyze("CUST007", load_customer_transactions("CUST007"))
    assert triggered_rule_ids(findings) == {"R3"}


def test_pattern_break_only_customer():
    engine = RulesEngine()
    findings = engine.analyze("CUST006", load_customer_transactions("CUST006"))
    assert triggered_rule_ids(findings) == {"R4"}


def test_traceability_of_flagged_transactions():
    engine = RulesEngine()
    txs = load_customer_transactions("CUST001")
    all_ids = {t["transaction_id"] for t in txs}
    findings = engine.analyze("CUST001", txs)
    for f in findings:
        for tid in f["matched_transaction_ids"]:
            assert tid in all_ids, f"Flagged transaction {tid} not found in customer history!"
