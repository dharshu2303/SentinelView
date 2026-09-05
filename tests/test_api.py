from copy import deepcopy

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

