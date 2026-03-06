import { ApiResponse } from "../../ApiResponse";

export class MakeOfferResponse extends ApiResponse {
  result: {
    txid?: string;
    hex?: string;
  };
}