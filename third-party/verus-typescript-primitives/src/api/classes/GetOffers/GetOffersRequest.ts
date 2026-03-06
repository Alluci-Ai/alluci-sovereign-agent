import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { GET_OFFERS } from "../../../constants/cmds";

export class GetOffersRequest extends ApiRequest {
  currencyorid: string;
  iscurrency?: boolean;
  withtx?: boolean;

  constructor(
    chain: string,
    currencyorid: string,
    iscurrency?: boolean,
    withtx?: boolean,
  ) {
    super(chain, GET_OFFERS);
    this.currencyorid = currencyorid;
    this.iscurrency = iscurrency;
    this.withtx = withtx;
  }

  getParams(): RequestParams {
    const params = [
      this.currencyorid,
      this.iscurrency == null ? false : this.iscurrency,
      this.withtx,
    ];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): GetOffersRequest {
    return new GetOffersRequest(
      object.chain as string,
      object.currencyorid as string,
      object.iscurrency != null ? (object.iscurrency as boolean) : undefined,
      object.withtx != null ? (object.withtx as boolean) : undefined,
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      currencyorid: this.currencyorid,
      iscurrency: this.iscurrency,
      withtx: this.withtx
    };
  }
}