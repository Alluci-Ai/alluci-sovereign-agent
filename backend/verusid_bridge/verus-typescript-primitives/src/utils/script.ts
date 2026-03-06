import * as pushdata from './pushdata';
import { OPS } from './ops';
import REVERSE_OPS from './reverseops';
import { isHexString } from './string';

const OP_INT_BASE = OPS.OP_RESERVED; // OP_1 - 1

export type ScriptChunk = Buffer | number;

export function isOPInt (value: number): boolean {
  return ((value === OPS.OP_0) ||
    (value >= OPS.OP_1 && value <= OPS.OP_16) ||
    (value === OPS.OP_1NEGATE));
}

export function isPushOnlyChunk(value: ScriptChunk): boolean {
  return Buffer.isBuffer(value) || isOPInt(value);
}

export function isPushOnly(value: Array<ScriptChunk>): boolean {
  return value.every(isPushOnlyChunk);
}

export function asMinimalOP(buffer: Buffer): number | undefined {
  if (buffer.length === 0) return OPS.OP_0;
  if (buffer.length !== 1) return;
  if (buffer[0] >= 1 && buffer[0] <= 16) return OP_INT_BASE + buffer[0];
  if (buffer[0] === 0x81) return OPS.OP_1NEGATE;
}

export function compile(chunks: Buffer | Array<ScriptChunk>): Buffer {
  if (Buffer.isBuffer(chunks)) return chunks;

  const bufferSize: number = (chunks.reduce(function (accum: number, chunk) {
    if (Buffer.isBuffer(chunk)) {
      // adhere to BIP62.3, minimal push policy
      if (chunk.length === 1 && asMinimalOP(chunk) !== undefined) {
        return accum + 1;
      }

      return accum + pushdata.encodingLength(chunk.length) + chunk.length;
    } else {
      // opcode
      return accum + 1;
    }
  }, 0.0) as number)

  var buffer = Buffer.alloc(bufferSize);
  var offset = 0;

  chunks.forEach(function (chunk: ScriptChunk) {
    // data chunk
    if (Buffer.isBuffer(chunk)) {
      // adhere to BIP62.3, minimal push policy
      var opcode = asMinimalOP(chunk);
      if (opcode !== undefined) {
        buffer.writeUInt8(opcode, offset);
        offset += 1;
        return;
      }

      offset += pushdata.encode(buffer, chunk.length, offset);
      chunk.copy(buffer, offset);
      offset += chunk.length;

    // opcode
    } else {
      buffer.writeUInt8(chunk, offset);
      offset += 1;
    }
  })

  if (offset !== buffer.length) throw new Error('Could not decode chunks');
  return buffer;
}

export function decompile (buffer: Array<ScriptChunk> | Buffer): Array<ScriptChunk> {
  if (Array.isArray(buffer)) return buffer;

  var chunks = [];
  var i = 0;

  while (i < buffer.length) {
    var opcode = buffer[i];

    // data chunk
    if ((opcode > OPS.OP_0) && (opcode <= OPS.OP_PUSHDATA4)) {
      var d = pushdata.decode(buffer, i);

      // did reading a pushDataInt fail? empty script
      if (d === null) return [];
      i += d.size;

      // attempt to read too much data? empty script
      if (i + d.number > buffer.length) return [];

      var data = Buffer.from(buffer.subarray(i, i + d.number));
      i += d.number;

      // decompile minimally
      var op = asMinimalOP(data);
      if (op !== undefined) {
        chunks.push(op);
      } else {
        chunks.push(data);
      }
    } else {
      chunks.push(opcode);

      i += 1;
    }
  }

  return chunks;
}

export function toASM (chunks: Array<ScriptChunk> | Buffer): string {
  if (Buffer.isBuffer(chunks)) {
    chunks = decompile(chunks);
  }

  return chunks.map(function (chunk) {
    // data?
    if (Buffer.isBuffer(chunk)) {
      var op = asMinimalOP(chunk);
      if (op === undefined) return chunk.toString('hex');
      chunk = op;
    }

    // opcode!
    return REVERSE_OPS[chunk];
  }).join(' ');
}

export function fromASM (asm: string): Buffer {
  return compile(asm.split(' ').map(function (chunkStr: string) {
    // opcode?
    if (OPS[chunkStr] !== undefined) return OPS[chunkStr];
    if (!isHexString(chunkStr)) throw new Error("Expected hex in fromASM");

    // data!
    return Buffer.from(chunkStr, 'hex')
  }))
}

export function isCanonicalPubKey (buffer: Buffer): boolean {
  if (!Buffer.isBuffer(buffer)) return false
  if (buffer.length < 33) return false

  switch (buffer[0]) {
    case 0x02:
    case 0x03:
      return buffer.length === 33
    case 0x04:
      return buffer.length === 65
  }

  return false
}

export function isDefinedHashType (hashType: number): boolean {
  var hashTypeMod = hashType & ~0xc0

  return hashTypeMod > 0x00 && hashTypeMod < 0x04
}