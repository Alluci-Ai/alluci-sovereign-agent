import { ApiRequest } from "../../ApiRequest";
import { SignDataArgs } from "../../SignDataArgs";
import { ApiPrimitiveJson, RequestParams } from "../../ApiPrimitive";
import { SIGN_DATA } from "../../../constants/cmds";
import { DataDescriptorInfo } from "../../../utils/types/DataDescriptor";
import { SignDataParameters } from "../../../utils/types/SignData";



export class SignDataRequest extends ApiRequest {
  data: SignDataArgs;

  constructor(chain: string, signableItems: SignDataArgs) {
    super(chain, SIGN_DATA);
    this.data = signableItems;
  }

  getParams(): RequestParams {
    const params = [this.data];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): SignDataRequest {
    return new SignDataRequest(
      object.chain as string,
      object.data as SignDataArgs
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      data: this.data,
    };
  }
}