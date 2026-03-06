import {
  AuthenticationResponseDetails,
  CompactIAddressObject
} from "../../vdxf/classes";
import { TEST_CHALLENGE_ID, TEST_SYSTEMID } from "../constants/fixtures";

describe("AuthenticationRequestDetails", () => {
  describe("constructor and basic properties", () => {
    test("creates instance with all optional data", () => {
      const details = new AuthenticationResponseDetails({
        requestID: CompactIAddressObject.fromAddress(TEST_CHALLENGE_ID, TEST_SYSTEMID.toAddress()!)
      });

      const detailsBuffer = details.toBuffer();

      const newDetails = new AuthenticationResponseDetails();
      newDetails.fromBuffer(detailsBuffer);

      expect(newDetails.requestID!.toAddress()).toBe(TEST_CHALLENGE_ID);

      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
    });
  }); 
});
