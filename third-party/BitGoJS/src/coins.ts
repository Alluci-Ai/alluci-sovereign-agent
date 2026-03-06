/**
 * @prettier
 */
import * as networks from './networks';
import { coins, Network, NetworkName, PBaaSNetwork } from './networkTypes';

const typeforce = require('typeforce');

/**
 * @returns {Network[]} all known networks as array
 */
export function getNetworkList(): Network[] {
  return Object.keys(networks).map((n) => networks[<NetworkName>n]);
}

/**
 * @param {Network} network
 * @returns {NetworkName} the name of the network. Returns undefined if network is not a value
 *                   of `networks`
 */
export function getNetworkName(network: Network): NetworkName | undefined {
  const nameStringOrUndefined = Object.keys(networks).find((n) => networks[<NetworkName>n] === network);

  if (typeof nameStringOrUndefined === 'string') return <NetworkName>nameStringOrUndefined
  else return undefined
}

/**
 * @param {Network} network
 * @returns {Object} the mainnet corresponding to a testnet
 */
export function getMainnet(network: Network): Network {
  switch (network) {
    case networks.verus:
    case networks.verustest:
      return networks.verus

    case networks.kmd:
      return networks.kmd

    case networks.doge:
      return networks.doge

    case networks.digibyte:
      return networks.digibyte

    case networks.bitcoin:
    case networks.testnet:
      return networks.bitcoin;

    case networks.bitcoincash:
    case networks.bitcoincashTestnet:
      return networks.bitcoincash;

    case networks.bitcoingold:
    case networks.bitcoingoldTestnet:
      return networks.bitcoingold;

    case networks.bitcoinsv:
    case networks.bitcoinsvTestnet:
      return networks.bitcoinsv;

    case networks.dash:
    case networks.dashTest:
      return networks.dash;

    case networks.litecoin:
    case networks.litecoinTest:
      return networks.litecoin;

    case networks.zcash:
    case networks.zcashTest:
      return networks.zcash

    case networks.default:
      return networks.default

    default:
      return network
  }
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is a mainnet
 */
export function isMainnet(network: Network): boolean {
  return getMainnet(network) === network;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is a testnet
 */
export function isTestnet(network: Network): boolean {
  return getMainnet(network) !== network;
}

/**
 *
 * @param {Network} network
 * @param {Network} otherNetwork
 * @returns {boolean} true iff both networks are for the same coin
 */
export function isSameCoin(network: Network, otherNetwork: Network) {
  return getMainnet(network) === getMainnet(otherNetwork);
}

const mainnets = getNetworkList().filter(isMainnet);
const testnets = getNetworkList().filter(isTestnet);

/**
 * Map where keys are mainnet networks and values are testnet networks
 * @type {Map<Network, Network[]>}
 */
const mainnetTestnetPairs = new Map(mainnets.map((m) => [m, testnets.filter((t) => getMainnet(t) === m)]));

/**
 * @param {Network} network
 * @returns {Network|undefined} - The testnet corresponding to a mainnet.
 *                               Returns undefined if a network has no testnet.
 */
export function getTestnet(network: Network): Network | undefined {
  if (isTestnet(network)) {
    return network;
  }
  const testnets = mainnetTestnetPairs.get(network);
  if (testnets === undefined) {
    throw new Error(`invalid argument`);
  }
  if (testnets.length === 0) {
    return
  }
  if (testnets.length === 1) {
    return testnets[0];
  }
  throw new Error(`more than one testnet for ${getNetworkName(network)}`);
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network bitcoin or testnet
 */
export function isBitcoin(network: Network) {
  return getMainnet(network) === networks.bitcoin;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is bitcoincash or bitcoincashTestnet
 */
export function isBitcoinCash(network: Network) {
  return getMainnet(network) === networks.bitcoincash;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is bitcoingold
 */
export function isBitcoinGold(network: Network) {
  return getMainnet(network) === networks.bitcoingold;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is bitcoinsv or bitcoinsvTestnet
 */
export function isBitcoinSV(network: Network) {
  return getMainnet(network) === networks.bitcoinsv;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is dash or dashTest
 */
export function isDash(network: Network) {
  return getMainnet(network) === networks.dash;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is litecoin or litecoinTest
 */
export function isLitecoin(network: Network) {
  return getMainnet(network) === networks.litecoin;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is zcash or zcashTest
 */
export function isZcash(network: Network) {
  return getMainnet(network) === networks.zcash;
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is Verus or VerusTest
 */
export  function isVerus (network: Network) {
  return getMainnet(network) === networks.verus
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is PBaaS compatible
 */
export function isPBaaS (network: Network) {
  return network && !!(network as PBaaSNetwork).isPBaaS
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is zcash compatible
 */
export function isZcashCompatible (network: Network) {
  return isZcash(network) || isPBaaS(network) || isKomodo(network)
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is Komodo
 */
export  function isKomodo (network: Network) {
  return getMainnet(network) === networks.kmd
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is Doge
 */
export  function isDoge (network: Network) {
  return getMainnet(network) === networks.doge
}

/**
 * @param {Network} network
 * @returns {boolean} true iff network is Digibyte
 */
export  function isDigibyte (network: Network) {
  return getMainnet(network) === networks.digibyte
}

/**
 * @param {Network} network
 * @returns {boolean} returns true iff network is any of the network stated in the argument
 */
export const isValidNetwork = typeforce.oneOf(
  isBitcoin,
  isBitcoinCash,
  isBitcoinGold,
  isBitcoinSV,
  isDash,
  isLitecoin,
  isZcash,
  isZcashCompatible,
  isVerus,
  isPBaaS,
  isKomodo,
  isDoge,
  isDigibyte
)


/** @deprecated */
export const BCH = coins.BCH;
/** @deprecated */
export const BSV = coins.BSV;
/** @deprecated */
export const BTC = coins.BTC;
/** @deprecated */
export const BTG = coins.BTG;
/** @deprecated */
export const DASH = coins.DASH;
/** @deprecated */
export const DEFAULT = coins.DEFAULT;
/** @deprecated */
export const DGB = coins.DGB;
/** @deprecated */
export const DOGE = coins.DOGE;
/** @deprecated */
export const KMD = coins.KMD;
/** @deprecated */
export const LTC = coins.LTC;
/** @deprecated */
export const VRSC = coins.VRSC;
/** @deprecated */
export const ZEC = coins.ZEC;
