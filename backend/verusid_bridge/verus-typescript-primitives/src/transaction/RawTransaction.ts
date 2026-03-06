import { ApiPrimitive } from "../api/ApiPrimitive";

export interface RawTransaction {
  hex: string;
  txid: string;
  overwintered: boolean;
  version: number;
  versiongroupid: string;
  locktime: number;
  expiryheight: number;
  vin: Array<ApiPrimitive>;
  vout: Array<ApiPrimitive>;
  vjoinsplit: Array<ApiPrimitive>;
  valueBalance: number;
  vShieldedSpend: Array<ApiPrimitive>;
  vShieldedOutput: Array<ApiPrimitive>;
  blockhash: string;
  height: number;
  confirmations: number;
  time: number;
  blocktime: number;
}
