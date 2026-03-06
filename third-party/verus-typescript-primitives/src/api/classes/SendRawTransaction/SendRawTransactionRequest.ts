import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { SEND_RAW_TRANSACTION } from "../../../constants/cmds";

export class SendRawTransactionRequest extends ApiRequest {
  hexstring: string;
  allowhighfees?: boolean;

  constructor(
    chain: string,
    hexstring: string,
    allowhighfees?: boolean,
  ) {
    super(chain, SEND_RAW_TRANSACTION);
    this.hexstring = hexstring;
    this.allowhighfees = allowhighfees;
  }

  getParams(): RequestParams {
    const params = [
      this.hexstring,
      this.allowhighfees
    ];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): SendRawTransactionRequest {
    return new SendRawTransactionRequest(
      object.chain as string,
      object.hexstring as string,
      object.allowhighfees != null ? (object.allowhighfees as boolean) : undefined
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      hexstring: this.hexstring,
      allowhighfees: this.allowhighfees
    };
  }
}
