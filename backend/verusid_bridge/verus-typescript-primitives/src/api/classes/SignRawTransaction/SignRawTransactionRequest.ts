import { ApiRequest } from "../../ApiRequest";
import { ApiPrimitiveJson, RequestParams } from "../../ApiPrimitive";
import { SIGN_RAW_TRANSACTION } from "../../../constants/cmds";

type PrevTx = {
  txid: string;
  vout: number;
  scriptPubKey: string;
  redeemScript: string;
  amount: number;
};

type SigHashType = "ALL" | "NONE" | "SINGLE" | "ALL|ANYONECANPAY" | "NONE|ANYONECANPAY" | "SINGLE|ANYONECANPAY";

export class SignRawTransactionRequest extends ApiRequest {
  hexstring: string;
  prevtxs?: Array<PrevTx>;
  sighashtype?: SigHashType;
  branchid?: string;

  constructor(chain: string, hexstring: string, prevtxs?: Array<PrevTx>, sighashtype?: SigHashType, branchid?: string) {
    super(chain, SIGN_RAW_TRANSACTION);
    this.hexstring = hexstring;
    this.prevtxs = prevtxs;
    this.sighashtype = sighashtype;
    this.branchid = branchid;
  }

  getParams(): RequestParams {
    const params = [
      this.hexstring,
      this.prevtxs,
      this.sighashtype,
      this.branchid
    ];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): SignRawTransactionRequest {
    return new SignRawTransactionRequest(
      object.chain as string,
      object.hexstring as string,
      object.prevtxs != null ? (object.prevtxs as Array<PrevTx>) : undefined,
      object.sighashtype != null ? (object.sighashtype as SigHashType) : undefined,
      object.branchid != null ? (object.branchid as string) : undefined,
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      hexstring: this.hexstring,
      prevtxs: this.prevtxs,
      sighashtype: this.sighashtype,
      branchid: this.branchid,
    };
  }
}
