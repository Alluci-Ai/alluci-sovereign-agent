import { RawTransaction } from "../../../transaction/RawTransaction";
import { ApiResponse } from "../../ApiResponse";

export class GetRawTransactionResponse extends ApiResponse {
  result: string | RawTransaction
}
