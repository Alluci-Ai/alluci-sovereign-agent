import { I_ADDR_VERSION, X_ADDR_VERSION } from "../../constants/vdxf";
import { getDataKey, nameAndParentAddrToIAddr, toIAddress } from "../../utils/address";
import { DATA_TYPE_DEFINEDKEY, IDENTITY_UPDATE_REQUEST_VDXF_KEY, VERUSPAY_INVOICE_VDXF_KEY, WALLET_VDXF_KEY } from "../../vdxf";

describe('Address tests', () => {
  test('toIAddress tests', async () => {
    expect(toIAddress("VRSCTEST")).toBe("iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq");
    expect(toIAddress("Andromeda.VRSCTEST")).toBe("iNC9NG5Jqk2tqVtqfjfiSpaqxrXaFU6RDu");
    expect(toIAddress("service.VRSCTEST@")).toBe("iFZC7A1HnnJGwBmoPjX3mG37RKbjZZLPhm");
    expect(toIAddress("VRSC")).toBe("i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV");
    expect(toIAddress("The Verus Coin Foundation.VRSC@")).toBe("iDV1KZA6vBXi9k6K3imiSLe5CsYG6MdH4V");
    expect(toIAddress("The Verus Coin Foundation.VRSC")).toBe("iDV1KZA6vBXi9k6K3imiSLe5CsYG6MdH4V");
    expect(toIAddress("Test.VRSC-BTC.VRSCTEST@")).toBe("i9PCGgRJiaRvxbgZ8T5dd33qjFP4NVJvZm");
    expect(toIAddress("Test.VRSC-BTC@", "VRSCTEST")).toBe("i9PCGgRJiaRvxbgZ8T5dd33qjFP4NVJvZm");
    expect(toIAddress("The Verus Coin Foundation@", "VRSC")).toBe("iDV1KZA6vBXi9k6K3imiSLe5CsYG6MdH4V");
    expect(toIAddress("Ⓐ.VRSC")).toBe("iKaSEU4KPrKahpemwHLoQVLPUof6fSE1uk");
    expect(toIAddress("Ⓐtest.VRSC@")).toBe("iENnjC8BaDqjEWYQGxhEZuDeWeFQ5qfjGn");
    expect(toIAddress("The Verus Coin Foundation.vrsc")).toBe("iDV1KZA6vBXi9k6K3imiSLe5CsYG6MdH4V");
    expect(toIAddress("The Verus Coin Foundation.vrsc", "VRSC")).toBe("iDV1KZA6vBXi9k6K3imiSLe5CsYG6MdH4V");
  });

  test('nameAndParentAddrToIAddr tests', async () => {
    expect(nameAndParentAddrToIAddr("VRSCTEST")).toBe("iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq");
    expect(nameAndParentAddrToIAddr("Andromeda", "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq")).toBe("iNC9NG5Jqk2tqVtqfjfiSpaqxrXaFU6RDu");
    expect(nameAndParentAddrToIAddr("VRSC")).toBe("i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV");
    expect(nameAndParentAddrToIAddr("The Verus Coin Foundation", "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV")).toBe("iDV1KZA6vBXi9k6K3imiSLe5CsYG6MdH4V");
  });

  test('getDataKey tests', () => {
    const keys = [
      VERUSPAY_INVOICE_VDXF_KEY, 
      IDENTITY_UPDATE_REQUEST_VDXF_KEY, 
      WALLET_VDXF_KEY,
      DATA_TYPE_DEFINEDKEY
    ]

    for (const key of keys) {
      const dataKeyI = getDataKey(key.qualifiedname.name, undefined, undefined, I_ADDR_VERSION);
      const dataKeyX = getDataKey(key.qualifiedname.name, undefined, undefined, X_ADDR_VERSION);

      expect(dataKeyI.id).toBe(key.vdxfid);
      expect(dataKeyI.namespace).toBe(key.qualifiedname.namespace);
      expect(dataKeyX.id).toBe(key.indexid!);
      expect(dataKeyX.namespace).toBe(key.qualifiedname.namespace);
    }
  });
});
