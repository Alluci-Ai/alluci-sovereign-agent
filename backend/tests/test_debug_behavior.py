import pytest
pytestmark = pytest.mark.unit

from unittest.mock import patch
from backend.ws_gateway import _rpc_error

@patch('backend.app.settings')
def test_rpc_error_without_debug(mock_settings):
    mock_settings.DEBUG = False
    err_json = _rpc_error(id=1, code=-32602, message='Invalid params', data={'field': 'error'})
    err = eval(err_json)  # simple parse
    assert err['error']['code'] == -32602
    assert err['error']['message'] == 'Invalid params'
    # data should NOT be present when DEBUG is False
    assert 'data' not in err['error']

@patch('backend.app.settings')
def test_rpc_error_with_debug(mock_settings):
    mock_settings.DEBUG = True
    err_json = _rpc_error(id=2, code=-32602, message='Invalid params', data={'field': 'error'})
    err = eval(err_json)
    assert err['error']['code'] == -32602
    assert err['error']['message'] == 'Invalid params'
    # data should be included when DEBUG is True
    assert err['error']['data'] == {'field': 'error'}
