/**
 * @prettier
 */

/**
 * @deprecated
 */
export const coins = {
  BCH: 'bch',
  BSV: 'bsv',
  BTC: 'btc',
  BTG: 'btg',
  LTC: 'ltc',
  ZEC: 'zec',
  DASH: 'dash',
  VRSC: 'vrsc',
  DEFAULT: 'default',
  KMD: 'kmd',
  DGB: 'dgb',
  DOGE: 'doge',
} as const;

/** @deprecated */
export type CoinKey = keyof typeof coins;
/** @deprecated */
export type Coin = typeof coins[CoinKey];

export type NetworkName =
  | 'bitcoin'
  | 'testnet'
  | 'bitcoincash'
  | 'bitcoincashTestnet'
  | 'bitcoingold'
  | 'bitcoingoldTestnet'
  | 'bitcoinsv'
  | 'bitcoinsvTestnet'
  | 'dash'
  | 'dashTest'
  | 'default'
  | 'digibyte'
  | 'doge'
  | 'litecoin'
  | 'litecoinTest'
  | 'kmd'
  | 'verus'
  | 'verustest'
  | 'zcash'
  | 'zcashTest';

export type Network = {
  messagePrefix: string;
  pubKeyHash: number;
  scriptHash: number;
  wif: number;
  bip32: {
    public: number;
    private: number;
  };
  bech32?: string;
  /**
   * @deprecated
   */
  coin: Coin;
  forkId?: number;
};

export type ZcashNetwork = Network & {
  consensusBranchId: Record<number, number>;
  isZcashCompatible: boolean;
};

export type PBaaSNetwork = ZcashNetwork & {
  verusID: number;
  isPBaaS: boolean;
};

export type DigiDogeNetwork = Network & {
  bip44: number;
  dustThreshold: number;
};

export type BitcoinCashNetwork = Network & {
  cashAddr: {
    prefix: string;
    pubKeyHash: number;
    scriptHash: number;
  };
};
