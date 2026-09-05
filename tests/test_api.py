from copy import deepcopy

import app as app_module



def test_clean_customer_path():
    client = app_module.app.test_client()
    payload = client.post('/api/customers/C001/investigate').get_json()
    assert payload['status'] == 'clean'
    assert payload['rule_engine_verdict'] == 'CLEAN'


def test_gemini_failure_fallback_is_demoable():
    client = app_module.app.test_client()
    payload = client.post('/api/customers/C003/investigate', json={'simulate_gemini_failure': True}).get_json()
    assert payload['status'] == 'flagged'
    assert payload['fallback_mode'] is True
    assert 'AI narrative unavailable' in payload['narrative']['summary']


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
