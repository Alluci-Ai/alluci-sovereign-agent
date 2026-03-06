import { ApiResponse } from "../../ApiResponse";

export class GetAddressDeltasResponse extends ApiResponse {
  result: Array<{
    satoshis: number;
    txid: string;
    index: number;
    blockindex: number;
    height: number;
    address: string;
    currencyvalues?: { [key: string]: number },
    blocktime?: number;
    currencynames?: { [key: string]: string },
    sent?: {
      outputs: Array<{
        addresses: string | Array<string>;
        amounts: { [key: string]: number };
      }>;
    };
  }>;
}