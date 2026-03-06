import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { GET_INFO } from "../../../constants/cmds";

export class GetInfoRequest extends ApiRequest {
  constructor(chain: string) {
    super(chain, GET_INFO);
  }

  getParams(): RequestParams {
    return [];
  }

  static fromJson(object: ApiPrimitiveJson): GetInfoRequest {
    return new GetInfoRequest(object.chain as string);
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
    };
  }
}
