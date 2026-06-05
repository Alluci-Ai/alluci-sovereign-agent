import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from backend.security.verus_rpc import VerusRPCClient
from backend.config import settings

@pytest.fixture
def rpc():
    return VerusRPCClient()

@pytest.mark.asyncio
async def test_rpc_call_success(rpc):
    with patch.object(rpc.client, "post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": "success_data", "error": None}
        mock_post.return_value = mock_resp
        
        result = await rpc._call("testmethod", ["param1"])
        assert result == "success_data"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs["json"]["method"] == "testmethod"
        assert kwargs["json"]["params"] == ["param1"]

@pytest.mark.asyncio
async def test_rpc_auth():
    with patch("backend.security.verus_rpc.settings") as mock_s:
        mock_s.VERUS_RPC_USER = "testuser"
        mock_s.VERUS_RPC_PASSWORD = "testpassword"
        mock_s.VERUS_RPC_HOST = "127.0.0.1"
        mock_s.VERUS_RPC_PORT = 1234
        mock_s.VERUS_PUBLIC_RPC_URL = "http://public"
        mock_s.VERUS_LITE_MODE = False
        
        rpc_auth = VerusRPCClient()
        assert rpc_auth.auth == ("testuser", "testpassword")
        
        with patch.object(rpc_auth.client, "post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"result": "success_data", "error": None}
            mock_post.return_value = mock_resp
            
            await rpc_auth._call("testmethod", [])
            args, kwargs = mock_post.call_args
            assert kwargs["auth"] == ("testuser", "testpassword")

@pytest.mark.asyncio
async def test_rpc_call_rpc_error(rpc):
    with patch.object(rpc.client, "post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": None, "error": "Something went wrong"}
        mock_post.return_value = mock_resp
        
        with pytest.raises(Exception, match="Something went wrong"):
            await rpc._call("testmethod", [])

@pytest.mark.asyncio
async def test_rpc_call_http_error(rpc):
    with patch.object(rpc.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        
        with pytest.raises(httpx.ConnectError):
            await rpc._call("testmethod", [])

@pytest.mark.asyncio
async def test_rpc_call_fallback_rpc_error(rpc):
    # If a safe method returns an RPC error and local fails, it should fallback to public
    with patch.object(rpc.client, "post", new_callable=AsyncMock) as mock_post:
        # First call fails with RPC error
        mock_resp_fail = MagicMock()
        mock_resp_fail.json.return_value = {"error": "Local node sync error"}
        
        # Second call succeeds
        mock_resp_success = MagicMock()
        mock_resp_success.json.return_value = {"result": "public_data", "error": None}
        
        mock_post.side_effect = [mock_resp_fail, mock_resp_success]
        
        with patch("backend.security.verus_rpc.settings") as mock_s:
            mock_s.VERUS_LITE_MODE = False
            result = await rpc._call("getinfo", [])
            assert result == "public_data"
            assert mock_post.call_count == 2

@pytest.mark.asyncio
async def test_rpc_call_fallback_http_error(rpc):
    with patch.object(rpc.client, "post", new_callable=AsyncMock) as mock_post:
        mock_resp_success = MagicMock()
        mock_resp_success.json.return_value = {"result": "public_data", "error": None}
        mock_post.side_effect = [httpx.ConnectError("down"), mock_resp_success]
        
        with patch("backend.security.verus_rpc.settings") as mock_s:
            mock_s.VERUS_LITE_MODE = False
            result = await rpc._call("getinfo", [])
            assert result == "public_data"
            assert mock_post.call_count == 2

@pytest.mark.asyncio
async def test_identity_methods(rpc):
    with patch.object(rpc, "_call", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "ok"
        await rpc.get_identity("id@")
        mock_call.assert_called_with("getidentity", ["id@"])
        
        await rpc.sign_message("id@", "msg")
        mock_call.assert_called_with("signmessage", ["id@", "msg"])
        
        await rpc.verify_message("id@", "sig", "msg")
        mock_call.assert_called_with("verifymessage", ["id@", "sig", "msg"])
        
        await rpc.update_identity({"name": "id@"})
        mock_call.assert_called_with("updateidentity", [{"name": "id@"}])
        
        await rpc.register_name_commitment("name", "addr", "ref")
        mock_call.assert_called_with("registernamecommitment", ["name", "addr", "ref"])
        
        await rpc.register_identity({"commit": "data"})
        mock_call.assert_called_with("registeridentity", [{"commit": "data"}])
        
        await rpc.revoke_identity("id@")
        mock_call.assert_called_with("revokeidentity", ["id@"])
        
        await rpc.recover_identity("id@")
        mock_call.assert_called_with("recoveridentity", ["id@"])
        
        await rpc.set_identity_timelock("id@", 100)
        mock_call.assert_called_with("updateidentity", [{"name": "id@", "flags": 2, "timelock": 100}])

@pytest.mark.asyncio
async def test_get_content_multimap(rpc):
    with patch.object(rpc, "get_identity", new_callable=AsyncMock) as mock_get_id:
        mock_get_id.return_value = {"identity": {"contentmultimap": {"k1": ["v1"], "k2": ["v2"]}}}
        
        res_all = await rpc.get_content_multimap("id@")
        assert res_all == {"k1": ["v1"], "k2": ["v2"]}
        
        res_key = await rpc.get_content_multimap("id@", "k1")
        assert res_key == ["v1"]

@pytest.mark.asyncio
async def test_wallet_methods(rpc):
    with patch.object(rpc, "_call", new_callable=AsyncMock) as mock_call:
        await rpc.get_balance("*", 1)
        mock_call.assert_called_with("getbalance", ["*", 1])
        
        await rpc.get_currency_balance("addr")
        mock_call.assert_called_with("getcurrencybalance", ["addr"])
        
        await rpc.get_unconfirmed_balance()
        mock_call.assert_called_with("getunconfirmedbalance", [])
        
        await rpc.list_unspent(1, 99, ["addr"])
        mock_call.assert_called_with("listunspent", [1, 99, ["addr"]])
        
        await rpc.list_transactions("*", 10, 5)
        mock_call.assert_called_with("listtransactions", ["*", 10, 5])
        
        await rpc.get_transaction("tx1")
        mock_call.assert_called_with("gettransaction", ["tx1"])
        
        await rpc.send_to_address("addr", 10.0, "c1", "c2")
        mock_call.assert_called_with("sendtoaddress", ["addr", 10.0, "c1", "c2"])
        
        await rpc.send_currency("addr", [{"a": 1}], 1, 0.01)
        mock_call.assert_called_with("sendcurrency", ["addr", [{"a": 1}], 1, 0.01])
        
        await rpc.get_new_address()
        mock_call.assert_called_with("getnewaddress", [])
        
        await rpc.get_addresses_by_account("acc")
        mock_call.assert_called_with("getaddressesbyaccount", ["acc"])
        
        await rpc.validate_address("addr")
        mock_call.assert_called_with("validateaddress", ["addr"])
        
        await rpc.get_wallet_info()
        mock_call.assert_called_with("getwalletinfo", [])

@pytest.mark.asyncio
async def test_z_methods(rpc):
    with patch.object(rpc, "_call", new_callable=AsyncMock) as mock_call:
        await rpc.z_get_balance("zaddr", 1)
        mock_call.assert_called_with("z_getbalance", ["zaddr", 1])
        
        await rpc.z_get_new_address()
        mock_call.assert_called_with("z_getnewaddress", [])
        
        await rpc.z_send_many("fromz", [{"a": 1}], 1, 0.01)
        mock_call.assert_called_with("z_sendmany", ["fromz", [{"a": 1}], 1, 0.01])
        
        await rpc.z_get_operation_result(["op1"])
        mock_call.assert_called_with("z_getoperationresult", [["op1"]])
        
        await rpc.z_list_addresses()
        mock_call.assert_called_with("z_listaddresses", [])

@pytest.mark.asyncio
async def test_defi_methods(rpc):
    with patch.object(rpc, "_call", new_callable=AsyncMock) as mock_call:
        await rpc.get_currency("VRSC")
        mock_call.assert_called_with("getcurrency", ["VRSC"])
        
        await rpc.get_currency_converters(["VRSC"])
        mock_call.assert_called_with("getcurrencyconverters", [["VRSC"]])
        
        await rpc.define_currency({"k": "v"})
        mock_call.assert_called_with("definecurrency", [{"k": "v"}])
        
        await rpc.get_offers("VRSC", True, False)
        mock_call.assert_called_with("getoffers", ["VRSC", True, False])
        
        await rpc.make_offer("addr", {"o": 1}, True)
        mock_call.assert_called_with("makeoffer", ["addr", {"o": 1}, True])

@pytest.mark.asyncio
async def test_mining_methods(rpc):
    with patch.object(rpc, "_call", new_callable=AsyncMock) as mock_call:
        await rpc.set_generate(True, 2)
        mock_call.assert_called_with("setgenerate", [True, 2])
        
        await rpc.get_mining_info()
        mock_call.assert_called_with("getmininginfo", [])
        
        await rpc.get_generate()
        mock_call.assert_called_with("getgenerate", [])
        
        await rpc.get_block_template({"k": "v"})
        mock_call.assert_called_with("getblocktemplate", [{"k": "v"}])

@pytest.mark.asyncio
async def test_info_methods(rpc):
    with patch.object(rpc, "_call", new_callable=AsyncMock) as mock_call:
        await rpc.get_blockchain_info()
        mock_call.assert_called_with("getblockchaininfo", [])
        
        await rpc.get_info()
        mock_call.assert_called_with("getinfo", [])
        
        await rpc.get_address_balance(["addr"])
        mock_call.assert_called_with("getaddressbalance", [{"addresses": ["addr"]}])

@pytest.mark.asyncio
async def test_bridge_methods(rpc):
    with patch.object(rpc, "_call", new_callable=AsyncMock) as mock_call:
        await rpc.get_cross_chain_export("tx1")
        mock_call.assert_called_with("getcrosschain export", ["tx1"])
        
        await rpc.get_pending_transfers("VRSC")
        mock_call.assert_called_with("getpendingtransfers", ["VRSC"])

@pytest.mark.asyncio
async def test_close(rpc):
    with patch.object(rpc.client, "aclose", new_callable=AsyncMock) as mock_close:
        await rpc.close()
        mock_close.assert_called_once()
