import varuint from '../utils/varuint'
import bufferutils from '../utils/bufferutils'
import { BigNumber } from '../utils/types/BigNumber';
import { fromBase58Check, toBase58Check } from '../utils/address';
import { HASH160_BYTE_LENGTH, HASH256_BYTE_LENGTH, I_ADDR_VERSION, VDXF_OBJECT_DEFAULT_VERSION } from '../constants/vdxf';
import { BN } from 'bn.js';
import { SerializableEntity } from '../utils/types/SerializableEntity';
import varint from '../utils/varint';
import { isHexString } from '../utils/string';
import { CurrencyValueMap } from './CurrencyValueMap';
import { Rating, RatingJson } from './Rating';
import { TransferDestination, TransferDestinationJson } from './TransferDestination';
import { ContentMultiMapRemove, ContentMultiMapRemoveJson } from './ContentMultiMapRemove';
import { CrossChainDataRef, CrossChainDataRefJson } from './CrossChainDataRef';
import { SignatureData, SignatureJsonDataInterface } from './SignatureData';
import { DataDescriptor, DataDescriptorJson } from './DataDescriptor';
import { MMRDescriptor, MMRDescriptorJson } from './MMRDescriptor';
import { Credential, CredentialJson } from './Credential';
import { URLRef } from './URLRef';
import {IdentityMultimapRef} from './IdentityMultimapRef';
import * as VDXF_Data from '../vdxf/vdxfdatakeys';

export const VDXF_UNI_VALUE_VERSION_INVALID = new BN(0, 10);
export const VDXF_UNI_VALUE_VERSION_CURRENT = new BN(1, 10);

const { BufferWriter, BufferReader } = bufferutils


export type VdxfUniType = string | Buffer | BigNumber | CurrencyValueMap | Rating |
  TransferDestination | ContentMultiMapRemove | CrossChainDataRef | SignatureData |
  DataDescriptor | MMRDescriptor | URLRef | IdentityMultimapRef | Credential;

export interface VdxfUniValueInterface {
  [key: string]: string | number | RatingJson | TransferDestinationJson |
  ContentMultiMapRemoveJson | CrossChainDataRefJson | SignatureJsonDataInterface | DataDescriptorJson | MMRDescriptorJson | VdxfUniValueInterface;
  serializedhex?: string;
  serializedbase64?: string;
  message?: string;
};

export type VdxfUniValueJson = string | VdxfUniValueInterface;

export type VdxfUniValueJsonArray = Array<VdxfUniValueJson>;

export type JsonSerializableObject = CurrencyValueMap | Rating |
  TransferDestination | ContentMultiMapRemove | CrossChainDataRef | SignatureData |
  DataDescriptor | MMRDescriptor | Credential;
// This UniValue class was adapted from C++ code for encoding JSON objects into bytes. It is not serialization and
// therefore doesn't have a fromBuffer function, as you can't reliably decode it, only encode.
export class VdxfUniValue implements SerializableEntity {
  values: Array<{ [key: string]: VdxfUniType }>;
  version: BigNumber;

  constructor(data?: { values: Array<{ [key: string]: VdxfUniType }>, version?: BigNumber }) {
    if (data?.values) this.values = data.values;
    if (data?.version) this.version = data.version;
    else this.version = VDXF_UNI_VALUE_VERSION_CURRENT;
  }

  getByteLength() {
    let length = 0;

    for (const inner of this.values) {

      const key = Object.keys(inner)[0];
      const value = inner[key];

      // if we just have serialized data 
      if (key === "") {
        length += Buffer.from(value as string, "hex").length;
        continue;
      }

      if (key == VDXF_Data.DataByteKey.vdxfid) {
        length += 1;
        continue;
      }
      else if ((key == VDXF_Data.DataUint16Key.vdxfid) || (key == VDXF_Data.DataInt16Key.vdxfid)) {
        length += 2;
        continue;
      }
      else if ((key == VDXF_Data.DataInt32Key.vdxfid) || (key == VDXF_Data.DataUint32Key.vdxfid)) {
        length += 4;
        continue;
      }
      else if (key == VDXF_Data.DataInt64Key.vdxfid) {
        length += 8;
        continue;
      }
      else if (key == VDXF_Data.DataUint160Key.vdxfid) {
        length += HASH160_BYTE_LENGTH;
        continue;
      }
      else if (key == VDXF_Data.DataUint256Key.vdxfid) {
        length += HASH256_BYTE_LENGTH;
        continue;
      }

      length += HASH160_BYTE_LENGTH;

      function totalStreamLength(bufLen: number): number {
        const encodeStreamLen = varuint.encodingLength(bufLen + varuint.encodingLength(bufLen));

        return bufLen + encodeStreamLen;
      }

      if (key == VDXF_Data.DataStringKey.vdxfid) {
        const valBuf = Buffer.from(value as string, "utf-8");
        length += varint.encodingLength(new BN(1));
        // NOTE: 3 is from ss type + ver + vdxfIdVersion 
        length += varuint.encodingLength(valBuf.length);

        length += totalStreamLength(valBuf.length);
      }
      else if (key == VDXF_Data.DataByteVectorKey.vdxfid) {
        const valBuf = Buffer.from(value as string, "hex");
        length += varint.encodingLength(new BN(1));
        length += varuint.encodingLength(valBuf.length)

        length += totalStreamLength(valBuf.length);
      }
      else if (key == VDXF_Data.DataCurrencyMapKey.vdxfid) {

        const oneCurMap = new CurrencyValueMap({...value as object, multivalue: true} as CurrencyValueMap);
        length += varint.encodingLength(new BN(1));
        length += totalStreamLength(oneCurMap.getByteLength());
      }
      else if (key == VDXF_Data.DataRatingsKey.vdxfid) {
        const oneRatingMap = new Rating(value as Rating);

        length += varint.encodingLength(oneRatingMap.version);
        length += totalStreamLength(oneRatingMap.getByteLength());
      }
      else if (key == VDXF_Data.CredentialKey.vdxfid) {
        const oneCredential = new Credential(value as Credential);
        length += varint.encodingLength(oneCredential.version);
        length += totalStreamLength(oneCredential.getByteLength());
      }
      else if (key == VDXF_Data.DataTransferDestinationKey.vdxfid) {
        const transferDest = new TransferDestination(value as TransferDestination);

        length += varint.encodingLength(transferDest.typeNoFlags());
        length += totalStreamLength(transferDest.getByteLength());
      }
      else if (key == VDXF_Data.ContentMultiMapRemoveKey.vdxfid) {
        const multiRemove = new ContentMultiMapRemove(value as ContentMultiMapRemove);

        length += varint.encodingLength(multiRemove.version);
        length += totalStreamLength(multiRemove.getByteLength());
      }
      else if (key == VDXF_Data.CrossChainDataRefKey.vdxfid) {

        const crossCh = (value as CrossChainDataRef);

        length += varint.encodingLength(VDXF_OBJECT_DEFAULT_VERSION);
        length += totalStreamLength(crossCh.getByteLength());
      }
      else if (key == VDXF_Data.DataDescriptorKey.vdxfid) {
        const descr = new DataDescriptor(value as DataDescriptor);

        length += varint.encodingLength(descr.version);
        length += totalStreamLength(descr.getByteLength());
      }
      else if (key == VDXF_Data.MMRDescriptorKey.vdxfid) {
        const descr = new MMRDescriptor(value as MMRDescriptor);

        length += varint.encodingLength(descr.version);
        length += totalStreamLength(descr.getByteLength());
      }
      else if (key == VDXF_Data.SignatureDataKey.vdxfid) {
        const sigData = new SignatureData(value as SignatureData);

        length += varint.encodingLength(sigData.version);
        length += totalStreamLength(sigData.getByteLength());
      } else {
        throw new Error("contentmap invalid or unrecognized vdxfkey for object type: " + key);
      }

    }
    return length;
  }

  toBuffer(): Buffer {
    const writer = new BufferWriter(Buffer.alloc(this.getByteLength()));

    for (const inner of this.values) {
      const key = Object.keys(inner)[0];
      const value = inner[key];

      if (key === "") {
        writer.writeSlice(value as Buffer);
        continue;
      }

      if (key == VDXF_Data.DataByteKey.vdxfid) {
        const oneByte = Buffer.from(value as string, "hex");
        if (oneByte.length != 1) {
          throw new Error("contentmap: byte data must be exactly one byte");
        }
        writer.writeSlice(oneByte);
      }
      else if (key == VDXF_Data.DataInt16Key.vdxfid) {
        const oneShort = Buffer.alloc(2);
        oneShort.writeInt16LE((value as BigNumber).toNumber());
        writer.writeSlice(oneShort);
      }
      else if (key == VDXF_Data.DataUint16Key.vdxfid) {
        const oneUShort = Buffer.alloc(2);
        oneUShort.writeUInt16LE((value as BigNumber).toNumber());
        writer.writeSlice(oneUShort);
      }
      else if (key == VDXF_Data.DataInt32Key.vdxfid) {
        const oneInt = Buffer.alloc(4);
        oneInt.writeInt32LE((value as BigNumber).toNumber());
        writer.writeSlice(oneInt);
      }
      else if (key == VDXF_Data.DataUint32Key.vdxfid) {
        const oneUInt = Buffer.alloc(4);
        oneUInt.writeUInt32LE((value as BigNumber).toNumber());
        writer.writeSlice(oneUInt);
      }
      else if (key == VDXF_Data.DataInt64Key.vdxfid) {
        const oneInt64 = Buffer.alloc(8);
        oneInt64.writeBigInt64LE(BigInt((value as BigNumber).toString()));
        writer.writeSlice(oneInt64);
      }
      else if (key == VDXF_Data.DataUint160Key.vdxfid) {
        const oneKey = fromBase58Check(value as string).hash;
        writer.writeSlice(oneKey);
      }
      else if (key == VDXF_Data.DataUint256Key.vdxfid) {
        const oneHash = Buffer.from(value as string, "hex");
        if (oneHash.length != HASH256_BYTE_LENGTH) {
          throw new Error("contentmap: hash data must be exactly 32 bytes");
        }
        writer.writeVarSlice(oneHash.reverse());
      }
      else if (key == VDXF_Data.DataStringKey.vdxfid) {

        const valBuf = Buffer.from(value as string, "utf-8");

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(new BN(1));
        writer.writeCompactSize(valBuf.length + varuint.encodingLength(valBuf.length));
        writer.writeVarSlice(valBuf);
      }
      else if (key == VDXF_Data.DataByteVectorKey.vdxfid) {

        const valBuf = Buffer.from(value as string, "hex")

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(new BN(1));
        writer.writeCompactSize(varuint.encodingLength(valBuf.length) + valBuf.length);
        writer.writeVarSlice(valBuf);
      }
      else if (key == VDXF_Data.DataCurrencyMapKey.vdxfid) {

        const oneCurMap = new CurrencyValueMap({...value as object, multivalue: true} as CurrencyValueMap)

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(new BN(1));
        writer.writeCompactSize(oneCurMap.getByteLength());
        writer.writeSlice(oneCurMap.toBuffer());
      }
      else if (key == VDXF_Data.DataRatingsKey.vdxfid) {

        const oneRatingMap = new Rating(value as Rating);

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(oneRatingMap.version);
        writer.writeCompactSize(oneRatingMap.getByteLength());
        writer.writeSlice(oneRatingMap.toBuffer());
      }

      else if (key == VDXF_Data.CredentialKey.vdxfid) {

        const oneCredential = (value as Credential);
        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(oneCredential.version);
        writer.writeCompactSize(oneCredential.getByteLength());
        writer.writeSlice(oneCredential.toBuffer());
      }

      else if (key == VDXF_Data.DataTransferDestinationKey.vdxfid) {

        const transferDest = new TransferDestination(value as TransferDestination);

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(transferDest.typeNoFlags());
        writer.writeCompactSize(transferDest.getByteLength());
        writer.writeSlice(transferDest.toBuffer());
      }
      else if (key == VDXF_Data.ContentMultiMapRemoveKey.vdxfid) {

        const transferDest = new ContentMultiMapRemove(value as ContentMultiMapRemove);

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(transferDest.version);
        writer.writeCompactSize(transferDest.getByteLength());
        writer.writeSlice(transferDest.toBuffer());
      }
      else if (key == VDXF_Data.CrossChainDataRefKey.vdxfid) {

        const transferDest = (value as CrossChainDataRef);

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(VDXF_OBJECT_DEFAULT_VERSION);
        writer.writeCompactSize(transferDest.getByteLength());
        writer.writeSlice(transferDest.toBuffer());
      }
      else if (key == VDXF_Data.DataDescriptorKey.vdxfid) {

        const descr = new DataDescriptor(value as DataDescriptor);

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(descr.version);
        writer.writeCompactSize(descr.getByteLength());
        writer.writeSlice(descr.toBuffer());
      }
      else if (key == VDXF_Data.MMRDescriptorKey.vdxfid) {

        const descr = new MMRDescriptor(value as MMRDescriptor);

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(descr.version);
        writer.writeCompactSize(descr.getByteLength());
        writer.writeSlice(descr.toBuffer());
      }
      else if (key == VDXF_Data.SignatureDataKey.vdxfid) {

        const sigData = new SignatureData(value as SignatureData);

        writer.writeSlice(fromBase58Check(key).hash);
        writer.writeVarInt(sigData.version);
        writer.writeCompactSize(sigData.getByteLength());
        writer.writeSlice(sigData.toBuffer());
      } else {
        throw new Error("contentmap invalid or unrecognized vdxfkey for object type: " + key);
      }

    }

    return writer.buffer;
  }

  fromBuffer(buffer: Buffer, offset: number = 0): number {
    const reader = new BufferReader(buffer, offset);

    this.values = [];

    let bytesLeft = reader.buffer.length - reader.offset;

    while (bytesLeft > HASH160_BYTE_LENGTH) // size of uint160
    {
      let pSuccess = { value: false };
      let objectUni: { key: string, value: VdxfUniType };
      const initialOffset = reader.offset;

      try {
        let checkVal: string;
        let version = new BN(0);
        let objSize = 0;
        checkVal = toBase58Check(reader.readSlice(HASH160_BYTE_LENGTH), I_ADDR_VERSION);

        if (checkVal == VDXF_Data.DataCurrencyMapKey.vdxfid) {
          const oneCurrencyMap = new CurrencyValueMap({ multivalue: true });
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = oneCurrencyMap.fromBuffer(reader.buffer, reader.offset);
          if (oneCurrencyMap.isValid()) {
            objectUni = { key: checkVal, value: oneCurrencyMap };
          }
        }
        else if (checkVal == VDXF_Data.DataRatingsKey.vdxfid) {
          const oneRatingObj = new Rating();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = oneRatingObj.fromBuffer(reader.buffer, reader.offset);
          if (oneRatingObj.isValid()) {
            objectUni = { key: checkVal, value: oneRatingObj };
          }
        }
        else if (checkVal == VDXF_Data.CredentialKey.vdxfid) {
          const credentialObj = new Credential();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = credentialObj.fromBuffer(reader.buffer, reader.offset);
          if (credentialObj.isValid()) {
            objectUni = { key: checkVal, value: credentialObj };
          }
        }
        else if (checkVal == VDXF_Data.DataTransferDestinationKey.vdxfid) {
          const oneTransferDest = new TransferDestination();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = oneTransferDest.fromBuffer(reader.buffer, reader.offset);
          if (oneTransferDest.isValid()) {
            objectUni = { key: checkVal, value: oneTransferDest };
          }
        }
        else if (checkVal == VDXF_Data.ContentMultiMapRemoveKey.vdxfid) {
          const contentMap = new ContentMultiMapRemove();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = contentMap.fromBuffer(reader.buffer, reader.offset);
          if (contentMap.isValid()) {
            objectUni = { key: checkVal, value: contentMap };
          }
        }
        else if (checkVal == VDXF_Data.DataStringKey.vdxfid) {
          let stringVal: string;
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          stringVal = reader.readVarSlice().toString('utf8');
          objectUni = { key: checkVal, value: stringVal };
        }
        else if (checkVal == VDXF_Data.DataByteVectorKey.vdxfid) {
          let vecVal: Buffer;
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          vecVal = reader.readVarSlice();
          objectUni = { key: checkVal, value: vecVal.toString('hex') };
        }
        else if (checkVal == VDXF_Data.CrossChainDataRefKey.vdxfid) {
          const dataRef = new CrossChainDataRef();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = dataRef.fromBuffer(reader.buffer, reader.offset);
          if (dataRef.isValid()) {
            objectUni = { key: checkVal, value: dataRef };
          }
        }
        else if (checkVal == VDXF_Data.DataDescriptorKey.vdxfid) {
          const dataDescriptor = new DataDescriptor();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = dataDescriptor.fromBuffer(reader.buffer, reader.offset);
          if (dataDescriptor.isValid()) {
            objectUni = { key: checkVal, value: dataDescriptor };
          }
        }
        else if (checkVal == VDXF_Data.MMRDescriptorKey.vdxfid) {
          const mmrDescriptor = new MMRDescriptor();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = mmrDescriptor.fromBuffer(reader.buffer, reader.offset);
          if (mmrDescriptor.isValid()) {
            objectUni = { key: checkVal, value: mmrDescriptor };
          }
        }
        else if (checkVal == VDXF_Data.SignatureDataKey.vdxfid) {
          const sigData = new SignatureData();
          version = reader.readVarInt();
          objSize = reader.readCompactSize();
          reader.offset = sigData.fromBuffer(reader.buffer, reader.offset);
          if (sigData.isValid()) {
            objectUni = { key: checkVal, value: sigData };
          }
        }

        // if we have an object that we recognized, encode it
        if (objectUni && objectUni.key && objectUni.value) {
          if (pSuccess != null) {
            pSuccess.value = true;
          }
        }
        else {
          if (pSuccess != null) {
            pSuccess.value = false;
          }
        }
      }
      catch (e) {
        if (pSuccess != null) {
          pSuccess.value = false;
        }
      }

      bytesLeft = reader.buffer.length - reader.offset;

      if (pSuccess?.value && pSuccess?.value) {
        this.values.push({ [objectUni.key]: objectUni.value });
      }
      else {
        // add the remaining data as a hex string
        reader.offset = initialOffset;
        this.values.push({ [""]: reader.readSlice(reader.buffer.length - reader.offset) });
        bytesLeft = 0;
        break;
      }
    }
    if (bytesLeft && bytesLeft <= HASH160_BYTE_LENGTH) {
      this.values.push({ [""]: reader.readSlice(bytesLeft) });
    }
    return reader.offset;
  }

  static fromJson(obj): VdxfUniValue {
    const arrayItem = new Array<{ [key: string]: VdxfUniType }>;

    if (!Array.isArray(obj)) {
      if (typeof (obj) != 'object') {
        if (typeof (obj) != 'string') throw new Error('Not JSON string as expected');
        if (isHexString(obj)) {
          arrayItem.push({ [""]: Buffer.from(obj, "hex") })
          return new VdxfUniValue({
            values: arrayItem
          });
        }
        arrayItem.push({ [""]: Buffer.from(obj, "utf-8") })
        return new VdxfUniValue({
          values: arrayItem
        });
      }

      if (obj.serializedhex) {
        if (!isHexString(obj.serializedhex)) {
          throw new Error("contentmap: If the \"serializedhex\" key is present, it's data must be only valid hex and complete");
        }
        arrayItem.push({ [""]: Buffer.from(obj.serializedhex, "hex") })
        return new VdxfUniValue({
          values: arrayItem
        });
      }

      if (obj.serializedbase64) {
        try {
          arrayItem.push({ [""]: Buffer.from(obj.serializedbase64, "base64") })
          return new VdxfUniValue({
            values: arrayItem
          });
        } catch (e) {
          throw new Error("contentmap: If the \"serializedbase64\" key is present, it's data must be only valid base64 and complete");
        }
      }

      if (obj.message) {
        arrayItem.push({ [""]: Buffer.from(obj.message, "utf-8") })
        return new VdxfUniValue({
          values: arrayItem
        });
      }
    }

    if (!Array.isArray(obj)) {
      obj = [obj];
    }

    // this should be an object with "vdxfkey" as the key and {object} as the json object to serialize
    for (let i = 0; i < obj.length; i++) {

      if (typeof (obj[i]) != 'object') {
        if (typeof (obj[i]) != 'string') throw new Error('Not JSON string as expected');
        if (isHexString(obj[i] as string)) {
          arrayItem.push({ [""]: Buffer.from(obj[i] as string, "hex") })
          continue;
        }
        arrayItem.push({ [""]: Buffer.from(obj[i] as string, "utf-8") })
        continue;
      }

      const oneValKeys = Object.keys(obj[i]);
      const oneValValues = Object.values(obj[i]);

      for (let k = 0; k < oneValKeys.length; k++) {
        const objTypeKey = oneValKeys[k];
        if (objTypeKey == VDXF_Data.DataByteKey.vdxfid) {

          const oneByte = Buffer.from(oneValValues[k] as string, "hex");
          if (oneByte.length != 1) {
            throw new Error("contentmap: byte data must be exactly one byte");
          }
          arrayItem.push({ [objTypeKey]: oneByte });
        }
        else if (objTypeKey == VDXF_Data.DataInt16Key.vdxfid) {
          const oneShort = Buffer.alloc(2);
          oneShort.writeInt16LE(oneValValues[k] as number);
          arrayItem.push({ [objTypeKey]: oneShort });
        }
        else if (objTypeKey == VDXF_Data.DataUint16Key.vdxfid) {
          const oneUShort = Buffer.alloc(2);
          oneUShort.writeUInt16LE(oneValValues[k] as number);
          arrayItem.push({ [objTypeKey]: oneUShort });
        }
        else if (objTypeKey == VDXF_Data.DataInt32Key.vdxfid) {
          const oneInt = Buffer.alloc(4);
          oneInt.writeInt32LE(oneValValues[k] as number);
          arrayItem.push({ [objTypeKey]: oneInt });

        }
        else if (objTypeKey == VDXF_Data.DataUint32Key.vdxfid) {
          const oneUInt = Buffer.alloc(4);
          oneUInt.writeUInt32LE(oneValValues[k] as number);
          arrayItem.push({ [objTypeKey]: oneUInt });
        }
        else if (objTypeKey == VDXF_Data.DataInt64Key.vdxfid) {
          const oneInt64 = Buffer.alloc(8);
          oneInt64.writeIntLE(oneValValues[k] as number, 0, 8);
          arrayItem.push({ [objTypeKey]: oneInt64 });
        }
        else if (objTypeKey == VDXF_Data.DataUint160Key.vdxfid) {
          fromBase58Check(oneValValues[k] as string).hash;
          arrayItem.push({ [objTypeKey]: oneValValues[k] as string });
        }
        else if (objTypeKey == VDXF_Data.DataUint256Key.vdxfid) {
          const oneHash = Buffer.from(oneValValues[k] as string, "hex");
          if (oneHash.length != HASH256_BYTE_LENGTH) {
            throw new Error("contentmap: hash data must be exactly 32 bytes");
          }
          arrayItem.push({ [objTypeKey]: oneHash });
        }
        else if (objTypeKey == VDXF_Data.DataStringKey.vdxfid) {
          arrayItem.push({ [objTypeKey]: oneValValues[k] as string });
        }
        else if (objTypeKey == VDXF_Data.DataByteVectorKey.vdxfid) {

          if (!isHexString(oneValValues[k] as string)) {
            throw new Error("contentmap: bytevector data must be valid hex");
          }

          arrayItem.push({ [objTypeKey]: Buffer.from(oneValValues[k] as string, "hex") });

        }
        else if (objTypeKey == VDXF_Data.DataCurrencyMapKey.vdxfid) {

          const oneCurMap = CurrencyValueMap.fromJson(oneValValues[k] as {[key: string]: string}, true);
          arrayItem.push({ [objTypeKey]: oneCurMap });

        }
        else if (objTypeKey == VDXF_Data.DataRatingsKey.vdxfid) {

          const oneRatingMap = Rating.fromJson(oneValValues[k] as RatingJson);
          arrayItem.push({ [objTypeKey]: oneRatingMap });

        }
        else if (objTypeKey == VDXF_Data.DataTransferDestinationKey.vdxfid) {

          const transferDest = TransferDestination.fromJson(oneValValues[k] as TransferDestinationJson);
          arrayItem.push({ [objTypeKey]: transferDest });

        }
        else if (objTypeKey == VDXF_Data.ContentMultiMapRemoveKey.vdxfid) {

          const content = ContentMultiMapRemove.fromJson(oneValValues[k] as ContentMultiMapRemoveJson);
          arrayItem.push({ [objTypeKey]: content });

        }
        else if (objTypeKey == VDXF_Data.CrossChainDataRefKey.vdxfid) {

          const crossChainRefKey = CrossChainDataRef.fromJson(oneValValues[k] as CrossChainDataRefJson);
          arrayItem.push({ [objTypeKey]: crossChainRefKey });

        }
        else if (objTypeKey == VDXF_Data.DataDescriptorKey.vdxfid) {

          const descriptor = DataDescriptor.fromJson(oneValValues[k]);
          arrayItem.push({ [objTypeKey]: descriptor });

        }
        else if (objTypeKey == VDXF_Data.MMRDescriptorKey.vdxfid) {

          const mmrDescriptor = MMRDescriptor.fromJson(oneValValues[k] as MMRDescriptorJson);
          arrayItem.push({ [objTypeKey]: mmrDescriptor });

        }
        else if (objTypeKey == VDXF_Data.SignatureDataKey.vdxfid) {

          const sigData = SignatureData.fromJson(oneValValues[k]);
          arrayItem.push({ [objTypeKey]: sigData });

        }
        else if (objTypeKey == VDXF_Data.CredentialKey.vdxfid) {

          const oneCredential = Credential.fromJson(oneValValues[k] as CredentialJson);
          arrayItem.push({ [objTypeKey]: oneCredential });

        }  
        else {
          throw new Error("Unknown vdxfkey: " + oneValValues[k]);
        }
      }
    }
    return new VdxfUniValue({
      values: arrayItem
    })
  }

  toJson(): VdxfUniValueJsonArray | VdxfUniValueJson {
    let ret = [];

    for (const inner of this.values) {

      const key = Object.keys(inner)[0];
      const value = inner[key];

      if (key === "" && Buffer.isBuffer(value)) {
        ret.push((value as Buffer).toString('hex'));
      } else if (Buffer.isBuffer(value)) {
        ret.push({ [key]: (value as Buffer).toString('hex') });
      } else if (typeof(value) === 'string') {
        ret.push({ [key]: value });
      } else if (value instanceof BN) {
        ret.push({ [key]: (value as BigNumber).toString(10) });
      } else {
        ret.push({ [key]: (value as JsonSerializableObject).toJson() });
      }
    }

    if (ret && ret.length == 1) {
      return ret[0];
    }

    return ret;
  }

}