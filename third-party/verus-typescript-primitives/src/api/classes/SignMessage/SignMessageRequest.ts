import { ApiRequest } from "../../ApiRequest";
import { ApiPrimitiveJson, RequestParams } from "../../ApiPrimitive";
import { SIGN_MESSAGE } from "../../../constants/cmds";

export class SignMessageRequest extends ApiRequest {
  tAddrOrIdentity: string;
  message: string;
  cursig?: string;

  constructor(chain: string, tAddrOrIdentity: string, message: string, cursig?: string) {
    super(chain, SIGN_MESSAGE);
    this.tAddrOrIdentity = tAddrOrIdentity;
    this.message = message;
    this.cursig = cursig;
  }

  getParams(): RequestParams {
    const params = [this.tAddrOrIdentity, this.message, this.cursig];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): SignMessageRequest {
    return new SignMessageRequest(
      object.chain as string,
      object.tAddrOrIdentity as string,
      object.message as string,
      object.cursig != null ? (object.cursig as string) : undefined
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      tAddrOrIdentity: this.tAddrOrIdentity,
      message: this.message,
      cursig: this.cursig
    };
  }
}