import varint from '../utils/varint'
import varuint from '../utils/varuint'
import { fromBase58Check, toBase58Check } from "../utils/address";
import bufferutils from '../utils/bufferutils'
import { BN } from 'bn.js';
import { BigNumber } from '../utils/types/BigNumber';
import { HASH160_BYTE_LENGTH, I_ADDR_VERSION } from '../constants/vdxf';
import { SerializableEntity } from '../utils/types/SerializableEntity';
const { BufferReader, BufferWriter } = bufferutils
import { bnToDecimal, decimalToBn } from '../utils/numberConversion';
export class CurrencyValueMap implements SerializableEntity {
  value_map: Map<string, BigNumber>;
  multivalue: boolean;

  constructor(data: { value_map?: Map<string, BigNumber>, multivalue?: boolean } = {}) {
    this.value_map = new Map(data.value_map || []);
    this.multivalue = !!(data.multivalue);
  }

  getNumValues() {
    return new BN(this.value_map.size, 10)
  }

  getByteLength() {
    let byteLength = 0;

    if (this.multivalue) {
      byteLength += varuint.encodingLength(this.value_map.size)
    }

    for (const [key, value] of this.value_map) {
      byteLength += HASH160_BYTE_LENGTH
      byteLength += this.multivalue ? 8 : varint.encodingLength(value)
    }

    return byteLength
  }

  toBuffer() {
    const bufferWriter = new BufferWriter(Buffer.alloc(this.getByteLength()))
    
    if (this.multivalue) {
      const entries: Array<{ [key: string]: BigNumber }> = [];
   
      bufferWriter.writeCompactSize(this.value_map.size);
      // Convert entries to array with [Buffer, BigNumber]
      for (const [key, value] of this.value_map) {
        const { hash } = fromBase58Check(key);
        entries.push({ [hash.toString('hex')]: value });
      }

      // Sort by Buffer (vkey) value, smallest first
      entries.sort((a, b) => {
        const aKey = Object.keys(a)[0];
        const bKey = Object.keys(b)[0];
        const aBuf = Buffer.from(aKey, 'hex');
        const bBuf = Buffer.from(bKey, 'hex');
        return aBuf.compare(bBuf);
      });

      for (const value of entries) {
        const key = Object.keys(value)[0];
        const innervalue = value[key];
   
        bufferWriter.writeSlice(Buffer.from(key, 'hex'));
        bufferWriter.writeInt64(innervalue); 
      }

    } else {

      for (const [key, value] of this.value_map) {
        const { hash } = fromBase58Check(key);
  
        bufferWriter.writeSlice(hash);
        bufferWriter.writeVarInt(value);
      }
    }

    return bufferWriter.buffer
  }

  fromBuffer(buffer: Buffer, offset: number = 0) {
    const reader = new BufferReader(buffer, offset);
    let count: number;

    if (this.multivalue) {
      count = reader.readCompactSize();
    } else {
      count = 1;
    }

    for (let i = 0; i < count; i++) {
      const hash = reader.readSlice(20)
      const value = this.multivalue ? reader.readInt64() : reader.readVarInt()

      const base58Key = toBase58Check(hash, I_ADDR_VERSION)

      this.value_map.set(base58Key, value)
    }

    return reader.offset;
  }

  isValid(): boolean {
    for (let [key, value] of this.value_map) {
      if (!key || (typeof (key) == 'string' && key.length == 0)) {
        return false;
      }
    }
    return true;
  }

  toJson() {
    const value_map: { [key: string]: string } = {};

    for (let [key, value] of this.value_map) {
      value_map[key] = bnToDecimal(value)
    }

    return value_map;

  }

  static fromJson(data: { [key: string]: string }, multivalue: boolean = false): CurrencyValueMap {
    const value_map = new Map<string, BigNumber>();

    // Object.entries preserves the insertion order of the object's keys
    // If the input object is created with insertion order in mind, this will preserve it
    for (const key of Object.keys(data)) {
      value_map.set(key, decimalToBn(data[key]));
    }

    return new CurrencyValueMap({ value_map, multivalue });
  }
}