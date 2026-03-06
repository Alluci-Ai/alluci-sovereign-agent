import { BN } from "bn.js";
import { AppEncryptionRequestDetails, CompactIAddressObject, CompactAddressObject } from "../../vdxf/classes";
import { BigNumber } from "../../utils/types/BigNumber";
import { SaplingPaymentAddress } from "../../pbaas";

// Helper function to create TransferDestination from address string
function createCompactAddressObject(type: BigNumber, address: string): CompactIAddressObject {
  const obj = new CompactIAddressObject({
    address,
    type
  });
  
  return obj;
}

describe("AppEncryptionRequestDetails serialization tests", () => {
  test("creates valid AppEncryptionRequestDetails without zaddress", () => {
    const details = new AppEncryptionRequestDetails({
      version: AppEncryptionRequestDetails.DEFAULT_VERSION,
      flags: AppEncryptionRequestDetails.FLAG_HAS_DERIVATION_ID
        .or(AppEncryptionRequestDetails.FLAG_HAS_REQUEST_ID),
      derivationNumber: new BN(42),
      derivationID: createCompactAddressObject(CompactAddressObject.TYPE_I_ADDRESS, "i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X"),
      requestID: CompactIAddressObject.fromAddress("iD4CrjbJBZmwEZQ4bCWgbHx9tBHGP9mdSQ")
    });

    const newDetails = new AppEncryptionRequestDetails();
    const buffer = details.toBuffer();
    newDetails.fromBuffer(buffer);
    const originalBuffer = details.toBuffer();
    const deserializedBuffer = newDetails.toBuffer();
    expect(originalBuffer.toString('hex')).toBe(deserializedBuffer.toString('hex'));

    expect(details.isValid()).toBe(true);
    expect(details.derivationNumber.toNumber()).toBe(42);
    expect(details.derivationID?.address).toBe("i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X");
    expect(details.requestID?.toAddress()).toBe("iD4CrjbJBZmwEZQ4bCWgbHx9tBHGP9mdSQ");
  });

  test("creates valid AppEncryptionRequestDetails with zaddress", () => {
    const details = new AppEncryptionRequestDetails({
      version: AppEncryptionRequestDetails.DEFAULT_VERSION,
      flags: AppEncryptionRequestDetails.FLAG_HAS_DERIVATION_ID
        .or(AppEncryptionRequestDetails.FLAG_HAS_REQUEST_ID),
      encryptResponseToAddress: SaplingPaymentAddress.fromAddressString("zs1sthrnsx5vmpmdl3pcd0paltcq9jf56hjjzu87shf90mt54y3szde6zaauvxw5sfuqh565arhmh4"),
      derivationNumber: new BN(42),
      derivationID: createCompactAddressObject(CompactAddressObject.TYPE_I_ADDRESS, "i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X"),
      requestID: CompactIAddressObject.fromAddress("iD4CrjbJBZmwEZQ4bCWgbHx9tBHGP9mdSQ")
    });

    const newDetails = new AppEncryptionRequestDetails();
    const buffer = details.toBuffer();
    newDetails.fromBuffer(buffer);
    const originalBuffer = details.toBuffer();
    const deserializedBuffer = newDetails.toBuffer();
    expect(originalBuffer.toString('hex')).toBe(deserializedBuffer.toString('hex'));

    expect(details.isValid()).toBe(true);
    expect(details.encryptResponseToAddress!.toAddressString()).toBe("zs1sthrnsx5vmpmdl3pcd0paltcq9jf56hjjzu87shf90mt54y3szde6zaauvxw5sfuqh565arhmh4");
    expect(details.derivationNumber.toNumber()).toBe(42);
    expect(details.derivationID?.address).toBe("i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X");
    expect(details.requestID?.toAddress()).toBe("iD4CrjbJBZmwEZQ4bCWgbHx9tBHGP9mdSQ");
  });

  test("serializes and deserializes AppEncryptionRequestDetails correctly", () => {
    // Create the first AppEncryptionRequestDetails
    const originalDetails = new AppEncryptionRequestDetails({
      version: AppEncryptionRequestDetails.DEFAULT_VERSION,
      flags: AppEncryptionRequestDetails.FLAG_HAS_DERIVATION_ID
      .or(AppEncryptionRequestDetails.FLAG_HAS_REQUEST_ID),
      encryptResponseToAddress: SaplingPaymentAddress.fromAddressString("zs1sthrnsx5vmpmdl3pcd0paltcq9jf56hjjzu87shf90mt54y3szde6zaauvxw5sfuqh565arhmh4"),
      derivationNumber: new BN(42),
      derivationID: createCompactAddressObject(CompactAddressObject.TYPE_I_ADDRESS, "i9nwxtKuVYX4MSbeULLiK2ttVi6rUEhh4X"),
      requestID: CompactIAddressObject.fromAddress("iD4CrjbJBZmwEZQ4bCWgbHx9tBHGP9mdSQ")
  });

    // Serialize to buffer
    const buffer = originalDetails.toBuffer();

    // Create a new instance and deserialize from buffer
    const deserializedDetails = new AppEncryptionRequestDetails();
    deserializedDetails.fromBuffer(buffer);

    // Verify both instances are valid
    expect(originalDetails.isValid()).toBe(true);
    expect(deserializedDetails.isValid()).toBe(true);

    // Verify all properties match
    expect(deserializedDetails.version.toNumber()).toBe(originalDetails.version.toNumber());
    expect(deserializedDetails.flags.toNumber()).toBe(originalDetails.flags.toNumber());
    expect(deserializedDetails.encryptResponseToAddress!.toAddressString()).toBe(originalDetails.encryptResponseToAddress!.toAddressString());
    expect(deserializedDetails.derivationNumber.toNumber()).toBe(originalDetails.derivationNumber.toNumber());
    expect(deserializedDetails.derivationID?.BNType.toNumber()).toBe(originalDetails.derivationID?.BNType.toNumber());
    expect(deserializedDetails.derivationID?.address).toBe(originalDetails.derivationID?.address);
    expect(deserializedDetails.requestID?.toAddress()).toBe(originalDetails.requestID?.toAddress());

    // Verify that serializing both instances produces the same buffer
    const originalBuffer = originalDetails.toBuffer();
    const deserializedBuffer = deserializedDetails.toBuffer();
    expect(originalBuffer.toString('hex')).toBe(deserializedBuffer.toString('hex'));
  });

  test("fromIAddress creates valid CompactAddressObject", () => {
    const iaddr = "iDZvpsGCfX6vMJxi3F7m26qCX2Ns6QtQYk";
    const compactObj = CompactAddressObject.fromIAddress(iaddr);

    expect(compactObj).toBeInstanceOf(CompactAddressObject);
    expect(compactObj.address).toBe(iaddr);
    expect(compactObj.BNType.toString()).toBe(CompactAddressObject.TYPE_I_ADDRESS.toString());

    const item = new CompactAddressObject();
    item.fromBuffer(compactObj.toBuffer());

    expect(compactObj.toBuffer().toString('hex')).toBe(item.toBuffer().toString('hex'));

  });

  test("toIAddress converts FQN to IAddress correctly", () => {
    const fqn = "myidentity.VRSC@";
    const compactObj = new CompactAddressObject({
      type: CompactAddressObject.TYPE_FQN,
      address: fqn,
      rootSystemName: "VRSC"
    });
    const iaddr = compactObj.toIAddress();

    expect(iaddr).toBe("iDZvpsGCfX6vMJxi3F7m26qCX2Ns6QtQYk");
    const item = new CompactAddressObject();
    item.fromBuffer(compactObj.toBuffer());

    expect(compactObj.toBuffer().toString('hex')).toBe(item.toBuffer().toString('hex'));

  });
});
