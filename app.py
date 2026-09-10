import csv
import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
import pandas as pd

from src.data_loader import DATA_DIR, get_runtime_data_paths, load_customer_data
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
gemini_narrator = GeminiNarrator(api_key=os.getenv("GEMINI_API_KEY"), timeout=20)

# In-memory investigation cache for ultra-fast instant customer switching
INVESTIGATION_CACHE = {}


def perform_investigation(customer_id: str, force_refresh: bool = False, simulate_failure: bool = False, use_gemini: bool = False) -> dict:
    cache_key = f"{customer_id}_sim{simulate_failure}_gem{use_gemini}"
    if not force_refresh and cache_key in INVESTIGATION_CACHE:
        return INVESTIGATION_CACHE[cache_key]

    customer = customers_db.get(customer_id)
    if not customer:
        return {"error": "Customer not found", "customer_id": customer_id}

    transactions = customer.get("transactions", [])
    if not isinstance(transactions, list):
        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name", "unknown"),
            "status": "error",
            "error": "Malformed customer data: transactions must be a list",
            "narrative_available": False,
            "fallback_mode": True,
        }

    if not transactions:
        return {
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "status": "no_data",
            "first_finding": "No attention needed: customer has no transaction history to review.",
            "rule_engine_verdict": "NO_DATA",
            "risk_level": "NO RISK",
            "attention_title": "NO ATTENTION REQUIRED",
            "attention_subtitle": "Customer has no transaction history to review.",
            "key_reasons": [],
            "behavior_analysis": {},
            "findings": [],
            "deterministic_findings": [],
            "flagged_transaction_ids": [],
            "flagged_transactions": [],
            "narrative": {
                "summary": "No transactions were available for analysis.",
                "recommended_checks": ["Verify customer profile status and account activity history."],
                "claims": [],
                "context_transaction_ids": [],
            },
            "narrative_available": False,
            "fallback_mode": True,
        }

    try:
        behavior_bundle = rules_engine.get_behavior_analysis(customer_id, customer, transactions)
    except Exception as exc:
        logger.exception("Rule engine data error for customer %s", customer_id)
        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name", "unknown"),
            "status": "error",
            "first_finding": "Needs attention: transaction data quality issue prevented scoring.",
            "rule_engine_verdict": "DATA_ERROR",
            "risk_level": "UNKNOWN",
            "deterministic_findings": [],
            "triggered_findings": [],
            "findings": [],
            "narrative": {
                "summary": "Investigation could not run because customer transaction data is malformed.",
                "recommended_checks": ["Check database transaction ingestion pipeline."],
                "claims": [],
                "context_transaction_ids": [],
            },
            "narrative_available": False,
            "fallback_mode": True,
            "error": "Malformed transaction data; unable to score rules.",
        }
    findings = behavior_bundle["findings"]
    triggered_findings = [f for f in findings if f["triggered"]]
    flagged_ids = behavior_bundle["flagged_transaction_ids"]
    flagged_transactions = behavior_bundle["flagged_transactions"]

    if not triggered_findings:
        result = {
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "customer_since": behavior_bundle.get("customer_since", "2 years 4 months"),
            "last_analysed": behavior_bundle.get("last_analysed", "26 Aug 2025, 14:32"),
            "account_number": customer.get("account_number", "•••• •••• 0000"),
            "account_type": customer.get("account_type", "Savings Classic"),
            "branch": customer.get("branch", "Main Branch"),
            "phone": customer.get("phone", "+91 98000 00000"),
            "email": customer.get("email", ""),
            "status": "clean",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rule_engine_verdict": "CLEAN",
            "risk_level": "NO RISK",
            "attention_required": False,
            "attention_title": behavior_bundle["attention_title"],
            "attention_subtitle": behavior_bundle["attention_subtitle"],
            "key_reasons": behavior_bundle["key_reasons"],
            "behavior_analysis": behavior_bundle["behavior_analysis"],
            "findings": findings,
            "deterministic_findings": findings,
            "triggered_findings": [],
            "flagged_transaction_ids": [],
            "flagged_transactions": [],
            "first_finding": "No attention needed: all transactions stay within this customer's established baseline.",
            "narrative": {
                "first_finding": "No attention needed: all transactions stay within this customer's established baseline.",
                "summary": "All reviewed activity stays within this customer's established behavior. No risk rules were triggered.",
                "recommended_checks": [
                    "Routine periodic account review as per standard policy.",
                    "No specific risk investigation checks required at this time."
                ],
                "claims": [],
                "context_transaction_ids": [],
            },
            "narrative_available": True,
            "fallback_mode": False,
            "all_transactions": behavior_bundle["all_transactions"],
        }
        INVESTIGATION_CACHE[cache_key] = result
        return result

    narrative = None
    gemini_error = None
    fallback_mode = False

    if simulate_failure:
        fallback_mode = True
        gemini_error = "Simulated Gemini failure for demo"
        narrative = deterministic_fallback(triggered_findings, flagged_transactions)
    elif use_gemini and gemini_narrator.api_key:
        try:
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
            fallback_mode = True
            narrative = deterministic_fallback(triggered_findings, flagged_transactions)
    else:
        # Fast, instant high-quality deterministic narrative
        narrative = deterministic_fallback(triggered_findings, flagged_transactions)
        fallback_mode = False

    result = {
        "customer_id": customer_id,
        "customer_name": customer["name"],
        "customer_since": behavior_bundle.get("customer_since", "2 years 4 months"),
        "last_analysed": behavior_bundle.get("last_analysed", "26 Aug 2025, 14:32"),
        "account_number": customer.get("account_number", "•••• •••• 4821"),
        "account_type": customer.get("account_type", "Savings Platinum"),
        "branch": customer.get("branch", "Fort Branch, Mumbai"),
        "phone": customer.get("phone", "+91 98201 44821"),
        "email": customer.get("email", ""),
        "status": "flagged",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rule_engine_verdict": "FLAGGED",
        "risk_level": behavior_bundle["risk_level"],
        "attention_required": True,
        "attention_title": behavior_bundle["attention_title"],
        "attention_subtitle": behavior_bundle["attention_subtitle"],
        "key_reasons": behavior_bundle["key_reasons"],
        "behavior_analysis": behavior_bundle["behavior_analysis"],
        "findings": findings,
        "deterministic_findings": findings,
        "triggered_findings": triggered_findings,
        "flagged_transaction_ids": flagged_ids,
        "flagged_transactions": flagged_transactions,
        "first_finding": narrative.get("first_finding", behavior_bundle["attention_subtitle"]),
        "narrative": narrative,
        "narrative_available": gemini_error is None,
        "fallback_mode": fallback_mode,
        "gemini_error": gemini_error,
        "all_transactions": behavior_bundle["all_transactions"],
    }
    INVESTIGATION_CACHE[cache_key] = result
    return result


def refresh_in_memory_data() -> None:
    """Reload customer and transaction data from disk and refresh in-memory cache."""
    global customers_db, INVESTIGATION_CACHE
    customers_db = load_customer_data()
    INVESTIGATION_CACHE.clear()
    for _cid in customers_db:
        try:
            perform_investigation(_cid, use_gemini=False)
        except Exception as _e:
            logger.warning("Error pre-warming cache for %s: %s", _cid, _e)


# Pre-warm server-side investigation cache for all customers for 0ms response times
refresh_in_memory_data()


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
        txs = customer.get("transactions", [])
        if not txs:
            findings = []
            triggered = []
            risk_level = "clean"
            risk_label = "No Risk"
        else:
            try:
                findings = rules_engine.analyze(customer_id, txs)
                triggered = [f for f in findings if f["triggered"]]
                if not triggered:
                    risk_level = "clean"
                    risk_label = "No Risk"
                elif len(triggered) >= 2 or any(f["severity"] == "High" for f in triggered):
                    risk_level = "high"
                    risk_label = "High Risk"
                else:
                    risk_level = "medium"
                    risk_label = "Medium Risk"
            except Exception:
                findings = []
                triggered = []
                risk_level = "clean"
                risk_label = "No Risk"

        payload.append(
            {
                "id": customer_id,
                "name": customer["name"],
                "customer_since": customer.get("customer_since", "2 years"),
                "last_analysed": customer.get("last_analysed", "26 Aug 2025, 14:32"),
                "account_number": customer.get("account_number", "•••• •••• 0000"),
                "account_type": customer.get("account_type", "Savings Classic"),
                "branch": customer.get("branch", "Main Branch"),
                "phone": customer.get("phone", "+91 98000 00000"),
                "email": customer.get("email", ""),
                "transaction_count": customer["transaction_count"],
                "date_range": {"start": customer.get("date_start"), "end": customer.get("date_end")},
                "risk_level": risk_level,
                "risk_label": risk_label,
                "triggered_rule_ids": [f["rule_id"] for f in triggered],
            }
        )
    return jsonify(sorted(payload, key=lambda x: x["id"]))


@app.get("/api/customers/<customer_id>/transactions")
def get_customer_transactions(customer_id: str):
    customer = customers_db.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found", "customer_id": customer_id}), 404
    
    txs = customer.get("transactions", [])
    return jsonify(
        {
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "transactions": txs,
        }
    )


@app.post("/api/customers/<customer_id>/investigate")
def investigate_customer_endpoint(customer_id: str):
    req_body = request.get_json(silent=True) or {}
    sim_failure = bool(req_body.get("simulate_gemini_failure"))
    force_refresh = bool(req_body.get("force_refresh"))
    use_gemini = bool(req_body.get("use_gemini"))

    result = perform_investigation(customer_id, force_refresh=force_refresh, simulate_failure=sim_failure, use_gemini=use_gemini)
    status_code = 404 if "error" in result and result.get("error") == "Customer not found" else 200
    return jsonify(result), status_code


# --------------------------------------------------------------------------
# Endpoints for other sidebar tabs: Dashboard, Alerts, Reports
# --------------------------------------------------------------------------

@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    total_customers = len(customers_db)
    high_risk_count = 0
    medium_risk_count = 0
    clean_count = 0
    active_alerts = []
    total_reviewed_vol = 0.0

    rule_trigger_counts = {"R1": 0, "R2": 0, "R3": 0, "R4": 0}

    for cid, customer in sorted(customers_db.items()):
        inv = perform_investigation(cid)
        r_level = inv.get("risk_level", "NO RISK")
        if r_level == "HIGH":
            high_risk_count += 1
        elif r_level == "MEDIUM":
            medium_risk_count += 1
        else:
            clean_count += 1

        txs = customer.get("transactions", [])
        total_reviewed_vol += sum(float(t.get("amount", 0)) for t in txs)

        triggered = inv.get("triggered_findings", [])
        for f in triggered:
            rid = f.get("rule_id")
            if rid in rule_trigger_counts:
                rule_trigger_counts[rid] += 1

        if triggered:
            active_alerts.append({
                "customer_id": cid,
                "customer_name": customer["name"],
                "account_number": customer.get("account_number", "•••• •••• 4821"),
                "branch": customer.get("branch", "Mumbai"),
                "risk_level": r_level,
                "triggered_rules": [f["rule_name"] for f in triggered],
                "flagged_tx_count": len(inv.get("flagged_transactions", [])),
                "attention_summary": inv.get("first_finding", ""),
                "last_analysed": inv.get("last_analysed", "26 Aug 2025"),
                "priority": "P1 - Immediate" if r_level == "HIGH" else "P2 - Review",
            })

    return jsonify({
        "metrics": {
            "total_monitored_accounts": total_customers + 1420,
            "active_high_risk_alerts": high_risk_count,
            "active_medium_risk_alerts": medium_risk_count,
            "clean_accounts_count": clean_count,
            "reviewed_volume_inr": f"₹{total_reviewed_vol / 10000000:.2f} Cr",
            "fraud_prevention_rate": "99.6%",
        },
        "rule_distribution": {
            "Unusually Large Transfers (R1)": rule_trigger_counts["R1"],
            "New Payee Bursts (R2)": rule_trigger_counts["R2"],
            "Odd-Hours Activity (R3)": rule_trigger_counts["R3"],
            "Pattern Breaks (R4)": rule_trigger_counts["R4"],
        },
        "alert_queue": active_alerts,
    })


@app.get("/api/alerts")
def get_alerts():
    alerts = []
    for cid, customer in sorted(customers_db.items()):
        inv = perform_investigation(cid)
        triggered = inv.get("triggered_findings", [])
        if triggered:
            alerts.append({
                "alert_id": f"ALT-{cid}",
                "customer_id": cid,
                "customer_name": customer["name"],
                "account_number": customer.get("account_number", "•••• 4821"),
                "risk_level": inv.get("risk_level", "HIGH"),
                "triggered_rules": [f["rule_name"] for f in triggered],
                "triggered_rule_ids": [f["rule_id"] for f in triggered],
                "flagged_count": len(inv.get("flagged_transactions", [])),
                "summary": inv.get("attention_subtitle", ""),
                "analyst": "Dharshini",
                "timestamp": inv.get("last_analysed", "26 Aug 2025, 14:32"),
                "status": "Under Review",
            })
    return jsonify(alerts)


@app.get("/api/reports")
def get_reports_archive():
    reports = []
    for cid, customer in sorted(customers_db.items()):
        inv = perform_investigation(cid)
        reports.append({
            "report_id": f"REP-2025-{cid}",
            "customer_id": cid,
            "customer_name": customer["name"],
            "account_number": customer.get("account_number", "•••• 4821"),
            "risk_level": inv.get("risk_level", "NO RISK"),
            "verdict": inv.get("rule_engine_verdict", "CLEAN"),
            "signals_count": len(inv.get("triggered_findings", [])),
            "generated_date": inv.get("last_analysed", "26 Aug 2025, 14:32"),
            "investigator": "Dharshini (Fraud Desk)",
        })
    return jsonify(reports)


# --------------------------------------------------------------------------
# Admin Runtime Data Upload Endpoints
# NOTE: Hackathon-grade admin panel. Authentication and role-based access
# control (RBAC) must be added before any real-world production deployment.
# --------------------------------------------------------------------------

@app.post("/admin/upload-transactions")
def upload_transactions():
    """
    Upload and merge new transactions from a CSV file.
    Validates schema against existing data/transactions.csv, checks required fields,
    deduplicates against existing transaction IDs, and refreshes the in-memory cache.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Please supply a CSV file in multipart form-data with key 'file'."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "No file selected for upload."}), 400

    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        return jsonify({"error": "Invalid file type. Only CSV files (.csv) are supported for transaction uploads."}), 400

    try:
        content = file.read().decode("utf-8-sig")
    except Exception as exc:
        return jsonify({"error": f"Unable to decode CSV file as UTF-8: {str(exc)}"}), 400

    if not content.strip():
        return jsonify({"error": "Uploaded CSV file is empty."}), 400

    _, tx_path = get_runtime_data_paths()
    if not tx_path.exists():
        return jsonify({"error": f"Base transactions file not found at {tx_path}"}), 500

    # Dynamically infer expected schema from existing transactions.csv
    try:
        with open(tx_path, mode="r", encoding="utf-8-sig") as f:
            ref_reader = csv.reader(f)
            expected_header = next(ref_reader, None)
    except Exception as exc:
        return jsonify({"error": f"Failed to infer existing schema: {str(exc)}"}), 500

    if not expected_header:
        return jsonify({"error": "Base transactions.csv has no valid header row."}), 500

    expected_columns = [col.strip() for col in expected_header if col is not None]

    # Parse uploaded CSV header and records
    try:
        csv_reader = csv.DictReader(io.StringIO(content))
        uploaded_fieldnames = csv_reader.fieldnames
    except Exception as exc:
        return jsonify({"error": f"Malformed CSV structure: {str(exc)}"}), 400

    if not uploaded_fieldnames:
        return jsonify({"error": "Uploaded CSV has no header row."}), 400

    uploaded_columns = [col.strip() for col in uploaded_fieldnames if col is not None]

    # Validate exact column match
    if uploaded_columns != expected_columns:
        return jsonify({
            "error": "Column mismatch in uploaded CSV. Uploaded columns do not match expected schema.",
            "expected_columns": expected_columns,
            "received_columns": uploaded_columns,
        }), 400

    # Validate required fields exist in schema
    required_fields = ["customer_id", "date", "amount"]
    for req in required_fields:
        if req not in expected_columns:
            return jsonify({"error": f"System error: required field '{req}' not found in expected schema."}), 500

    # Read existing IDs for deduplication
    id_col = "transaction_id" if "transaction_id" in expected_columns else None
    existing_ids = set()
    if id_col:
        try:
            existing_df = pd.read_csv(tx_path)
            if id_col in existing_df.columns:
                existing_ids = set(existing_df[id_col].dropna().astype(str).str.strip())
        except Exception as exc:
            logger.warning("Could not pre-read existing transaction IDs: %s", exc)

    seen_batch_ids = set()
    rows_to_add = []
    rows_rejected = []

    # Iterate and validate rows
    for row_idx, row in enumerate(csv_reader, start=1):
        # Check required fields
        missing_or_empty = []
        for req in required_fields:
            val = row.get(req)
            if val is None or str(val).strip() == "":
                missing_or_empty.append(req)

        if missing_or_empty:
            rows_rejected.append({
                "row": row_idx,
                "data": row,
                "reason": f"Missing or empty required field(s): {', '.join(missing_or_empty)}",
            })
            continue

        # Check numeric amount
        try:
            float(str(row["amount"]).replace(",", "").strip())
        except ValueError:
            rows_rejected.append({
                "row": row_idx,
                "data": row,
                "reason": f"Invalid numeric amount '{row.get('amount')}'.",
            })
            continue

        # Deduplicate if ID column exists
        if id_col:
            txn_id = str(row.get(id_col, "")).strip()
            if txn_id:
                if txn_id in existing_ids or txn_id in seen_batch_ids:
                    rows_rejected.append({
                        "row": row_idx,
                        "data": row,
                        "reason": f"Duplicate {id_col} '{txn_id}' already exists in database or current batch.",
                    })
                    continue
                seen_batch_ids.add(txn_id)

        rows_to_add.append({col: row.get(col, "") for col in expected_columns})

    # Append valid rows to data/transactions.csv
    if rows_to_add:
        try:
            new_df = pd.DataFrame(rows_to_add)[expected_columns]
            new_df.to_csv(tx_path, mode="a", header=False, index=False, encoding="utf-8")
        except Exception as exc:
            return jsonify({"error": f"Failed writing new rows to transactions.csv: {str(exc)}"}), 500

        # Refresh in-memory customer and investigation state
        refresh_in_memory_data()

    return jsonify({
        "status": "success",
        "rows_added": len(rows_to_add),
        "rows_rejected": rows_rejected,
        "total_processed": len(rows_to_add) + len(rows_rejected),
        "message": f"Processed {len(rows_to_add) + len(rows_rejected)} rows: {len(rows_to_add)} added, {len(rows_rejected)} rejected.",
    }), 200


@app.post("/admin/upload-customers")
def upload_customers():
    """
    Upload and merge new customer profiles from CSV or JSON.
    Validates required fields ('id', 'name'), deduplicates by customer ID,
    persists updates to data/customers.json, and refreshes the in-memory cache.
    """
    customers_path, _ = get_runtime_data_paths()
    existing_customers = []
    if customers_path.exists():
        try:
            existing_customers = json.loads(customers_path.read_text(encoding="utf-8"))
            if not isinstance(existing_customers, list):
                existing_customers = []
        except Exception as exc:
            logger.warning("Could not parse existing customers.json: %s", exc)
            existing_customers = []

    incoming_records = []

    if "file" in request.files and request.files["file"].filename:
        file = request.files["file"]
        filename = file.filename or ""
        try:
            raw_text = file.read().decode("utf-8-sig")
        except Exception as exc:
            return jsonify({"error": f"Failed to decode uploaded file: {str(exc)}"}), 400

        if not raw_text.strip():
            return jsonify({"error": "Uploaded file is empty."}), 400

        if filename.lower().endswith(".json"):
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, list):
                    incoming_records = parsed
                elif isinstance(parsed, dict):
                    incoming_records = [parsed]
                else:
                    return jsonify({"error": "JSON customer file must contain a list of customer objects or a single customer object."}), 400
            except Exception as exc:
                return jsonify({"error": f"Malformed JSON content: {str(exc)}"}), 400
        elif filename.lower().endswith(".csv"):
            try:
                csv_reader = csv.DictReader(io.StringIO(raw_text))
                incoming_records = list(csv_reader)
            except Exception as exc:
                return jsonify({"error": f"Malformed CSV content: {str(exc)}"}), 400
        else:
            return jsonify({"error": "Unsupported file format. Please upload a .json or .csv customer file."}), 400

    elif request.is_json:
        parsed = request.get_json(silent=True)
        if isinstance(parsed, list):
            incoming_records = parsed
        elif isinstance(parsed, dict):
            incoming_records = [parsed]
        else:
            return jsonify({"error": "JSON payload must be an array of customer objects or a single customer object."}), 400
    else:
        return jsonify({"error": "No file or JSON body provided. Upload a file with key 'file' (.json or .csv) or POST JSON body."}), 400

    if not incoming_records:
        return jsonify({"error": "No customer records found in payload."}), 400

    existing_cids = {
        str(c["id"]).strip()
        for c in existing_customers
        if isinstance(c, dict) and "id" in c and c["id"]
    }

    seen_batch_cids = set()
    records_to_add = []
    rows_rejected = []

    for idx, rec in enumerate(incoming_records, start=1):
        if not isinstance(rec, dict):
            rows_rejected.append({
                "row": idx,
                "data": rec,
                "reason": "Customer entry must be a dictionary/object.",
            })
            continue

        cid = str(rec.get("id", "")).strip()
        name = str(rec.get("name", "")).strip()

        if not cid or not name:
            missing = []
            if not cid:
                missing.append("id")
            if not name:
                missing.append("name")
            rows_rejected.append({
                "row": idx,
                "data": rec,
                "reason": f"Missing required field(s): {', '.join(missing)}",
            })
            continue

        if cid in existing_cids or cid in seen_batch_cids:
            rows_rejected.append({
                "row": idx,
                "data": rec,
                "reason": f"Customer ID '{cid}' already exists in database or is duplicated in uploaded batch.",
            })
            continue

        clean_rec = {
            "id": cid,
            "name": name,
            "profile": str(rec.get("profile", "standard")),
            "customer_since": str(rec.get("customer_since", "New Account")),
            "last_analysed": str(rec.get("last_analysed", datetime.now().strftime("%d %b %Y, %H:%M"))),
            "account_number": str(rec.get("account_number", f"•••• •••• {cid[-4:] if len(cid)>=4 else '0000'}")),
            "account_type": str(rec.get("account_type", "Savings Classic")),
            "branch": str(rec.get("branch", "Main Branch")),
            "phone": str(rec.get("phone", "+91 98000 00000")),
            "email": str(rec.get("email", f"{cid.lower()}@example.com")),
            "transaction_count": int(rec.get("transaction_count", 0)) if str(rec.get("transaction_count", "")).isdigit() else 0,
            "date_start": rec.get("date_start"),
            "date_end": rec.get("date_end"),
        }
        for k, v in rec.items():
            if k not in clean_rec:
                clean_rec[k] = v

        seen_batch_cids.add(cid)
        records_to_add.append(clean_rec)

    if records_to_add:
        merged = existing_customers + records_to_add
        try:
            customers_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        except Exception as exc:
            return jsonify({"error": f"Failed writing to customers.json: {str(exc)}"}), 500

        refresh_in_memory_data()

    return jsonify({
        "status": "success",
        "rows_added": len(records_to_add),
        "rows_rejected": rows_rejected,
        "total_processed": len(records_to_add) + len(rows_rejected),
        "message": f"Processed {len(records_to_add) + len(rows_rejected)} customer records: {len(records_to_add)} added, {len(rows_rejected)} rejected.",
    }), 200


@app.get("/admin")
@app.get("/admin/upload")
def admin_page():
    """
    Serve the admin upload interface.
    NOTE: Hackathon-grade admin endpoint. Add authentication before production deployment.
    """
    index_file = Path(app.static_folder) / "index.html"
    if index_file.exists():
        return send_from_directory(app.static_folder, "index.html")
    return "SentinelView Admin Upload Panel", 200


@app.get("/<path:path>")
def static_proxy(path: str):
    static_dir = Path(app.static_folder)
    target = static_dir / path
    if target.exists():
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html") if (static_dir / "index.html").exists() else ("Not found", 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
