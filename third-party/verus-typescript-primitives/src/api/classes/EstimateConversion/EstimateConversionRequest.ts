import { ApiRequest } from "../../ApiRequest";
import { ApiPrimitiveJson, RequestParams } from "../../ApiPrimitive";
import { ESTIMATE_CONVERSION } from "../../../constants/cmds";

type Output = {
  currency: string;
  amount: number;
  convertto: string;
  preconvert?: boolean;
  via?: string;
}

export class EstimateConversionRequest extends ApiRequest {
  output: Output;

  constructor(chain: string, output: Output) {
    super(chain, ESTIMATE_CONVERSION);
    this.output = output;
  }

  getParams(): RequestParams {
    const params = [
      this.output
    ];

    return params;
  }

  static fromJson(object: ApiPrimitiveJson): EstimateConversionRequest {
    return new EstimateConversionRequest(
      object.chain as string,
      object.output as Output
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      output: this.output
    };
  }
}
