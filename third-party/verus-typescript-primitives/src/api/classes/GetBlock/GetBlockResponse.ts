import { BlockInfo } from "../../../block/BlockInfo";
import { ApiResponse } from "../../ApiResponse";

export class GetBlockResponse extends ApiResponse {
  result: string | BlockInfo
}
