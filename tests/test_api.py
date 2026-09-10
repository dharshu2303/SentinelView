from copy import deepcopy
import io
import json
import app as app_module
def test_clean_customer_path():
    client = app_module.app.test_client()
    payload = client.post('/api/customers/CUST002/investigate').get_json()
    assert payload['status'] == 'clean'
    assert payload['rule_engine_verdict'] == 'CLEAN'
    assert payload['risk_level'] == 'NO RISK'
    assert payload['attention_required'] is False
    assert 'NO ATTENTION REQUIRED' in payload['attention_title']
    assert len(payload['flagged_transactions']) == 0


def test_flagged_customer_path():
    client = app_module.app.test_client()
    payload = client.post('/api/customers/CUST001/investigate', json={'simulate_gemini_failure': True}).get_json()
    assert payload['status'] == 'flagged'
    assert payload['rule_engine_verdict'] == 'FLAGGED'
    assert payload['risk_level'] == 'HIGH'
    assert payload['attention_required'] is True
    assert 'ATTENTION REQUIRED' in payload['attention_title']
    assert len(payload['flagged_transactions']) == 5
    assert len(payload['key_reasons']) == 3
    assert 'typical_transfer_amount' in payload['behavior_analysis']


def test_gemini_failure_fallback_is_demoable():
    client = app_module.app.test_client()
    payload = client.post('/api/customers/CUST001/investigate', json={'simulate_gemini_failure': True}).get_json()
    assert payload['status'] == 'flagged'
    assert payload['fallback_mode'] is True
    assert len(payload['narrative']['recommended_checks']) > 0


def test_empty_history_returns_sane_response():
    original = deepcopy(app_module.customers_db)
    try:
        app_module.customers_db['EMPTY'] = {
            'id': 'EMPTY',
            'name': 'Empty Example',
            'transactions': [],
            'transaction_count': 0,
            'date_start': None,
            'date_end': None,
        }
        client = app_module.app.test_client()
        payload = client.post('/api/customers/EMPTY/investigate').get_json()
        assert payload['status'] == 'no_data'
        assert payload['fallback_mode'] is True
    finally:
        app_module.customers_db = original


def test_malformed_history_returns_sane_response():
    original = deepcopy(app_module.customers_db)
    try:
        app_module.customers_db['BROKEN'] = {
            'id': 'BROKEN',
            'name': 'Broken Example',
            'transactions': [{'transaction_id': 'X1'}],
            'transaction_count': 1,
            'date_start': None,
            'date_end': None,
        }
        client = app_module.app.test_client()
        payload = client.post('/api/customers/BROKEN/investigate').get_json()
        assert payload['status'] == 'error'
        assert payload['rule_engine_verdict'] == 'DATA_ERROR'
    finally:
        app_module.customers_db = original


def test_no_fraud_declarations():
    client = app_module.app.test_client()
    for cid in ['CUST001', 'CUST002', 'CUST003']:
        payload = client.post(f'/api/customers/{cid}/investigate', json={'simulate_gemini_failure': True}).get_json()
        text_dump = str(payload).lower()
        assert 'fraud has occurred' not in text_dump
        assert 'fraud confirmed' not in text_dump
        assert 'confirmed fraud' not in text_dump


def test_all_customers_have_transactions_for_risk_prediction():
    client = app_module.app.test_client()
    customers_list = client.get('/api/customers').get_json()
    assert len(customers_list) == 12

    for c in customers_list:
        cid = c['id']
        payload = client.post(f'/api/customers/{cid}/investigate').get_json()
        assert 'all_transactions' in payload
        assert len(payload['all_transactions']) >= 50, f"Customer {cid} must have transaction history for baseline evaluation"
        if payload['risk_level'] == 'NO RISK':
            assert len(payload['flagged_transactions']) == 0
        else:
            assert len(payload['flagged_transactions']) > 0


def test_dashboard_alerts_reports_endpoints():
    client = app_module.app.test_client()
    stats = client.get('/api/dashboard/stats').get_json()
    assert 'metrics' in stats
    assert stats['metrics']['active_high_risk_alerts'] > 0
    assert 'rule_distribution' in stats
    assert 'alert_queue' in stats

    alerts = client.get('/api/alerts').get_json()
    assert len(alerts) > 0

    reports = client.get('/api/reports').get_json()
    assert len(reports) == 12


def test_upload_transactions_success_and_cache_refresh():
    tx_path = app_module.DATA_DIR / "transactions.csv"
    orig_tx_bytes = tx_path.read_bytes()
    try:
        client = app_module.app.test_client()
        csv_data = (
            "transaction_id,customer_id,date,description,payee,amount,channel,category,region\n"
            "CUST002-NEW01,CUST002,2025-08-25T14:00:00,Office Supplies,Staples,1500.0,UPI,services,Mumbai_Metro\n"
            "CUST002-NEW02,CUST002,2025-08-25T15:00:00,Software,JetBrains,8500.0,Net Banking,services,Mumbai_Metro\n"
        )
        resp = client.post(
            "/admin/upload-transactions",
            data={"file": (io.BytesIO(csv_data.encode("utf-8")), "new_tx.csv")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["status"] == "success"
        assert payload["rows_added"] == 2
        assert len(payload["rows_rejected"]) == 0

        # Verify transaction was ingested and in-memory cache was refreshed
        cust_tx_resp = client.get("/api/customers/CUST002/transactions").get_json()
        tx_ids = [t["transaction_id"] for t in cust_tx_resp["transactions"]]
        assert "CUST002-NEW01" in tx_ids
        assert "CUST002-NEW02" in tx_ids
    finally:
        tx_path.write_bytes(orig_tx_bytes)
        app_module.refresh_in_memory_data()


def test_upload_transactions_missing_columns():
    client = app_module.app.test_client()
    bad_csv = "customer_id,date,amount\nCUST001,2025-08-25T10:00:00,5000\n"
    resp = client.post(
        "/admin/upload-transactions",
        data={"file": (io.BytesIO(bad_csv.encode("utf-8")), "bad_schema.csv")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 400
    payload = resp.get_json()
    assert "error" in payload
    assert "Column mismatch" in payload["error"]


def test_upload_transactions_deduplication_and_missing_values():
    tx_path = app_module.DATA_DIR / "transactions.csv"
    orig_tx_bytes = tx_path.read_bytes()
    try:
        client = app_module.app.test_client()
        # Row 1: duplicate of existing CUST001-T001
        # Row 2: valid new transaction
        # Row 3: duplicate within same batch (same ID as Row 2)
        # Row 4: missing required date
        # Row 5: invalid amount
        csv_data = (
            "transaction_id,customer_id,date,description,payee,amount,channel,category,region\n"
            "CUST001-T001,CUST001,2025-08-25T10:00:00,Existing Tx,Payee,5000,UPI,services,Mumbai_Metro\n"
            "CUST001-NEW99,CUST001,2025-08-25T11:00:00,New Valid Tx,Payee,6000,UPI,services,Mumbai_Metro\n"
            "CUST001-NEW99,CUST001,2025-08-25T12:00:00,Batch Dupe Tx,Payee,7000,UPI,services,Mumbai_Metro\n"
            "CUST001-NEW100,CUST001,,Missing Date Tx,Payee,8000,UPI,services,Mumbai_Metro\n"
            "CUST001-NEW101,CUST001,2025-08-25T13:00:00,Bad Amount,Payee,NOT_A_NUMBER,UPI,services,Mumbai_Metro\n"
        )
        resp = client.post(
            "/admin/upload-transactions",
            data={"file": (io.BytesIO(csv_data.encode("utf-8")), "mixed.csv")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["status"] == "success"
        assert payload["rows_added"] == 1
        assert len(payload["rows_rejected"]) == 4
        reasons = [r["reason"] for r in payload["rows_rejected"]]
        assert any("already exists" in r for r in reasons)
        assert any("Missing or empty" in r for r in reasons)
        assert any("Invalid numeric amount" in r for r in reasons)
    finally:
        tx_path.write_bytes(orig_tx_bytes)
        app_module.refresh_in_memory_data()


def test_upload_customers_json_and_csv():
    cust_path = app_module.DATA_DIR / "customers.json"
    orig_cust_bytes = cust_path.read_bytes()
    try:
        client = app_module.app.test_client()

        # 1. JSON upload with new customer + duplicate of existing CUST001
        json_payload = [
            {"id": "CUST001", "name": "Priya Sharma"},
            {"id": "CUST099", "name": "Aditi Roy", "branch": "Salt Lake, Kolkata"},
        ]
        resp = client.post(
            "/admin/upload-customers",
            data={"file": (io.BytesIO(json.dumps(json_payload).encode("utf-8")), "customers.json")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["rows_added"] == 1
        assert len(payload["rows_rejected"]) == 1
        assert "already exists" in payload["rows_rejected"][0]["reason"]

        # Verify new customer appears in API
        customers_list = client.get("/api/customers").get_json()
        cids = [c["id"] for c in customers_list]
        assert "CUST099" in cids

        # 2. CSV customer upload with missing name
        csv_data = "id,name,branch\nCUST100,,Connaught Place\nCUST101,Rohan Sen,Park Street\n"
        resp_csv = client.post(
            "/admin/upload-customers",
            data={"file": (io.BytesIO(csv_data.encode("utf-8")), "customers.csv")},
            content_type="multipart/form-data",
        )
        assert resp_csv.status_code == 200
        p_csv = resp_csv.get_json()
        assert p_csv["rows_added"] == 1
        assert len(p_csv["rows_rejected"]) == 1
        assert "Missing required field" in p_csv["rows_rejected"][0]["reason"]
    finally:
        cust_path.write_bytes(orig_cust_bytes)
        app_module.refresh_in_memory_data()


