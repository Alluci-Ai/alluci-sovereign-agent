import { bech32 } from "bech32";

export const fromBech32 = (address: string): { version: number, prefix: string, data: Buffer } => {
  var result = bech32.decode(address, 1000); // Allow longer strings like extended keys
  var data = bech32.fromWords(result.words);

  return {
    version: result.words[0],
    prefix: result.prefix,
    data: Buffer.from(data)
  }
}

export const toBech32 = (prefix: string, data: Buffer): string => {
  const words = bech32.toWords(data);
  var result = bech32.encode(prefix, words, 1000); // Allow longer strings like extended keys

  return result;
}

export const convertBits = (data: Buffer, from: number, to: number, strictMode: boolean): Buffer => {
  const length = strictMode
    ? Math.floor((data.length * from) / to)
    : Math.ceil((data.length * from) / to);
  const mask = (1 << to) - 1;
  const result = Buffer.alloc(length);
  let index = 0;
  let accumulator = 0;
  let bits = 0;

  for (const value of data) {
    accumulator = (accumulator << from) | value;
    bits += from;
    while (bits >= to) {
      bits -= to;
      result[index] = (accumulator >> bits) & mask;
      ++index;
    }
  }

  if (!strictMode) {
    if (bits > 0) {
      result[index] = (accumulator << (to - bits)) & mask;
      ++index;
    }
  } else {
    throw new Error("Bits cannot be converted")
  }

  return result;
}

export const decodeSaplingAddress = (address: string): { d: Buffer, pk_d: Buffer } => {
  const result = fromBech32(address);

  //const data = convertBits(result.data, 5, 8, false);

  if (result.data.length !== 43) {
    throw new Error('Invalid sapling address');
  }

  return { d: Buffer.from(result.data.subarray(0, 11)), pk_d: Buffer.from(result.data.subarray(11)) };
}

export const encodeSaplingAddress = (data: { d: Buffer, pk_d: Buffer }): string => {
  const buffer = Buffer.concat([data.d, data.pk_d]);

  //const data = convertBits(buffer, 8, 5, false);

  return toBech32('zs', buffer);
}

export interface SaplingExtendedSpendingKeyData {
  depth: number;
  parentFVKTag: Buffer;
  childIndex: Buffer;
  chainCode: Buffer;
  ask: Buffer;
  nsk: Buffer;
  ovk: Buffer;
  dk: Buffer;
}

export interface SaplingExtendedViewingKeyData {
  depth: number;
  parentFVKTag: Buffer;
  childIndex: Buffer;
  chainCode: Buffer;
  ak: Buffer;
  nk: Buffer;
  ovk: Buffer;
  dk: Buffer;
}

export function decodeSaplingExtendedSpendingKey(encoded: string): SaplingExtendedSpendingKeyData {
  const result = fromBech32(encoded);
  
  // Verify prefix is for extended spending key
  if (!result.prefix.startsWith('secret-extended-key-')) {
    throw new Error('Invalid Sapling extended spending key prefix');
  }

  // Data should be 169 bytes: 1 (depth) + 4 (parent) + 4 (child) + 32*4 (keys)
  if (result.data.length !== 169) {
    throw new Error(`Invalid Sapling extended spending key length: expected 169, got ${result.data.length}`);
  }

  let offset = 0;
  
  return {
    depth: result.data.readUInt8(offset++),
    parentFVKTag: Buffer.from(result.data.subarray(offset, offset += 4)),
    childIndex: Buffer.from(result.data.subarray(offset, offset += 4)),
    chainCode: Buffer.from(result.data.subarray(offset, offset += 32)),
    ask: Buffer.from(result.data.subarray(offset, offset += 32)),
    nsk: Buffer.from(result.data.subarray(offset, offset += 32)),
    ovk: Buffer.from(result.data.subarray(offset, offset += 32)),
    dk: Buffer.from(result.data.subarray(offset, offset += 32))
  };
}

export function encodeSaplingExtendedSpendingKey(data: SaplingExtendedSpendingKeyData, testnet: boolean = false): string {
  const prefix = testnet ? 'secret-extended-key-test' : 'secret-extended-key-main';
  
  const buffer = Buffer.concat([
    Buffer.from([data.depth]),
    data.parentFVKTag,
    data.childIndex,
    data.chainCode,
    data.ask,
    data.nsk,
    data.ovk,
    data.dk
  ]);
  
  return toBech32(prefix, buffer);
}

export function decodeSaplingExtendedViewingKey(encoded: string): SaplingExtendedViewingKeyData {
  const result = fromBech32(encoded);
  
  // Verify prefix is for extended viewing key
  if (!result.prefix.startsWith('zxview')) {
    throw new Error('Invalid Sapling extended viewing key prefix');
  }

  // Data should be 169 bytes: 1 (depth) + 4 (parent) + 4 (child) + 32*5 (keys)
  if (result.data.length !== 169) {
    throw new Error('Invalid Sapling extended viewing key length');
  }

  let offset = 0;
  
  return {
    depth: result.data.readUInt8(offset++),
    parentFVKTag: Buffer.from(result.data.subarray(offset, offset += 4)),
    childIndex: Buffer.from(result.data.subarray(offset, offset += 4)),
    chainCode: Buffer.from(result.data.subarray(offset, offset += 32)),
    ak: Buffer.from(result.data.subarray(offset, offset += 32)),
    nk: Buffer.from(result.data.subarray(offset, offset += 32)),
    ovk: Buffer.from(result.data.subarray(offset, offset += 32)),
    dk: Buffer.from(result.data.subarray(offset, offset += 32))
  };
}

export function encodeSaplingExtendedViewingKey(data: SaplingExtendedViewingKeyData, testnet: boolean = false): string {
  const prefix = testnet ? 'zxviewtestsapling' : 'zxviews';
  
  const buffer = Buffer.concat([
    Buffer.from([data.depth]),
    data.parentFVKTag,
    data.childIndex,
    data.chainCode,
    data.ak,
    data.nk,
    data.ovk,
    data.dk
  ]);
  
  return toBech32(prefix, buffer);
}