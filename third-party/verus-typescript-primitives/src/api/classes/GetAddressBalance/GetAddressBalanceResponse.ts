import { ApiResponse } from "../../ApiResponse";

export class GetAddressBalanceResponse extends ApiResponse {
  result: {
    balance: number;
    received: number;
    currencybalance: { [key: string]: number };
    currencyreceived: { [key: string]: number };
    currencynames?: { [key: string]: string };
  };
}
