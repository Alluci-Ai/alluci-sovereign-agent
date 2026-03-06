import {
  LOGIN_CONSENT_REQUEST_VDXF_KEY,
  WALLET_VDXF_KEY,
  VERUSPAY_INVOICE_VDXF_KEY,
  VDXFObject,
  VerusIDSignature,
  VerusIDSignatureInterface,
  VerusIDSignatureJson,
} from "../../";
import { IDENTITY_AUTH_SIG_VDXF_KEY } from "../../keys";
import { Hash160 } from "./../Hash160";
import bufferutils from "../../../utils/bufferutils";
import { HASH160_BYTE_LENGTH, I_ADDR_VERSION, R_ADDR_VERSION, VERUS_DATA_SIGNATURE_PREFIX } from "../../../constants/vdxf";
import { fromBase58Check, toBase58Check } from "../../../utils/address";
import createHash = require("create-hash");
import base64url from "base64url";
import { VerusPayInvoiceDetails, VerusPayInvoiceDetailsJson } from "./VerusPayInvoiceDetails";
import { BN } from 'bn.js';
import { BigNumber } from "../../../utils/types/BigNumber";
import { 
  VERUSPAY_VERSION_CURRENT, 
  VERUSPAY_VERSION_FIRSTVALID, 
  VERUSPAY_VERSION_LASTVALID, 
  VERUSPAY_VERSION_MASK, 
  VERUSPAY_VERSION_SIGNED 
} from "../../../constants/vdxf/veruspay";

export interface VerusPayInvoiceInterface {
  details: VerusPayInvoiceDetails;
  system_id?: string;
  signing_id?: string;
  signature?: VerusIDSignatureInterface;
  version?: BigNumber;
}

export type VerusPayInvoiceJson = {
  vdxfkey: string,
  details: VerusPayInvoiceDetailsJson;
  system_id?: string;
  signing_id?: string;
  signature?: VerusIDSignatureJson;
  version: string
}

export class VerusPayInvoice extends VDXFObject {
  system_id: string;
  signing_id: string;
  signature?: VerusIDSignature;
  details: VerusPayInvoiceDetails;

  constructor(
    request: VerusPayInvoiceInterface = {
      details: new VerusPayInvoiceDetails(),
    }
  ) {
    super(VERUSPAY_INVOICE_VDXF_KEY.vdxfid);

    this.system_id = request.system_id;
    this.signing_id = request.signing_id;
    this.signature = request.signature
      ? new VerusIDSignature(
          request.signature,
          IDENTITY_AUTH_SIG_VDXF_KEY,
          false
        )
      : undefined;

    if (request.version) this.version = request.version;
    else this.version = VERUSPAY_VERSION_CURRENT;

    this.details = new VerusPayInvoiceDetails(request.details, this.getVersionNoFlags());
  }

  getVersionNoFlags(): BigNumber {
    return this.version.and(VERUSPAY_VERSION_MASK.notn(VERUSPAY_VERSION_MASK.bitLength()))
  }

  isValidVersion(): boolean {
    return this.getVersionNoFlags().gte(VERUSPAY_VERSION_FIRSTVALID) && this.getVersionNoFlags().lte(VERUSPAY_VERSION_LASTVALID);
  }

  isSigned() {
    return !!(this.version.and(VERUSPAY_VERSION_SIGNED).toNumber());
  }

  setSigned() {
    this.version = this.version.or(VERUSPAY_VERSION_SIGNED);
  }

  getDetailsHash(signedBlockheight: number, signatureVersion: number = 2) {
    if (this.isSigned()) {
      var heightBufferWriter = new bufferutils.BufferWriter(
        Buffer.allocUnsafe(4)
      );
      heightBufferWriter.writeUInt32(signedBlockheight);
  
      if (signatureVersion === 1) {
        return createHash("sha256")
          .update(VERUS_DATA_SIGNATURE_PREFIX)
          .update(fromBase58Check(this.system_id).hash)
          .update(heightBufferWriter.buffer)
          .update(fromBase58Check(this.signing_id).hash)
          .update(this.details.toSha256())
          .digest();
      } else {
        return createHash("sha256")
          .update(fromBase58Check(this.system_id).hash)
          .update(heightBufferWriter.buffer)
          .update(fromBase58Check(this.signing_id).hash)
          .update(VERUS_DATA_SIGNATURE_PREFIX)
          .update(this.details.toSha256())
          .digest();
      }
    } else return this.details.toSha256()
  }

  protected _dataByteLength(signer: string = this.signing_id): number {
    if (this.isSigned()) {
      let length = 0;
  
      const _signature = this.signature
        ? this.signature
        : new VerusIDSignature(
            { signature: "" },
            IDENTITY_AUTH_SIG_VDXF_KEY,
            false
          );
  
      const _system_id = Hash160.fromAddress(this.system_id);
      length += _system_id.byteLength();
  
      const _signing_id = Hash160.fromAddress(signer);
      length += _signing_id.byteLength();

      length += _signature.byteLength();
      length += this.details.getByteLength();
  
      return length;
    } else return this.details.getByteLength()
  }

  protected _toDataBuffer(signer: string = this.signing_id): Buffer {
    const writer = new bufferutils.BufferWriter(
      Buffer.alloc(this.dataByteLength())
    );

    if (this.isSigned()) {
      const _signing_id = Hash160.fromAddress(signer);
      const _signature = this.signature
        ? this.signature
        : new VerusIDSignature(
            { signature: "" },
            IDENTITY_AUTH_SIG_VDXF_KEY,
            false
          );
  
      const _system_id = Hash160.fromAddress(this.system_id);
      writer.writeSlice(_system_id.toBuffer());
  
      writer.writeSlice(_signing_id.toBuffer());
  
      writer.writeSlice(_signature.toBuffer());
    }

    writer.writeSlice(this.details.toBuffer());

    return writer.buffer;
  }

  dataByteLength(): number {
    return this._dataByteLength();
  }

  toDataBuffer(): Buffer {
    return this._toDataBuffer();
  }

  protected _fromDataBuffer(buffer: Buffer, offset?: number): number {
    const reader = new bufferutils.BufferReader(buffer, offset);
    const reqLength = reader.readCompactSize();

    if (reqLength == 0) {
      throw new Error("Cannot create request from empty buffer");
    } else {
      if (this.isSigned()) {
        this.system_id = toBase58Check(
          reader.readSlice(HASH160_BYTE_LENGTH),
          I_ADDR_VERSION
        );
  
        this.signing_id = toBase58Check(
          reader.readSlice(HASH160_BYTE_LENGTH),
          I_ADDR_VERSION
        );
  
        const _sig = new VerusIDSignature(undefined, IDENTITY_AUTH_SIG_VDXF_KEY, false);
        reader.offset = _sig.fromBuffer(reader.buffer, reader.offset, IDENTITY_AUTH_SIG_VDXF_KEY.vdxfid);
        this.signature = _sig;
      }
      
      const _details = new VerusPayInvoiceDetails();
      reader.offset = _details.fromBuffer(reader.buffer, reader.offset, this.getVersionNoFlags());
      this.details = _details;
    }

    return reader.offset;
  }

  fromDataBuffer(buffer: Buffer, offset?: number): number {
    return this._fromDataBuffer(buffer, offset);
  }

  toWalletDeeplinkUri(): string {
    return `${WALLET_VDXF_KEY.vdxfid.toLowerCase()}://x-callback-url/${
      VERUSPAY_INVOICE_VDXF_KEY.vdxfid
    }/${this.toString(false)}`;
  }

  static fromWalletDeeplinkUri(uri: string): VerusPayInvoice {
    const split = uri.split(`${VERUSPAY_INVOICE_VDXF_KEY.vdxfid}/`);
    const inv = new VerusPayInvoice();
    inv.fromBuffer(base64url.toBuffer(split[1]), 0, VERUSPAY_INVOICE_VDXF_KEY.vdxfid);

    return inv;
  }

  toQrString(): string {
    return this.toString(true);
  }

  static fromQrString(qrstring: string): VerusPayInvoice {
    const inv = new VerusPayInvoice();
    inv.fromBuffer(base64url.toBuffer(qrstring), 0);

    return inv;
  }

  static fromJson(data: VerusPayInvoiceJson): VerusPayInvoice {
    return new VerusPayInvoice({
      details: VerusPayInvoiceDetails.fromJson(data.details, data.version ? new BN(data.version) : VERUSPAY_VERSION_CURRENT),
      signature: data.signature != null ? VerusIDSignature.fromJson(data.signature) : undefined,
      signing_id: data.signing_id,
      system_id: data.system_id,
      version: new BN(data.version)
    })
  }

  toJson(): VerusPayInvoiceJson {
    return {
      vdxfkey: this.vdxfkey,
      system_id: this.system_id,
      signing_id: this.signing_id,
      signature: this.isSigned() ? this.signature.toJson() : this.signature,
      details: this.details.toJson(),
      version: this.version.toString()
    };
  }
}
