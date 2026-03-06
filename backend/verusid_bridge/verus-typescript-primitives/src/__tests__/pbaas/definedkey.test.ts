import { BN } from "bn.js";
import { PRINCIPAL_DEFAULT_FLAGS, PRINCIPAL_VERSION_CURRENT, Principal } from "../../pbaas/Principal";
import { KeyID } from "../../pbaas/KeyID";
import { DefinedKey } from "../../pbaas";
import { DATA_TYPE_DEFINEDKEY, IDENTITY_UPDATE_REQUEST_VDXF_KEY, VERUSPAY_INVOICE_VDXF_KEY, WALLET_VDXF_KEY } from "../../vdxf";

describe('Serializes and deserializes DefinedKey', () => {
  test('(de)serialize definedkey with different fqns', () => {
    const keys = [
      VERUSPAY_INVOICE_VDXF_KEY, 
      IDENTITY_UPDATE_REQUEST_VDXF_KEY, 
      WALLET_VDXF_KEY,
      DATA_TYPE_DEFINEDKEY
    ]

    for (const key of keys) {
      const d = new DefinedKey({
        vdxfuri: key.qualifiedname.name,
        version: new BN(1),
        flags: new BN(0)
      })

      const dFromBuf = new DefinedKey();
      dFromBuf.fromBuffer(d.toBuffer());

      expect(dFromBuf.toBuffer().toString('hex')).toBe(d.toBuffer().toString('hex'))
      expect(d.getIAddr()).toBe(key.vdxfid);
    }
  });
});