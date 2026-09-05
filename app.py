from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import logging

from flask import Flask, jsonify, request, send_from_directory

from src.data_loader import load_customer_data
from src.gemini_narrator import GeminiNarrator, deterministic_fallback
from src.rules_engine import RulesEngine


def load_dotenv_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


load_dotenv_file(Path(__file__).resolve().parent / ".env")

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
logger = logging.getLogger(__name__)

rules_engine = RulesEngine()
customers_db = load_customer_data()
gemini_narrator = GeminiNarrator(api_key=os.getenv("GEMINI_API_KEY"), timeout=45)


@app.get("/")
def root():
    index = Path(app.static_folder) / "index.html"
    if index.exists():
        return send_from_directory(app.static_folder, "index.html")
    return "SentinelView API is running", 200


@app.get("/api/customers")
def list_customers():
    payload = []
    for customer_id, customer in customers_db.items():
        findings = rules_engine.analyze(customer_id, customer.get("transactions", []))
        triggered = [f for f in findings if f["triggered"]]
        payload.append(
            {
                "id": customer_id,
                "name": customer["name"],
                "transaction_count": customer["transaction_count"],
                "date_range": {"start": customer["date_start"], "end": customer["date_end"]},
                "risk_level": "clean" if not triggered else ("high" if len(triggered) >= 2 else "medium"),
                "triggered_rule_ids": [f["rule_id"] for f in triggered],
            }
        )
    return jsonify(sorted(payload, key=lambda x: x["id"]))


@app.get("/api/customers/<customer_id>/transactions")
def get_customer_transactions(customer_id: str):
    customer = customers_db.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found", "customer_id": customer_id}), 404
    return jsonify(
        {
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "transactions": customer.get("transactions", []),
        }
    )


@app.post("/api/customers/<customer_id>/investigate")
def investigate(customer_id: str):
    customer = customers_db.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found", "customer_id": customer_id}), 404

    transactions = customer.get("transactions", [])
    if not isinstance(transactions, list):
        return jsonify(
            {
                "customer_id": customer_id,
                "customer_name": customer.get("name", "unknown"),
                "status": "error",
                "error": "Malformed customer data: transactions must be a list",
                "narrative_available": False,
                "fallback_mode": True,
            }
        ), 200

    if not transactions:
        return jsonify(
            {
                "customer_id": customer_id,
                "customer_name": customer["name"],
                "status": "no_data",
                "first_finding": "No attention needed: customer has no transaction history to review.",
                "rule_engine_verdict": "NO_DATA",
                "deterministic_findings": [],
                "narrative": {
                    "summary": "No transactions were available.",
                    "claims": [],
                    "context_transaction_ids": [],
                },
                "narrative_available": False,
                "fallback_mode": True,
            }
        )

    try:
        findings = rules_engine.analyze(customer_id, transactions)
    except Exception as exc:
        logger.exception("Rule engine data error for customer %s", customer_id)
        return jsonify(
            {
                "customer_id": customer_id,
                "customer_name": customer.get("name", "unknown"),
                "status": "error",
                "first_finding": "Needs attention: transaction data quality issue prevented scoring.",
                "rule_engine_verdict": "DATA_ERROR",
                "deterministic_findings": [],
                "triggered_findings": [],
                "narrative": {
                    "summary": "Investigation could not run because customer transaction data is malformed.",
                    "claims": [],
                    "context_transaction_ids": [],
                },
                "narrative_available": False,
                "fallback_mode": True,
                "error": "Malformed transaction data; unable to score rules.",
            }
        ), 200
    triggered_findings = [f for f in findings if f["triggered"]]

    if not triggered_findings:
        return jsonify(
            {
                "customer_id": customer_id,
                "customer_name": customer["name"],
                "status": "clean",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rule_engine_verdict": "CLEAN",
                "deterministic_findings": findings,
                "triggered_findings": [],
                "first_finding": "No attention needed: no risk rules were triggered.",
                "narrative": {
                    "summary": "All reviewed activity stays within this customer’s established behavior.",
                    "claims": [],
                    "context_transaction_ids": [],
                },
                "narrative_available": True,
                "fallback_mode": False,
            }
        )

    flagged_ids = sorted({tx_id for f in triggered_findings for tx_id in f["matched_transaction_ids"]})
    flagged_transactions = [tx for tx in transactions if tx.get("transaction_id") in flagged_ids]

    narrative = None
    gemini_error = None
    req_body = request.get_json(silent=True) or {}
    try:
        if req_body.get("simulate_gemini_failure"):
            raise RuntimeError("Simulated Gemini failure for demo")
        narrative = gemini_narrator.generate_narrative(
            customer_id=customer_id,
            customer_name=customer["name"],
            findings=triggered_findings,
            flagged_transactions=flagged_transactions,
            all_transactions=transactions,
        )
    except Exception as exc:
        logger.exception("Gemini narrative failure for customer %s", customer_id)
        gemini_error = "Gemini narrative unavailable"
        narrative = deterministic_fallback(triggered_findings, flagged_transactions)

    return jsonify(
        {
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "status": "flagged",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_engine_verdict": "FLAGGED",
            "deterministic_findings": findings,
            "triggered_findings": triggered_findings,
            "flagged_transaction_ids": flagged_ids,
            "flagged_transactions": flagged_transactions,
            "first_finding": narrative["first_finding"],
            "narrative": narrative,
            "narrative_available": gemini_error is None,
            "fallback_mode": gemini_error is not None,
            "gemini_error": gemini_error,
        }
    )


@app.get("/<path:path>")
def static_proxy(path: str):
    static_dir = Path(app.static_folder)
    target = static_dir / path
    if target.exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html") if (static_dir / "index.html").exists() else ("Not found", 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
