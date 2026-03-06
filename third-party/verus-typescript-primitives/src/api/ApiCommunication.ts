import { ApiPrimitive } from "./ApiPrimitive";

export interface ApiCommunication {
  toJson: () => ApiPrimitive
}