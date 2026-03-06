import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { LIST_CURRENCIES } from "../../../constants/cmds";

type QueryObject = { 
  launchstate?: "prelaunch" | "launched" | "refund" | "complete",
  systemtype?: "local" | "imported" | "gateway" | "pbaas",
  fromsystem?: string,
  converter?: Array<string>
}

export class ListCurrenciesRequest extends ApiRequest {
  query?: QueryObject;
  startblock?: number;
  endblock?: number;

  constructor(
    chain: string,
    query?: QueryObject,
    startblock?: number,
    endblock?: number
  ) {
    super(chain, LIST_CURRENCIES);
    this.query = query;
    this.startblock = startblock;
    this.endblock = endblock;
  }

  getParams(): RequestParams {
    if (this.query == null && this.startblock == null && this.endblock == null) return []
    
    const params = [
      this.query == null ? {} : this.query,
      this.startblock == null ? 0 : this.startblock,
      this.endblock
    ];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): ListCurrenciesRequest {
    return new ListCurrenciesRequest(
      object.chain as string,
      object.query as QueryObject,
      object.startblock as number,
      object.endblock as number
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      query: this.query,
      startblock: this.startblock,
      endblock: this.endblock
    };
  }
}
