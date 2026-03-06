import { OrdinalVDXFObjectClass } from "./OrdinalVDXFObject";

// Singleton class that exists to create a bidirectional map of ordinals <-> vdxf keys
class _OrdinalVDXFObjectOrdinalMap {
  private keyToOrdinalMap: Map<string, number>;
  private ordinalToKeyMap: Map<number, string>;
  keyToOrdinalClass: Map<string, OrdinalVDXFObjectClass>;

  constructor() {
    this.keyToOrdinalMap = new Map();
    this.ordinalToKeyMap = new Map();
    this.keyToOrdinalClass = new Map();
  }

  private updateOrdinalToKeyMap() {
    this.ordinalToKeyMap = new Map(Array.from(this.keyToOrdinalMap, a => a.reverse() as [number,string]));
  }

  registerOrdinal(ordinal: number, vdxfKey: string, ordinalClass: OrdinalVDXFObjectClass, throwOnDuplicate: boolean = true): void {
    if (this.isRecognizedOrdinal(ordinal) || this.vdxfKeyHasOrdinal(vdxfKey)) {
      if (throwOnDuplicate) throw new Error("Cannot overwrite existing ordinal");
      else return;
    }

    this.keyToOrdinalMap.set(vdxfKey, ordinal);
    this.keyToOrdinalClass.set(vdxfKey, ordinalClass);
    this.updateOrdinalToKeyMap();
  }

  isRecognizedOrdinal(ordinal: number): boolean {
    return this.ordinalToKeyMap.has(ordinal);
  }

  vdxfKeyHasOrdinal(vdxfKey: string): boolean {
    return this.keyToOrdinalMap.has(vdxfKey);
  }

  hasClassForVdxfKey(vdxfKey: string): boolean {
    return this.keyToOrdinalClass.has(vdxfKey);
  }

  getOrdinalForVdxfKey(vdxfKey: string): number {
    return this.keyToOrdinalMap.get(vdxfKey);
  }

  getVdxfKeyForOrdinal(ordinal: number): string {
    return this.ordinalToKeyMap.get(ordinal);
  }

  getClassForVdxfKey(vdxfKey: string): OrdinalVDXFObjectClass {
    return this.keyToOrdinalClass.get(vdxfKey);
  }
}

export const OrdinalVDXFObjectOrdinalMap = new _OrdinalVDXFObjectOrdinalMap();