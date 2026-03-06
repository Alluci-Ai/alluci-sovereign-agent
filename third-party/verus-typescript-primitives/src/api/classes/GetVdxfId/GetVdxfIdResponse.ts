import { ApiResponse } from "../../ApiResponse";

export class GetVdxfIdResponse extends ApiResponse {
  result: {
    vdxfid: string,
    hash160result: string,
    qualifiedname: {
      name: string,
      parentid: string
    },
    bounddata?: {
      vdxfkey: string,
      uint256: string,
      indexnum: string
    }
  }
}
