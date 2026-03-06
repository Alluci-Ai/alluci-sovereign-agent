import { ContentMultiMap, ContentMultiMapJson, ContentMultiMapJsonValue, KvContent } from "../../pbaas/ContentMultiMap";
import { DATA_TYPE_STRING } from "../../vdxf";
import { VDXF_UNI_VALUE_VERSION_CURRENT, VdxfUniValue } from "../../pbaas/VdxfUniValue";
import { VdxfUniType } from "../../pbaas/VdxfUniValue";
import { manyContentMultimapData } from "../constants/fixtures";

describe('Serializes and deserializes ContentMultiMap', () => {
  const vdxfunivaluedata = new Array<{ [key: string]: VdxfUniType }>;
  vdxfunivaluedata.push({ [DATA_TYPE_STRING.vdxfid]: "Test String 123454321" });

  const vdxfunivalue = new VdxfUniValue({
    values: vdxfunivaluedata,
    version: VDXF_UNI_VALUE_VERSION_CURRENT
  });

  function testContentMultimapWithKvContent(kv: KvContent) {
    const c = new ContentMultiMap({
      kv_content: kv
    });

    const cFromBuf = new ContentMultiMap();

    cFromBuf.fromBuffer(c.toBuffer());

    expect(cFromBuf.toBuffer().toString('hex')).toBe(c.toBuffer().toString('hex'));
    expect(ContentMultiMap.fromJson(c.toJson()).toBuffer().toString("hex")).toBe(cFromBuf.toBuffer().toString('hex'));
  }

  test('test CMM with vdxfunivalue content', () => {
    const kvcontent: KvContent = new Map();
    kvcontent.set("iPsFBfFoCcxtuZNzE8yxPQhXVn4dmytf8j", [vdxfunivalue]);
    testContentMultimapWithKvContent(kvcontent);
  });

  test('test CMM with array of vdxfunivalue content', () => {
    const kvcontent: KvContent = new Map();
    kvcontent.set("iPsFBfFoCcxtuZNzE8yxPQhXVn4dmytf8j", [vdxfunivalue, vdxfunivalue, vdxfunivalue, vdxfunivalue]);
    kvcontent.set("iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq", [Buffer.alloc(20).fill("h")]);
    kvcontent.set("i5v3h9FWVdRFbNHU7DfcpGykQjRaHtMqu7", [Buffer.alloc(20).fill("h"), Buffer.alloc(20).fill("h"), Buffer.alloc(20).fill("h")]);
    kvcontent.set("i81XL8ZpuCo9jmWLv5L5ikdxrGuHrrpQLz", [vdxfunivalue]);
    testContentMultimapWithKvContent(kvcontent);
  });

  test('test CMM from json', () => {
    const cmm = ContentMultiMap.fromJson(manyContentMultimapData as unknown as { [key: string]: ContentMultiMapJsonValue });

    expect(cmm.toJson()).toEqual(manyContentMultimapData);
  });
});