import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { GET_CURRENCY } from "../../../constants/cmds";

export class GetCurrencyRequest extends ApiRequest {
  currencyname?: string;

  constructor(
    chain: string,
    currencyname?: string
  ) {
    super(chain, GET_CURRENCY);
    this.currencyname = currencyname;
  }

  getParams(): RequestParams {
    const params = [
      this.currencyname
    ];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): GetCurrencyRequest {
    return new GetCurrencyRequest(
      object.chain as string,
      object.currencyname as string
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      currencyname: this.currencyname
    };
  }
}
