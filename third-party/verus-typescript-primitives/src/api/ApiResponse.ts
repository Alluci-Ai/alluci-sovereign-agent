import { ApiCommunication } from "./ApiCommunication";
import { ApiPrimitive } from "./ApiPrimitive";

export class ApiResponse implements ApiCommunication {
  result: ApiPrimitive;

  constructor(result) {
    this.result = result;
  }
  
  toJson(): ApiPrimitive {
    return this.result;
  }
}
