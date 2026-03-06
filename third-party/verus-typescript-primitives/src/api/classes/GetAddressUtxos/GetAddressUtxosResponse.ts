import { ApiResponse } from "../../ApiResponse";

export class GetAddressUtxosResponse extends ApiResponse {
  result: Array<{
    address: string;
    txid: string;
    outputIndex: number;
    script: string;
    currencyvalues?: {
      [key: string]: number | undefined;
    };
    currencynames?: {
      [key: string]: string | undefined;
    };
    satoshis: number;
    height: number;
    isspendable: number;
    blocktime: number;
  }>;
}
