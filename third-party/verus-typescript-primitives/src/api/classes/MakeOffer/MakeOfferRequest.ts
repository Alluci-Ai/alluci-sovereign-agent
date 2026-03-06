import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { MAKE_OFFER } from "../../../constants/cmds";
import { OfferForMaking } from "../../../offers/OfferForMaking";

export class MakeOfferRequest extends ApiRequest {
  fromaddress: string;
  offer: OfferForMaking;
  returntx?: boolean;
  feeamount?: number;

  constructor(
    chain: string,
    fromaddress: string,
    offer: OfferForMaking,
    returntx?: boolean,
    feeamount?: number
  ) {
    super(chain, MAKE_OFFER);
    this.fromaddress = fromaddress;
    this.offer = offer;
    this.returntx = returntx;
    this.feeamount = feeamount;
  }

  getParams(): RequestParams {
    const params = [
      this.fromaddress,
      this.offer,
      this.returntx == null ? false : this.returntx,
      this.feeamount,
    ];

    return params.filter((x) => x != null);
  }

  static fromJson(object: ApiPrimitiveJson): MakeOfferRequest {
    return new MakeOfferRequest(
      object.chain as string,
      object.fromaddress as string,
      object.offer as OfferForMaking,
      object.returntx != null ? (object.returntx as boolean) : undefined,
      object.feeamount != null ? (object.feeamount as number) : undefined
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      fromaddress: this.fromaddress,
      offer: this.offer,
      returntx: this.returntx,
      feeamount: this.feeamount,
    };
  }
}