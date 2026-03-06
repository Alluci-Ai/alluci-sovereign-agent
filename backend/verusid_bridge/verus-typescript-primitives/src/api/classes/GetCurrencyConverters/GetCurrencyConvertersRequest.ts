import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { GET_CURRENCY_CONVERTERS } from "../../../constants/cmds";

export class GetCurrencyConvertersRequest extends ApiRequest {
  currencies: Array<string>;

  constructor(
    chain: string,
    currencies: Array<string>
  ) {
    super(chain, GET_CURRENCY_CONVERTERS);
    this.currencies = currencies;
  }

  getParams(): RequestParams {
    return this.currencies
  }

  static fromJson(object: ApiPrimitiveJson): GetCurrencyConvertersRequest {
    return new GetCurrencyConvertersRequest(
      object.chain as string,
      object.currencies as Array<string>
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      currencies: this.currencies
    };
  }
}
