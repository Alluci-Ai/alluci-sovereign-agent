import { IdentityDefinition } from "../identity/IdentityDefinition";
import { CurrencyOffering } from "./CurrencyOffering";
import { CurrencyReceiving } from "./CurrencyReceiving";
import { IdentityOffering } from "./IdentityOffering";

export interface OfferForMaking {
  changeaddress: string;
  offer: IdentityOffering | CurrencyOffering;
  for: IdentityDefinition | CurrencyReceiving;
  expiryheight?: number;
}