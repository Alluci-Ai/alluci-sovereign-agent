import { ApiResponse } from "../../ApiResponse";

export class SignMessageResponse extends ApiResponse {
  result: {
    hash: string;
    signature: string;
  };
}