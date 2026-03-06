import { ApiResponse } from "../../ApiResponse";

export class FundRawTransactionResponse extends ApiResponse {
  result: {
    hex: string;
    changepos: number;
    fee: number;
  };
}
