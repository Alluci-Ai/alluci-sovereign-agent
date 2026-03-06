import { BN } from "bn.js";

export const DATA_TYPE_UNKNOWN = new BN("0", 10);
export const DATA_TYPE_MMRDATA = new BN("1", 10);
export const DATA_TYPE_FILENAME = new BN("2", 10);
export const DATA_TYPE_MESSAGE = new BN("3", 10);
export const DATA_TYPE_VDXFDATA = new BN("4", 10);
export const DATA_TYPE_HEX = new BN("5", 10);
export const DATA_TYPE_BASE64 = new BN("6", 10);
export const DATA_TYPE_DATAHASH = new BN("7", 10);
export const DATA_TYPE_RAWSTRINGDATA = new BN("8", 10);

export const HASH_TYPE_INVALID = new BN(0, 10);
export const HASH_TYPE_BLAKE2B = new BN(1, 10);
export const HASH_TYPE_BLAKE2BMMR2 = new BN(2, 10);
export const HASH_TYPE_KECCAK256 = new BN(3, 10);
export const HASH_TYPE_SHA256D = new BN(4, 10);
export const HASH_TYPE_SHA256 = new BN(5, 10);

export const HASH_TYPE_SHA256_NAME = "sha256";
export const HASH_TYPE_SHA256D_NAME = "sha256D";
export const HASH_TYPE_BLAKE2B_NAME = "blake2b";
export const HASH_TYPE_KECCAK256_NAME = "keccak256";

export const DEFAULT_HASH_TYPE = HASH_TYPE_SHA256;
export const DEFAULT_HASH_TYPE_MMR = HASH_TYPE_BLAKE2B;
export const HASH_NAMES = [HASH_TYPE_SHA256_NAME, HASH_TYPE_SHA256D_NAME, HASH_TYPE_BLAKE2B_NAME, HASH_TYPE_KECCAK256_NAME];
export type AllowedHashes = (typeof HASH_NAMES)[number];

export const UINT_256_LENGTH = 32;

export const DEFAULT_VERUS_CHAINID = "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV";
export const TESTNET_VERUS_CHAINID = "iJhCezBExJHvtyH3fGhNnt2NhU4Ztkf2yq";
export const DEFAULT_VERUS_CHAINNAME = "VRSC";
export const KOMODO_ASSETCHAIN_MAXLEN = 65;
export const NULL_I_ADDR = "i3UXS5QPRQGNRDDqVnyWTnmFCTHDbzmsYk";