import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { Z_GET_OPERATION_STATUS } from "../../../constants/cmds";

export class ZGetOperationStatusRequest extends ApiRequest {
  operations?: Array<string>;

  constructor(
    chain: string,
    operations?: Array<string>
  ) {
    super(chain, Z_GET_OPERATION_STATUS);
    this.operations = operations;
  }

  getParams(): RequestParams {
    const params = [
      this.operations
    ];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): ZGetOperationStatusRequest {
    return new ZGetOperationStatusRequest(
      object.chain as string,
      object.operations as Array<string>
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      operations: this.operations,
    }
  }
}