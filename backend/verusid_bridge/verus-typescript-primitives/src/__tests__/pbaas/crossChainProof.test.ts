import { CrossChainProof } from '../../pbaas/CrossChainProof';
import { chainobjectsjsonobj, CrossChainProofjsonob } from "../constants/fixtures";
import * as VDXF_Data from '../../vdxf/vdxfdatakeys';
import { VdxfUniValue } from "../../pbaas/VdxfUniValue";
import { DataDescriptor } from '../../pbaas';

describe('CrossChainProof', () => {

  test('deserialize crosschainproof data', () => {
    const testrun = () => {

      const CrossChainProofhexdata = "01000000010a0001010108a2ebb2c55f83a8e2a426a53320ed4d42124f4da408a2ebb2c55f83a8e2a426a53320ed4d42124f4d018e01056ad69c87487592c161133433da3e3231483f63ef87888ca187baae4c5c078bf07ac69953b003076f5dccff0fcea0aa24d00ef79010efb4b4985dbf1d857439de6890604757529c94030042845b5e787ae2eeb7890ae9b16437c551bf273fc883012ff238f97b4c96a75087207482423ffa5f03d55e3bd941fd6f7f488584e12662c299d0a5d20c4069c5b51a"

      const innerDataDescriptor ={"i4GC1YGEVD21afWudGoFJVdnfjJ5XWnCQv":{"version":1,"flags":5,"objectdata":"d69c87487592c161133433da3e3231483f63ef87888ca187baae4c5c078bf07ac69953b003076f5dccff0fcea0aa24d00ef79010efb4b4985dbf1d857439de6890604757529c94030042845b5e787ae2eeb7890ae9b16437c551bf273fc883012ff238f97b4c96a75087","epk":"7482423ffa5f03d55e3bd941fd6f7f488584e12662c299d0a5d20c4069c5b51a"}};
      const crosschobj = new CrossChainProof();

      crosschobj.fromBuffer(Buffer.from(CrossChainProofhexdata, 'hex'));

      const crossChainProofObject = CrossChainProof.fromJson(chainobjectsjsonobj);

      const dataDesc = new VdxfUniValue();
      
      dataDesc.fromBuffer(crosschobj.chain_objects[0].data_vec);

      const dataDescriptorJson = dataDesc.toJson();

      expect(dataDescriptorJson).toEqual(innerDataDescriptor);
      expect(crossChainProofObject.chain_objects[0].vdxfd).toEqual(VDXF_Data.DataDescriptorKey.vdxfid);
      expect(crosschobj.chain_objects[0].vdxfd).toEqual(VDXF_Data.DataDescriptorKey.vdxfid)
      expect(crosschobj.toBuffer().toString('hex')).toBe(crossChainProofObject.toBuffer().toString('hex'));

    }

    testrun();
  });

});