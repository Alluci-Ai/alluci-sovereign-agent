import { ApiRequest } from "../../ApiRequest";
import { ApiPrimitiveJson, RequestParams } from "../../ApiPrimitive";
import { VERIFY_MESSAGE } from "../../../constants/cmds";

export class VerifyMessageRequest extends ApiRequest {
  tAddrOrIdentity: string;
  signature: string;
  message: string;
  checklatest?: boolean;

  constructor(
    chain: string,
    tAddrOrIdentity: string,
    signature: string,
    message: string,
    checklatest?: boolean
  ) {
    super(chain, VERIFY_MESSAGE);
    this.tAddrOrIdentity = tAddrOrIdentity;
    this.message = message;
    this.signature = signature;
    this.checklatest = checklatest;
  }

  getParams(): RequestParams {
    const params = [this.tAddrOrIdentity, this.signature, this.message, this.checklatest];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): VerifyMessageRequest {
    return new VerifyMessageRequest(
      object.chain as string,
      object.tAddrOrIdentity as string,
      object.signature as string,
      object.message as string,
      object.checklatest != null ? (object.checklatest as boolean) : undefined
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      tAddrOrIdentity: this.tAddrOrIdentity,
      signature: this.signature,
      message: this.message,
      checklatest: this.checklatest,
    };
  }
}