import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.verus_wallet import VerusWalletService
from backend.models import WalletDashboard
from backend.config import settings

@pytest.fixture
def mock_rpc():
    rpc = MagicMock()
    # Dashboard / Info
    rpc.get_info = AsyncMock(return_value={"name": "VRSC", "blocks": 1000, "connections": 8, "version": 2000000, "longestchain": 1000})
    rpc.get_identity = AsyncMock(return_value={"status": "active", "identity": {"name": "Test@", "identityaddress": "iTest", "contentmultimap": {}}})
    rpc.get_balance = AsyncMock(return_value=100.5)
    rpc.get_unconfirmed_balance = AsyncMock(return_value=1.5)
    rpc.get_mining_info = AsyncMock(return_value={"generate": True, "staking": False, "networkhashps": 1000000, "hashrate": 500, "difficulty": 10.5, "blocks": 1000})
    rpc.list_transactions = AsyncMock(return_value=[{"txid": "tx1", "category": "receive", "amount": 10.0, "time": 1600000000}])
    rpc.get_transaction = AsyncMock(return_value={"txid": "tx1", "category": "receive", "amount": 10.0, "time": 1600000000})
    
    # Balances
    rpc.get_addresses_by_account = AsyncMock(return_value=["addr1", "addr2"])
    rpc.get_currency_balance = AsyncMock(return_value={"VRSC": 50.0, "vETH": 1.5})
    rpc.get_address_balance = AsyncMock(return_value={"balance": 10050000000, "currencybalance": {"VRSC": 100.5}})
    
    # Send / Receive
    rpc.send_to_address = AsyncMock(return_value="txid123")
    rpc.send_currency = AsyncMock(return_value="txid123")
    rpc.get_new_address = AsyncMock(return_value="RNewAddress123")
    
    # Mining
    rpc.set_generate = AsyncMock()
    rpc.get_generate = AsyncMock(return_value=True)
    
    # DeFi / Bridge
    rpc.get_currency = AsyncMock(return_value={"name": "vETH", "bestcurrencystate": {"reservecurrencies": []}})
    rpc.get_currency_converters = AsyncMock(return_value=[{"currency": "vETH"}])
    rpc.get_pending_transfers = AsyncMock(return_value=[{"txid": "pending1"}])
    
    # VDXF
    rpc.update_identity = AsyncMock(return_value="txid_update")
    
    return rpc

@pytest.fixture
def wallet_service(mock_rpc):
    service = VerusWalletService()
    service.rpc = mock_rpc
    service.set_identity("Test@")
    return service

@pytest.mark.asyncio
async def test_set_identity(wallet_service):
    wallet_service.set_identity("NewIdentity")
    assert wallet_service.identity == "NewIdentity@"
    wallet_service.set_identity("iNewIdentity")
    assert wallet_service.identity == "iNewIdentity"

@pytest.mark.asyncio
async def test_get_dashboard_success(wallet_service):
    dashboard = await wallet_service.get_dashboard()
    assert dashboard.connected is True
    assert dashboard.total_vrsc == 100.5
    assert dashboard.unconfirmed == 1.5
    assert dashboard.blockchain["chain"] == "VRSC"
    assert dashboard.mining["generating"] is True
    assert dashboard.mining["local_hashrate"] == 500
    assert len(dashboard.recent_transactions) == 1
    assert dashboard.recent_transactions[0]["txid"] == "tx1"

@pytest.mark.asyncio
async def test_get_dashboard_disconnected(wallet_service, mock_rpc):
    mock_rpc.get_info.side_effect = Exception("Connection refused")
    with patch("backend.config.settings.VERUS_LITE_MODE", False):
        dashboard = await wallet_service.get_dashboard()
        assert dashboard.connected is False
        assert dashboard.total_vrsc == 0.0

@pytest.mark.asyncio
async def test_get_dashboard_lite_mode(wallet_service, mock_rpc):
    with patch("backend.config.settings.VERUS_LITE_MODE", True):
        dashboard = await wallet_service.get_dashboard()
        assert dashboard.connected is True
        assert dashboard.total_vrsc == 100.5

@pytest.mark.asyncio
async def test_get_balances(wallet_service):
    balances = await wallet_service.get_balances()
    assert balances["vrsc"] == 100.5
    assert balances["unconfirmed"] == 1.5
    assert "VRSC" in balances["currencies"]
    assert "vETH" in balances["currencies"]
    assert balances["currencies"]["VRSC"] == 100.0  # 50.0 * 2 addresses
    assert balances["currencies"]["vETH"] == 3.0    # 1.5 * 2 addresses
    assert len(balances["addresses"]) == 2

@pytest.mark.asyncio
async def test_get_balances_lite_mode(wallet_service, mock_rpc):
    with patch("backend.config.settings.VERUS_LITE_MODE", True):
        balances = await wallet_service.get_balances()
        assert balances["vrsc"] == 100.5
        assert len(balances["addresses"]) == 1
        assert balances["addresses"][0]["address"] == "iTest"

@pytest.mark.asyncio
async def test_get_transactions(wallet_service):
    result = await wallet_service.get_transactions(count=10)
    assert len(result["transactions"]) == 1
    assert result["transactions"][0]["txid"] == "tx1"

@pytest.mark.asyncio
async def test_get_transaction_detail(wallet_service):
    result = await wallet_service.get_transaction_detail("tx1")
    assert result["txid"] == "tx1"
    
    # Test error case
    wallet_service.rpc.get_transaction.side_effect = Exception("Not found")
    result_err = await wallet_service.get_transaction_detail("tx_unknown")
    assert result_err == {}

@pytest.mark.asyncio
async def test_send(wallet_service):
    # VRSC send
    res1 = await wallet_service.send("addr1", 10.0, "VRSC")
    assert res1["success"] is True
    wallet_service.rpc.send_to_address.assert_awaited_once_with("addr1", 10.0, "")
    
    # Token send
    res2 = await wallet_service.send("addr1", 10.0, "vETH")
    assert res2["success"] is True
    wallet_service.rpc.send_currency.assert_awaited_once()

@pytest.mark.asyncio
async def test_convert(wallet_service):
    res = await wallet_service.convert(10.0, "VRSC", "vETH", via="Bridge.vETH")
    assert res["success"] is True
    wallet_service.rpc.send_currency.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_receive_address(wallet_service):
    res = await wallet_service.get_receive_address()
    assert res["address"] == "RNewAddress123"

@pytest.mark.asyncio
async def test_create_invoice(wallet_service):
    res = await wallet_service.create_invoice(10.5, memo="Payment")
    assert res["success"] is True
    assert "verus:RNewAddress123" in res["invoice"]["uri"]
    assert "amount=10.5" in res["invoice"]["uri"]

@pytest.mark.asyncio
async def test_mining_staking_methods(wallet_service):
    res1 = await wallet_service.get_mining_status()
    assert res1["generating"] is True
    
    res2 = await wallet_service.start_mining(2)
    assert res2["success"] is True
    wallet_service.rpc.set_generate.assert_awaited_with(True, 2)
    
    res3 = await wallet_service.start_staking()
    assert res3["success"] is True
    wallet_service.rpc.set_generate.assert_awaited_with(True, 0)
    
    res4 = await wallet_service.stop_mining()
    assert res4["success"] is True
    wallet_service.rpc.set_generate.assert_awaited_with(False)

@pytest.mark.asyncio
async def test_defi_methods(wallet_service):
    currencies = await wallet_service.get_currencies()
    assert len(currencies) == 5 # Will mock return for all 5
    
    est = await wallet_service.get_conversion_estimate(10.0, "VRSC", "vETH")
    assert est["estimated"] is True
    assert est["converters"] == 1
    
    wallet_service.rpc.get_currency_converters.side_effect = Exception("Fail")
    est_err = await wallet_service.get_conversion_estimate(10.0, "VRSC", "vETH")
    assert "error" in est_err

@pytest.mark.asyncio
async def test_bridge_methods(wallet_service):
    res1 = await wallet_service.bridge_to_eth(10.0, "VRSC", "0xETH")
    assert res1["success"] is True
    
    res2 = await wallet_service.get_bridge_status()
    assert res2["active"] is True
    assert res2["pending_transfers"] == 1

@pytest.mark.asyncio
async def test_identity_methods(wallet_service):
    info = await wallet_service.get_identity_info()
    assert info["status"] == "active"
    
    manifest = await wallet_service.get_manifest()
    assert manifest == {}
    
    res_update = await wallet_service.update_manifest({"key": "val"})
    assert res_update["success"] is True
    
    res_data = await wallet_service.update_identity_data("key", "val")
    assert res_data["success"] is True

@pytest.mark.asyncio
async def test_vdxf_messaging(wallet_service):
    res1 = await wallet_service.send_vdxf_message("Peer@", "Hello")
    assert res1["success"] is True
    
    # Mock peer outbox
    wallet_service.rpc.get_identity.return_value = {
        "identity": {
            "contentmultimap": {
                "alluci.msg.v1.outbox@": [
                    {"recipient": "Test@", "content": "Hi there!"},
                    {"recipient": "Other@", "content": "Not for you"}
                ]
            }
        }
    }
    msgs = await wallet_service.fetch_vdxf_messages("Peer@")
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Hi there!"

@pytest.mark.asyncio
async def test_start_node(wallet_service):
    assert await wallet_service.start_node() is True
