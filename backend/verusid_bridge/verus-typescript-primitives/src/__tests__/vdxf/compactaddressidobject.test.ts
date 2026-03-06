import { CompactAddressObject, CompactAddressXVariant, CompactXAddressObject } from '../../vdxf/classes/CompactAddressObject';
import { BN } from "bn.js";



describe("CompactAddressObject", () => {
  describe("constructor and basic properties", () => {

    test("creates instance with iaddress", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_I_ADDRESS,
        address: "iB5PRXMHLYcNtM8dfLB6KwfJrHU2mKDYuU",
        rootSystemName: "VRSC"
      });

      const detailsBuffer = item.toBuffer();

      const newDetails = new CompactAddressObject();
      newDetails.fromBuffer(detailsBuffer);
      expect(newDetails.version.toString()).toBe("1");
      expect(newDetails.BNType.toNumber()).toBe(CompactAddressObject.TYPE_I_ADDRESS.toNumber());
      expect(newDetails.address).toBe("iB5PRXMHLYcNtM8dfLB6KwfJrHU2mKDYuU");
      expect(newDetails.rootSystemName).toBe("VRSC");
      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
      expect(item.toIAddress()).toBe("iB5PRXMHLYcNtM8dfLB6KwfJrHU2mKDYuU");
    });

    test("creates instance with xaddress", () => {
      const item = new CompactAddressObject<CompactAddressXVariant>({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_X_ADDRESS,
        address: "xA91QPpBrHZto92NCU5KEjCqRveS4dAPrf",
        rootSystemName: "VRSC"
      });

      const detailsBuffer = item.toBuffer();

      const newDetails = new CompactAddressObject<CompactAddressXVariant>();
      newDetails.fromBuffer(detailsBuffer);
      expect(newDetails.version.toString()).toBe("1");
      expect(newDetails.BNType.toNumber()).toBe(CompactAddressObject.TYPE_X_ADDRESS.toNumber());
      expect(newDetails.address).toBe("xA91QPpBrHZto92NCU5KEjCqRveS4dAPrf");
      expect(newDetails.rootSystemName).toBe("VRSC");
      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
    });

    test("creates instance with data key", () => {
      const item = new CompactAddressObject<CompactAddressXVariant>({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "vrsc::applications.wallet"
      });

      const detailsBuffer = item.toBuffer();

      const newDetails = new CompactAddressObject<CompactAddressXVariant>();
      newDetails.fromBuffer(detailsBuffer);
      expect(newDetails.version.toString()).toBe("1");
      expect(newDetails.BNType.toNumber()).toBe(CompactAddressObject.TYPE_FQN.toNumber());
      expect(newDetails.address).toBe("vrsc::applications.wallet");
      expect(newDetails.rootSystemName).toBe("VRSC");
      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
      expect(item.toXAddress()).toBe("xA91QPpBrHZto92NCU5KEjCqRveS4dAPrf");
    });

    test("creates instance of CompactXAddress with data key", () => {
      const item = new CompactXAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "vrsc::applications.wallet"
      });

      const detailsBuffer = item.toBuffer();

      const newDetails = new CompactAddressObject<CompactAddressXVariant>();
      newDetails.fromBuffer(detailsBuffer);
      expect(newDetails.version.toString()).toBe("1");
      expect(newDetails.BNType.toNumber()).toBe(CompactAddressObject.TYPE_FQN.toNumber());
      expect(newDetails.address).toBe("vrsc::applications.wallet");
      expect(newDetails.rootSystemName).toBe("VRSC");
      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
      expect(item.toAddress()).toBe("xA91QPpBrHZto92NCU5KEjCqRveS4dAPrf");
    });

    test("creates instance with fqn", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "bob.chips@",
        rootSystemName: "VRSC"
      });

      const detailsBuffer = item.toBuffer();

      const newDetails = new CompactAddressObject();
      newDetails.fromBuffer(detailsBuffer);
      expect(newDetails.version.toString()).toBe("1");
      expect(newDetails.BNType.toNumber()).toBe(CompactAddressObject.TYPE_FQN.toNumber());
      expect(newDetails.address).toBe("bob.chips@");
      expect(newDetails.rootSystemName).toBe("VRSC");
      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
    });

    test("creates instance with fqn that reduces to iaddress for space saving", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "bob91283472394872349824728934789234.token823984279847293847239487239847324.chips@",
        rootSystemName: "VRSC"
      });

      const detailsBuffer = item.toBuffer(); // this mutates the item to use iaddress internally

      const newDetails = new CompactAddressObject();
      newDetails.fromBuffer(detailsBuffer);
      expect(newDetails.version.toString()).toBe("1");
      expect(newDetails.rootSystemName).toBe("VRSC");
      expect(detailsBuffer.toString('hex')).toBe(newDetails.toBuffer().toString('hex'));
    });
  });

  describe("FQN suffix optimization", () => {
    test("strips .vrsc suffix from simple identity name", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "alice.vrsc",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // After deserialization, suffix should remain stripped
      expect(newDetails.address).toBe("alice");
      expect(newDetails.rootSystemName).toBe("VRSC");
      // Buffer should be smaller (no .vrsc suffix)
      expect(buffer.toString('hex')).not.toContain(Buffer.from('.vrsc', 'utf8').toString('hex'));
    });

    test("strips .vrsctest suffix from testnet identity", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "bob.vrsctest",
        rootSystemName: "VRSCTEST"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSCTEST";
      newDetails.fromBuffer(buffer);

      // After deserialization, suffix should remain stripped
      expect(newDetails.address).toBe("bob");
      expect(newDetails.rootSystemName).toBe("VRSCTEST");
      // Buffer should be smaller (no .vrsctest suffix)
      expect(buffer.toString('hex')).not.toContain(Buffer.from('.vrsctest', 'utf8').toString('hex'));
    });

    test("strips .vrsc@ suffix while preserving @ symbol", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "michael.vrsc@",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // After deserialization, should be "michael@" (suffix stripped but @ preserved)
      expect(newDetails.address).toBe("michael@");
      expect(newDetails.rootSystemName).toBe("VRSC");
    });

    test("preserves complex FQN with dots and @ unchanged", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "bob.chips@",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Complex name (contains dots) should not have suffix added
      expect(newDetails.address).toBe("bob.chips@");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("preserves VDXF keys unchanged (contains ::)", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "vrsc::applications.wallet",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // VDXF keys should remain unchanged
      expect(newDetails.address).toBe("vrsc::applications.wallet");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("preserves root system name unchanged", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "VRSC",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Root system name itself should not be modified
      expect(newDetails.address).toBe("VRSC");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("preserves explicitly defined FQN (ending with .)", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "example.",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Explicit definition (ending with .) should remain unchanged
      expect(newDetails.address).toBe("example.");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("preserves explicitly defined FQN (ending with .@)", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "example.@",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Explicit definition (ending with .) should remain unchanged
      expect(newDetails.address).toBe("example.@");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("handles strangely named fqn (vrsctest.vrsc.vrsc) with root system VRSC", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "vrsctest.vrsc.vrsc",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Explicit definition (ending with .) should remain unchanged
      expect(newDetails.address).toBe("vrsctest.vrsc");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("handles strangely named fqn (vrsctest.vrsc.vrsc@) with root system VRSC", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "vrsctest.vrsc.vrsc@",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Explicit definition (ending with .) should remain unchanged
      expect(newDetails.address).toBe("vrsctest.vrsc@");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("handles simple name without suffix", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "charlie",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Simple name without suffix should remain as-is
      expect(newDetails.address).toBe("charlie");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });

    test("round-trip consistency with suffix stripping", () => {
      const originalAddress = "david.vrsc";
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: originalAddress,
        rootSystemName: "VRSC"
      });

      const buffer1 = item.toBuffer();
      const deserialized1 = new CompactAddressObject();
      deserialized1.rootSystemName = "VRSC";
      deserialized1.fromBuffer(buffer1);

      // After first round-trip, suffix should be stripped
      expect(deserialized1.address).toBe("david");

      // Second serialization should produce same buffer
      const buffer2 = deserialized1.toBuffer();
      expect(buffer2.toString('hex')).toBe(buffer1.toString('hex'));

      // Third round-trip should still work
      const deserialized2 = new CompactAddressObject();
      deserialized2.rootSystemName = "VRSC";
      deserialized2.fromBuffer(buffer2);
      expect(deserialized2.address).toBe("david");
    });

    test("different rootSystemName contexts", () => {
      // Serialize with VRSC
      const itemVRSC = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "alice.vrsc",
        rootSystemName: "VRSC"
      });

      // Serialize with VRSCTEST
      const itemVRSCTEST = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "alice.vrsctest",
        rootSystemName: "VRSCTEST"
      });

      const bufferVRSC = itemVRSC.toBuffer();
      const bufferVRSCTEST = itemVRSCTEST.toBuffer();

      // Both should serialize to "alice"
      const deserializedVRSC = new CompactAddressObject();
      deserializedVRSC.rootSystemName = "VRSC";
      deserializedVRSC.fromBuffer(bufferVRSC);
      expect(deserializedVRSC.address).toBe("alice");

      const deserializedVRSCTEST = new CompactAddressObject();
      deserializedVRSCTEST.rootSystemName = "VRSCTEST";
      deserializedVRSCTEST.fromBuffer(bufferVRSCTEST);
      expect(deserializedVRSCTEST.address).toBe("alice");

      // Buffers should be identical (both serialize "alice")
      expect(bufferVRSC.toString('hex')).toBe(bufferVRSCTEST.toString('hex'));
    });

    test("case insensitive suffix matching", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "Alice.VRSC",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Case-insensitive suffix should be stripped, preserving case of name
      expect(newDetails.address).toBe("Alice");
    });

    test("preserves @ in complex name with @ symbol", () => {
      const item = new CompactAddressObject({
        version: new BN(CompactAddressObject.DEFAULT_VERSION),
        type: CompactAddressObject.TYPE_FQN,
        address: "john.doe.smith@",
        rootSystemName: "VRSC"
      });

      const buffer = item.toBuffer();
      const newDetails = new CompactAddressObject();
      newDetails.rootSystemName = "VRSC";
      newDetails.fromBuffer(buffer);

      // Complex name with @ should remain unchanged
      expect(newDetails.address).toBe("john.doe.smith@");
      expect(buffer.toString('hex')).toBe(item.toBuffer().toString('hex'));
    });
  });
});
