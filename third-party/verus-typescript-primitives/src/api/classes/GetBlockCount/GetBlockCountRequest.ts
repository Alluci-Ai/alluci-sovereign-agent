import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { GET_BLOCK_COUNT } from "../../../constants/cmds";

export class GetBlockCountRequest extends ApiRequest {

  constructor(chain: string) {
    super(chain, GET_BLOCK_COUNT);
  }

  getParams(): RequestParams {
    const params = [
    ];

    return params;
  }

  static fromJson(object: ApiPrimitiveJson): GetBlockCountRequest {
    return new GetBlockCountRequest(
      object.chain as string,
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
    };
  }
}
