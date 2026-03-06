/**
 * @fileoverview
 * This test verifies the correct calculation of the Merkle Mountain Range (MMR) root from a provided list of hashes.
 *
 * The test performs the following steps:
 * 1. Loads an MMR descriptor fixture containing serialized MMR hash data.
 * 2. Deserializes the hash list from the descriptor using the appropriate VDXF key.
 * 3. Iterates through the list of 32-byte hashes, constructing an array of Buffer objects.
 * 4. For each hash, creates an `MMRNode` and adds it to a new `MerkleMountainRange` instance.
 * 5. Constructs a `MerkleMountainView` (MMV) from the populated MMR.
 * 6. Calculates the MMR root by hashing up the MMV.
 * 7. Asserts that the computed MMR root matches the expected root from the fixture.
 *
 * This ensures that the MMR and MMV implementations correctly aggregate a set of leaf hashes into the expected root hash.
 */
import { VDXFData } from "../../vdxf";
import { VdxfUniValue } from "../../pbaas/VdxfUniValue";
import { SaltedData } from "../../pbaas/SaltedData";
import { MMRDescriptor } from "../../pbaas/MMRDescriptor";
import { MerkleMountainRange, MMRNode, MerkleMountainView } from "../../pbaas/MMR";
import Buff from "../../utils/bufferutils";
import * as VDXF_Data from '../../vdxf/vdxfdatakeys';
import { mmrDescriptorForRootProof } from "../constants/fixtures";
import * as createHash from "create-hash";

describe('Calculate the correct mmrRoot is created', () => {
  test('Check the hashes hash to the root in a mmrdescriptor also check the datadescriptors create the correct hash with the salt', async () => {

    const mmrDesc = MMRDescriptor.fromJson(mmrDescriptorForRootProof.mmrdescriptor);
    const hashes = new VDXFData;
    hashes.fromBuffer(mmrDesc.mmrHashes.objectdata);

    let hashArray = new Array<Buffer>();
    if (hashes.vdxfkey == VDXF_Data.VectorUint256Key.vdxfid) {

      const reader = new Buff.BufferReader(hashes.data, 0);

      const hashCount = reader.readCompactSize();

      for (let i = 0; i < hashCount; i++) {
        const hashslice = reader.readSlice(32);
        hashArray.push(hashslice);
      }
    } else {
      throw new Error("Invalid MMR descriptor");
    }

    const mmr = new MerkleMountainRange();

    for (let i = 0; i < hashArray.length; i++) {
      const hash = hashArray[i];
      if (hash.length !== 32) {
        throw new Error("Invalid hash length in MMR");
      }
      const newNode = new MMRNode(hash);
      mmr.add(newNode);
    }

    const mmv = new MerkleMountainView(mmr);

    const mmrRoot = mmv.getRoot();

    expect(mmrRoot.toString('hex')).toBe(mmrDescriptorForRootProof.mmrdescriptor.mmrroot.objectdata);

    for (let i = 0; i < hashArray.length; i++) {

      const descriptorRaw = mmrDesc.dataDescriptors[i].toJson();

      const vdxfencoded = VdxfUniValue.fromJson(descriptorRaw.objectdata);

      const serializeddata = vdxfencoded.toBuffer();

      const saltedData = new SaltedData(serializeddata, Buffer.from(descriptorRaw.salt as string, 'hex'));

      const sha256Hash = (input) => {
        return createHash("sha256")
        .update(input)
        .digest();
      }

      const saltedDataHashed = saltedData.getHash(sha256Hash);
      expect(saltedDataHashed.toString('hex')).toBe(hashArray[i].toString('hex'));

    }

  });

});
