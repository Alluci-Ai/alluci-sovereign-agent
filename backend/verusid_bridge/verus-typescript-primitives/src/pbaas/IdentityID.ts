import { I_ADDR_VERSION } from '../constants/vdxf';
import { SerializableEntity } from '../utils/types/SerializableEntity';
import { Hash160SerEnt } from '../vdxf/classes/Hash160';

export class IdentityID extends Hash160SerEnt implements SerializableEntity {
  constructor(
    hash: Buffer = Buffer.alloc(0)
  ) {
    super(hash, I_ADDR_VERSION, false);
  }

  fromBuffer(buffer: Buffer, offset: number = 0): number {
    const ret = super.fromBuffer(buffer, offset, false);

    this.version = I_ADDR_VERSION;
    
    return ret;
  }

  static fromAddress(address: string, varlength?: boolean): Hash160SerEnt {
    return new IdentityID(Hash160SerEnt.fromAddress(address, false).hash);
  }
}