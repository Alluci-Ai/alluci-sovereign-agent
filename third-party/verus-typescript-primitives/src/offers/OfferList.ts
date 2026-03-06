export type ListedCurrencyOffering = {
  [key: string]: number;
}

export interface ListedIdentityOffering {
  name: string;
  identityid: string;
  systemid: string;
  original: number;
}

export type ListedValueOffering = ListedCurrencyOffering | ListedIdentityOffering;

export interface ListedOfferTerms {
  offer: ListedValueOffering;
  accept: ListedValueOffering;
  blockexpiry: number;
  txid: number;
}

export interface ListedOffer {
  currencyid: string;
  price: number;
  offer: ListedOfferTerms;
}

export type OfferList = {
  [key: string]: Array<ListedOffer>
}