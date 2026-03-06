import { OPS } from "../../utils/ops";
import { ScriptChunk } from "../../utils/script";
import { SerializableEntity } from "../../utils/types/SerializableEntity";
import { OptCCParams } from "../OptCCParams";
import { VerusScript } from "./VerusScript";

export class SmartTransactionScript extends VerusScript implements SerializableEntity {
  protected master: OptCCParams;
  protected params: OptCCParams;

  constructor(master?: OptCCParams, params?: OptCCParams) {
    super(master == null || params == null ? [] : SmartTransactionScript.getChunks(master, params));

    this.master = master;
    this.params = params;
  }

  static getChunks(master: OptCCParams, params: OptCCParams): Array<ScriptChunk> {
    return [
      master.toChunk(),
      OPS.OP_CHECKCRYPTOCONDITION,
      params.toChunk(),
      OPS.OP_DROP
    ]
  }

  private updateChunks(): void {
    this.chunks = SmartTransactionScript.getChunks(this.master, this.params);
  }

  fromBuffer(
    buffer: Buffer,
    offset?: number,
    length?: number
  ): number {
    const _offset = super.fromBuffer(buffer, offset, length);

    this.master = OptCCParams.fromChunk(this.chunks[0] as Buffer);
    this.params = OptCCParams.fromChunk(this.chunks[2] as Buffer);

    return _offset;
  }

  toBuffer(): Buffer {
    this.updateChunks();
    return super.toBuffer();
  }

  getByteLength(): number {
    this.updateChunks();
    return super.getByteLength();
  }

  set masterOptCC(master: OptCCParams) {
    this.master = master;
    this.updateChunks();
  }

  set paramsOptCC(params: OptCCParams) { 
    this.params = params;
    this.updateChunks();
  }

  get masterOptCC(): OptCCParams {
    return this.master;
  }

  get paramsOptCC(): OptCCParams {
    return this.params;
  }
}