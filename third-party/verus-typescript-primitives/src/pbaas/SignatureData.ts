import varint from '../utils/varint'
import varuint from '../utils/varuint'
import { fromBase58Check, toBase58Check } from "../utils/address";
import bufferutils from '../utils/bufferutils'
import { BN } from 'bn.js';
import { BigNumber } from '../utils/types/BigNumber';
import { HASH160_BYTE_LENGTH, I_ADDR_VERSION } from '../constants/vdxf';
import { SerializableEntity } from '../utils/types/SerializableEntity';
import { EHashTypes } from './DataDescriptor';
const { BufferReader, BufferWriter } = bufferutils
const createHash = require("create-hash");
import { VERUS_DATA_SIGNATURE_PREFIX } from "../constants/vdxf";

export interface SignatureJsonDataInterface {
  version: number;
  systemid: string;
  hashtype: number;
  signaturehash: string;
  identityid: string;
  signaturetype: number;
  vdxfkeys?: Array<string>;
  vdxfkeynames?: Array<string>;
  boundhashes?: Array<string>;
  signature: string;
}

export class SignatureData implements SerializableEntity {
  version: BigNumber;
  system_ID: string;
  hash_type: BigNumber;
  signature_hash: Buffer;
  identity_ID: string;
  sig_type: BigNumber;
  vdxf_keys: Array<string>;
  vdxf_key_names: Array<string>;
  bound_hashes: Array<Buffer>;
  signature_as_vch: Buffer;

  static VERSION_INVALID = new BN(0);
  static FIRST_VERSION = new BN(1);
  static LAST_VERSION = new BN(1);
  static DEFAULT_VERSION = new BN(1);
  static TYPE_VERUSID_DEFAULT = new BN(1);

  constructor(data?: { version?: BigNumber, system_ID?: string, hash_type?: BigNumber, signature_hash?: Buffer, 
    identity_ID?: string, sig_type?: BigNumber, vdxf_keys?: Array<string>, vdxf_key_names?: Array<string>, 
    bound_hashes?: Array<Buffer>, signature_as_vch?: Buffer }) {

    if (data) {
      this.version = data.version || new BN(1, 10);
      this.system_ID = data.system_ID || "";
      this.hash_type = data.hash_type || new BN(0);
      this.signature_hash = data.signature_hash || Buffer.alloc(0);
      this.identity_ID = data.identity_ID || "";
      this.sig_type = data.sig_type || new BN(0);
      this.vdxf_keys = data.vdxf_keys || [];
      this.vdxf_key_names = data.vdxf_key_names || [];
      this.bound_hashes = data.bound_hashes || [];
      this.signature_as_vch = data.signature_as_vch || Buffer.alloc(0);
    }
  }

  static fromJson(data: SignatureJsonDataInterface | any) {

    const signatureData = new SignatureData();

    if (data) {
      signatureData.version = new BN(data.version);
      signatureData.system_ID = data.systemid;
      signatureData.hash_type = new BN(data.hashtype);
      signatureData.identity_ID = data.identityid;
      signatureData.sig_type = new BN(data.signaturetype);

      if (signatureData.hash_type.eq(new BN(Number(EHashTypes.HASH_SHA256)))) {
        signatureData.signature_hash = Buffer.from(data.signaturehash, 'hex');
      } else {
        signatureData.signature_hash = Buffer.from(data.signaturehash, 'hex').reverse();
      }

      signatureData.signature_as_vch = Buffer.from(data.signature, 'base64');
      signatureData.vdxf_keys = data.vdxfkeys || [];
      signatureData.vdxf_key_names = data.vdxfkeynames || [];
      signatureData.bound_hashes = data.boundhashes?.map((hash) => Buffer.from(hash, 'hex').reverse()) || [];

    }

    return signatureData;
  }

  /**
   * Determines the signature hash type based on the input buffer.
   * 
   * @param {Buffer} input - The input buffer containing signature data.
   * @returns {number} - The hash type. If the version byte is `2`, the next byte
   *                     in the buffer is returned as the hash type. Otherwise,
   *                     it defaults to `EHashTypes.HASH_SHA256`.
   * 
   * The method reads the first byte of the input buffer as the version. If the
   * version is `2`, it reads the next byte as the hash type. This logic is used
   * to support multiple versions of signature data formats, where version `2`
   * introduces a new hash type. For all other versions, the default hash type
   * is `EHashTypes.HASH_SHA256`.
   */
  static getSignatureHashType(input: Buffer) {

    var bufferReader = new bufferutils.BufferReader(input, 0);
    let version = bufferReader.readUInt8();
    if (version === 2)
      return bufferReader.readUInt8();
    else
      return EHashTypes.HASH_SHA256;
  }

  getByteLength() {
    let byteLength = 0;

    byteLength += varint.encodingLength(this.version);
    byteLength += HASH160_BYTE_LENGTH; // system_ID uint160
    byteLength += varint.encodingLength(this.hash_type);
    byteLength += varuint.encodingLength(this.signature_hash.length);
    byteLength += this.signature_hash.length;
    byteLength += HASH160_BYTE_LENGTH; // identity_ID uint160
    byteLength += varint.encodingLength(this.sig_type);
    byteLength += varuint.encodingLength(this.vdxf_keys.length);
    byteLength += this.vdxf_keys.length * 20;
    byteLength += varuint.encodingLength(this.vdxf_key_names.length);

    for (const keyName of this.vdxf_key_names) {
      byteLength += varuint.encodingLength(Buffer.from(keyName, 'utf8').length);
      byteLength += Buffer.from(keyName, 'utf8').length;
    }

    byteLength += varuint.encodingLength(this.bound_hashes.length);
    byteLength += this.bound_hashes.length * 32;
    byteLength += varuint.encodingLength(this.signature_as_vch.length);
    byteLength += this.signature_as_vch.length;

    return byteLength
  }

  toBuffer() {
    const bufferWriter = new BufferWriter(Buffer.alloc(this.getByteLength()))

    bufferWriter.writeVarInt(this.version);
    bufferWriter.writeSlice(fromBase58Check(this.system_ID).hash);
    bufferWriter.writeVarInt(this.hash_type);
    bufferWriter.writeVarSlice(this.signature_hash);
    bufferWriter.writeSlice(fromBase58Check(this.identity_ID).hash);
    bufferWriter.writeVarInt(this.sig_type);
    bufferWriter.writeCompactSize(this.vdxf_keys.length);

    for (const key of this.vdxf_keys) {
      bufferWriter.writeSlice(fromBase58Check(key).hash);
    }

    bufferWriter.writeCompactSize(this.vdxf_key_names.length);
    for (const keyName of this.vdxf_key_names) {
      bufferWriter.writeVarSlice(Buffer.from(keyName, 'utf8'));
    }
    bufferWriter.writeCompactSize(this.bound_hashes.length);
    for (const boundHash of this.bound_hashes) {
      bufferWriter.writeSlice(boundHash);
    }
    bufferWriter.writeVarSlice(this.signature_as_vch);

    return bufferWriter.buffer
  }

  fromBuffer(buffer: Buffer, offset: number = 0) {
    const reader = new BufferReader(buffer, offset);

    this.version = reader.readVarInt();
    this.system_ID = toBase58Check(reader.readSlice(20), I_ADDR_VERSION);
    this.hash_type = reader.readVarInt();
    this.signature_hash = reader.readVarSlice();
    this.identity_ID = toBase58Check(reader.readSlice(20), I_ADDR_VERSION);
    this.sig_type = reader.readVarInt();
    const vdxfKeysLength = reader.readCompactSize();
    this.vdxf_keys = [];

    for (let i = 0; i < vdxfKeysLength; i++) {
      this.vdxf_keys.push(toBase58Check(reader.readSlice(20), I_ADDR_VERSION));
    }

    const vdxfKeyNamesLength = reader.readCompactSize();
    this.vdxf_key_names = [];

    for (let i = 0; i < vdxfKeyNamesLength; i++) {
      this.vdxf_key_names.push(reader.readVarSlice().toString('utf8'));
    }

    const boundHashesLength = reader.readCompactSize();
    this.bound_hashes = [];

    for (let i = 0; i < boundHashesLength; i++) {
      this.bound_hashes.push(reader.readSlice(32));
    }

    this.signature_as_vch = reader.readVarSlice();

    return reader.offset;
  }

  isValid() {
    return !!(this.version.gte(SignatureData.FIRST_VERSION) &&
      this.version.lte(SignatureData.LAST_VERSION) &&
      this.system_ID);
  }

  toJson(): SignatureJsonDataInterface {

    const returnObj: SignatureJsonDataInterface = {
      version: this.version.toNumber(),
      systemid: this.system_ID,
      hashtype: this.hash_type.toNumber(),
      signaturehash: '', // Will be set below
      identityid: this.identity_ID,
      signaturetype: this.sig_type.toNumber(),
      signature: this.signature_as_vch.toString('base64')
    };

    if (this.hash_type.eq(new BN(Number(EHashTypes.HASH_SHA256)))) {
      returnObj.signaturehash = Buffer.from(this.signature_hash).toString('hex');
    } else {
      returnObj.signaturehash = Buffer.from(this.signature_hash).reverse().toString('hex');
    }

    if (this.vdxf_keys && this.vdxf_keys.length > 0) {
      returnObj.vdxfkeys = this.vdxf_keys;
    }

    if (this.vdxf_key_names && this.vdxf_key_names.length > 0) {
      returnObj.vdxfkeynames = this.vdxf_key_names;
    }

    if (this.bound_hashes && this.bound_hashes.length > 0) {
      returnObj.boundhashes = this.bound_hashes.map((hash) => Buffer.from(hash).reverse().toString('hex'));
    }

    return returnObj;
  }

  // To fully implement, refer to VerusCoin/src/pbaas/crosschainrpc.cpp line 337, IdentitySignatureHash
  // missing bound hashes and vdxf keys
  getIdentityHash(sigObject: { version: number, hash_type: number, height: number }): Buffer<ArrayBufferLike> {
    var heightBuffer = Buffer.allocUnsafe(4)
    heightBuffer.writeUInt32LE(sigObject.height);

    if (sigObject.hash_type != Number(EHashTypes.HASH_SHA256)) {
      throw new Error("Invalid signature type for identity hash");
    }

    if (sigObject.version == 1) {
      return createHash("sha256")
        .update(VERUS_DATA_SIGNATURE_PREFIX)
        .update(fromBase58Check(this.system_ID).hash)
        .update(heightBuffer)
        .update(fromBase58Check(this.identity_ID).hash)
        .update(this.signature_hash)
        .digest();
    } else {
      return createHash("sha256")
        .update(fromBase58Check(this.system_ID).hash)
        .update(heightBuffer)
        .update(fromBase58Check(this.identity_ID).hash)
        .update(VERUS_DATA_SIGNATURE_PREFIX)
        .update(this.signature_hash)
        .digest();
    }
  }
}