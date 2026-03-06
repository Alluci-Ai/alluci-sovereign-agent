import { VDXFObject, LOGIN_CONSENT_CONTEXT_VDXF_KEY } from "..";
import { HASH160_BYTE_LENGTH, I_ADDR_VERSION } from "../../constants/vdxf";
import { fromBase58Check, toBase58Check } from "../../utils/address";
import bufferutils from "../../utils/bufferutils";
import varuint from "../../utils/varuint";

export class Context extends VDXFObject {
  kv: { [key: string]: string };

  constructor(
    kv: { [key: string]: string } = {},
    vdxfkey: string = LOGIN_CONSENT_CONTEXT_VDXF_KEY.vdxfid
  ) {
    super(vdxfkey);

    this.kv = kv;
  }

  dataByteLength(): number {
    let length = 0;

    const keys = Object.keys(this.kv);

    length += varuint.encodingLength(keys.length);

    for (const key of keys) {
      const value = this.kv[key];

      if (value != null) {
        const valueBuf = Buffer.from(value, "utf-8");

        length += fromBase58Check(key).hash.length;
        length += valueBuf.length + varuint.encodingLength(valueBuf.length);
      }
    }

    return length;
  }

  toDataBuffer(): Buffer {
    const buffer = Buffer.alloc(this.dataByteLength());
    const writer = new bufferutils.BufferWriter(buffer);
    const keys = Object.keys(this.kv);

    writer.writeCompactSize(keys.length);

    for (const key of Object.keys(this.kv)) {
      const value = this.kv[key];
      const valueBuf = Buffer.from(value, "utf-8");

      writer.writeSlice(fromBase58Check(key).hash);
      writer.writeVarSlice(valueBuf);
    }

    return writer.buffer;
  }

  fromDataBuffer(buffer: Buffer, offset?: number): number {
    const reader = new bufferutils.BufferReader(buffer, offset);
    const contextLength = reader.readCompactSize();

    if (contextLength == 0) {
      this.kv = {};
      return reader.offset;
    } else {
      const numKeys = reader.readCompactSize();

      for (let i = 0; i < numKeys; i++) {
        this.kv[
          toBase58Check(reader.readSlice(HASH160_BYTE_LENGTH), I_ADDR_VERSION)
        ] = reader.readVarSlice().toString("utf-8");
      }

      return reader.offset;
    }
  }

  toJson() {
    return {
      kv: this.kv,
      vdxfkey: this.vdxfkey,
    };
  }
}