import { ApiRequest } from "../../ApiRequest";
import { RequestParams, ApiPrimitiveJson } from "../../ApiPrimitive";
import { GET_ADDRESS_UTXOS } from "../../../constants/cmds";

interface Addresses {
  addresses: Array<string>;
  chaininfo?: boolean;
  friendlynames?: boolean;
}

export class GetAddressUtxosRequest extends ApiRequest {
  addresses: Addresses;

  constructor(chain: string, addresses: Addresses) {
    super(chain, GET_ADDRESS_UTXOS);
    this.addresses = addresses;
  }

  getParams(): RequestParams {
    return [
      this.addresses as {
        addresses: Array<string>;
        chaininfo?: boolean;
        friendlynames?: boolean;
      },
    ];
  }

  static fromJson(object: ApiPrimitiveJson): GetAddressUtxosRequest {
    return new GetAddressUtxosRequest(
      object.chain as string,
      object.addresses as unknown as Addresses
    );
  }

  toJson(): ApiPrimitiveJson {
    return {
      chain: this.chain,
      addresses: this.addresses as {
        addresses: Array<string>;
        chaininfo?: boolean;
        friendlynames?: boolean;
      },
    };
  }
}
