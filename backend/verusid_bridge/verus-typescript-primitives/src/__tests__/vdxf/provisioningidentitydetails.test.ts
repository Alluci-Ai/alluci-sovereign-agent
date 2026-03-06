
import { ProvisionIdentityDetails } from "../../vdxf/classes/provisioning/ProvisionIdentityDetails";
import { CompactIAddressObject, CompactAddressObject, RequestURI, ResponseURI } from "../../vdxf/classes";
import { BN } from "bn.js";
import { TEST_IDENTITY_ID_1, TEST_IDENTITY_ID_2 } from "../constants/fixtures";

describe('Serializes and deserializes ProvisionIdentityDetails', () => {
  test('(de)serialize ProvisionIdentityDetails', () => {
    const e = new ProvisionIdentityDetails({
      version: new BN(1, 10),
      flags: ProvisionIdentityDetails.FLAG_HAS_SYSTEMID.or(ProvisionIdentityDetails.FLAG_HAS_PARENTID),
      uri: RequestURI.fromUriString("https://127.0.0.1/provision"),
      systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_1, rootSystemName: "VRSC" }),
      parentID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_2, rootSystemName: "VRSC" })
    });

    const r = e.toBuffer();
    const rFromBuf = new ProvisionIdentityDetails();
    rFromBuf.fromBuffer(r);

    expect(rFromBuf.toBuffer().toString('hex')).toBe(r.toString('hex'));
    expect(rFromBuf.uri!.getUriString()).toBe("https://127.0.0.1/provision");
    expect(rFromBuf.uri!.type.toString()).toBe(ResponseURI.TYPE_POST.toString());
  });

  test('(de)serialize ProvisionIdentity with fqn', async () => {
    const e = new ProvisionIdentityDetails({
      version: new BN(1, 10),
      flags: ProvisionIdentityDetails.FLAG_HAS_IDENTITY_ID,
      uri: RequestURI.fromUriString("https://127.0.0.1/provision"),
      identityID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_1, rootSystemName: "VRSC" })
    })

    const r = e.toBuffer();
    const rFromBuf = new ProvisionIdentityDetails();
    rFromBuf.fromBuffer(r);

    expect(rFromBuf.toBuffer().toString('hex')).toBe(r.toString('hex'));
    expect(rFromBuf.uri!.getUriString()).toBe("https://127.0.0.1/provision");
    expect(rFromBuf.uri!.type.toString()).toBe(ResponseURI.TYPE_POST.toString());
  });

  test('(de)serialize ProvisionIdentityDetails without uri', () => {
    const e = new ProvisionIdentityDetails({
      version: new BN(1, 10),
      flags: ProvisionIdentityDetails.FLAG_HAS_SYSTEMID.or(ProvisionIdentityDetails.FLAG_HAS_PARENTID),
      systemID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_1, rootSystemName: "VRSC" }),
      parentID: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_2, rootSystemName: "VRSC" })
    });

    expect(e.hasUri()).toBe(false);

    const r = e.toBuffer();
    const rFromBuf = new ProvisionIdentityDetails();
    rFromBuf.fromBuffer(r);

    expect(rFromBuf.toBuffer().toString('hex')).toBe(r.toString('hex'));
    expect(rFromBuf.hasUri()).toBe(false);
    expect(rFromBuf.uri).toBeUndefined();
  });
});
