export interface SerializableEntity {
  toBuffer(): Buffer;
  fromBuffer(buffer: Buffer, offset?: number, ...additionalArgs: any[]): number;
  getByteLength(): number;
}

export interface SerializableDataEntity {
  getDataByteLength(): number;
  toDataBuffer(): Buffer;

  // fromDataBuffer doesn't get passed an offset because it gets passed only the varslice of the buffer it is meant to interpret.
  fromDataBuffer(buffer: Buffer): void;
}