import { SerializableEntity } from "../utils/types/SerializableEntity";
import { Hash160 } from "../vdxf/classes";
import { Hash160SerEnt } from "../vdxf/classes/Hash160";

export class NoDestination extends Hash160SerEnt implements SerializableEntity {
  constructor() {
    super(Buffer.alloc(0), 0, false);
  }

  fromBuffer(buffer: Buffer, offset?: number): number {
    return offset;
  }
}