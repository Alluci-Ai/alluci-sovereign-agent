import { ApiCommunication } from "./ApiCommunication";
import { ApiPrimitive, ApiPrimitiveJson, RequestParams } from "./ApiPrimitive";

export abstract class ApiRequest implements ApiCommunication {
  chain: string;
  cmd: string;

  abstract getParams(): RequestParams;
  abstract toJson(): ApiPrimitiveJson;

  constructor(chain: string, cmd: string) {
    this.chain = chain;
    this.cmd = cmd;
  }

  prepare(): [string, string, RequestParams] {
    return [this.chain, this.cmd, this.getParams()];
  }
}
