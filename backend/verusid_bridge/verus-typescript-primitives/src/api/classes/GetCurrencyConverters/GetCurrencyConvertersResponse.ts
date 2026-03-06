import { CurrencyDefinition } from "../../../currency/CurrencyDefinition";
import { ApiResponse } from "../../ApiResponse";

export class GetCurrencyConvertersResponse extends ApiResponse {
  result: Array<{
    [key: string]: CurrencyDefinition
  }>
}