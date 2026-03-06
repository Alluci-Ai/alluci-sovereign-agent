import { BN } from "bn.js";
import { 
  AuthenticationRequestDetails,
  CompactAddressObject,
  CompactIAddressObject,
  RecipientConstraint
} from "../../vdxf/classes";
import { SERIALIZED_AUTHENTICATION_REQUEST_DETAILS, TEST_CHALLENGE_ID, TEST_IDENTITY_ID_1, TEST_IDENTITY_ID_2, TEST_IDENTITY_ID_3, TEST_SYSTEMID } from "../constants/fixtures";

describe("AuthenticationRequestDetails", () => {
  describe("constructor and basic properties", () => {
    test("creates instance with minimal required data", () => {
      const details = new AuthenticationRequestDetails();

      const detailsBuffer = details.toBuffer();

      const newDetails = new AuthenticationRequestDetails();
      newDetails.fromBuffer(detailsBuffer);

      expect(details.flags?.toString()).toBe("0");
      expect(details.recipientConstraints).toBeNull();
      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
    });

    test("creates instance with all optional data", () => {
      const details = new AuthenticationRequestDetails({
        requestID: CompactIAddressObject.fromAddress(TEST_CHALLENGE_ID, TEST_SYSTEMID.toAddress()!),
        recipientConstraints: [
          { type: RecipientConstraint.REQUIRED_ID, identity: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_1, rootSystemName: "VRSC" }) },
          { type: RecipientConstraint.REQUIRED_SYSTEM, identity: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_2, rootSystemName: "VRSC" }) },
          { type: RecipientConstraint.REQUIRED_PARENT, identity: new CompactIAddressObject({ version: CompactAddressObject.DEFAULT_VERSION, type: CompactAddressObject.TYPE_I_ADDRESS, address: TEST_IDENTITY_ID_3, rootSystemName: "VRSC" }) }
        ],
        expiryTime: new BN(2938475938457) // 1 hour from now
      });

      const detailsBuffer = details.toBuffer();

      const newDetails = new AuthenticationRequestDetails();
      newDetails.fromBuffer(detailsBuffer);

      expect(newDetails.requestID!.toAddress()).toBe(TEST_CHALLENGE_ID);
      expect(newDetails.recipientConstraints?.length).toBe(3);
      expect(newDetails.expiryTime?.toString()).toBe("2938475938457");

      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
    
      expect(details.toBuffer().toString('hex')).toBe(SERIALIZED_AUTHENTICATION_REQUEST_DETAILS.toString('hex'));

    });

    test("creates instance with default constructor", () => {
      const details = new AuthenticationRequestDetails();

      expect(details.hasRequestID()).toBe(false);
      expect(details.flags?.toString()).toBe("0");
      expect(details.recipientConstraints).toBeNull();
    });
  }); 
});
