import { CurrencyDefinition } from "../../../currency/CurrencyDefinition";
import { ApiResponse } from "../../ApiResponse";

export class GetCurrencyResponse extends ApiResponse {
  result: CurrencyDefinition;
}
