import json
import logging
from typing import Dict, Any, List
from .tools import register_tool
from backend.security.verus_rpc import verus_rpc

logger = logging.getLogger("VerusTools")

@register_tool(name="verus_get_vdxf_id", description="Gets the VDXF ID of a given string or entity.")
async def verus_get_vdxf_id(entity_name: str) -> str:
    """Gets the VDXF ID of a given string or entity."""
    try:
        # getvdxfid maps exactly to the RPC call
        result = await verus_rpc._call("getvdxfid", [entity_name])
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_get_vdxf_id: {e}")
        return json.dumps({"error": str(e)})

@register_tool(name="verus_get_identity", description="Looks up a VerusID identity on the blockchain.")
async def verus_get_identity(identity_str: str) -> str:
    """Looks up a VerusID identity on the blockchain."""
    try:
        result = await verus_rpc.get_identity(identity_str)
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_get_identity: {e}")
        return json.dumps({"error": str(e)})

@register_tool(name="verus_get_info", description="Gets the general information about the Verus node and blockchain.")
async def verus_get_info() -> str:
    """Gets the general information about the Verus node and blockchain."""
    try:
        result = await verus_rpc.get_info()
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_get_info: {e}")
        return json.dumps({"error": str(e)})

@register_tool(name="verus_get_currency", description="Gets information about a specific Verus currency.")
async def verus_get_currency(currency_name: str) -> str:
    """Gets information about a specific Verus currency."""
    try:
        result = await verus_rpc.get_currency(currency_name)
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_get_currency: {e}")
        return json.dumps({"error": str(e)})
        
@register_tool(name="verus_get_balance", description="Gets the total balance of the node's wallet.")
async def verus_get_balance() -> str:
    """Gets the total balance of the node's wallet."""
    try:
        result = await verus_rpc.get_balance()
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_get_balance: {e}")
        return json.dumps({"error": str(e)})

@register_tool(name="verus_send_currency", description="Sends currency from an address to one or more outputs.")
async def verus_send_currency(from_address: str, outputs_json: str) -> str:
    """Sends currency from an address to one or more outputs."""
    try:
        outputs = json.loads(outputs_json)
        result = await verus_rpc.send_currency(from_address, outputs)
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_send_currency: {e}")
        return json.dumps({"error": str(e)})
        
@register_tool(name="verus_get_offers", description="Gets current marketplace offers for a specific currency.")
async def verus_get_offers(currency: str, is_buy: bool = True) -> str:
    """Gets current marketplace offers for a specific currency."""
    try:
        result = await verus_rpc.get_offers(currency, is_buy)
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_get_offers: {e}")
        return json.dumps({"error": str(e)})
        
@register_tool(name="verus_make_offer", description="Creates an offer on the decentralized marketplace.")
async def verus_make_offer(from_address: str, offer_json: str) -> str:
    """Creates an offer on the decentralized marketplace."""
    try:
        offer = json.loads(offer_json)
        result = await verus_rpc.make_offer(from_address, offer)
        return json.dumps({"result": result})
    except Exception as e:
        logger.error(f"Error in verus_make_offer: {e}")
        return json.dumps({"error": str(e)})
