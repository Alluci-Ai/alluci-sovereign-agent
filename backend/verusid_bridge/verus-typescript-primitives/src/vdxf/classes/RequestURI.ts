import { BN } from "bn.js";
import { BigNumber } from "../../utils/types/BigNumber";
import { ResponseURI, ResponseURIJson } from "./ResponseURI";

export type RequestURIJson = ResponseURIJson;

export class RequestURI extends ResponseURI {
  constructor(data?: {
    uri?: Buffer,
    type?: BigNumber
  }) {
    super(data);

    if (this.type == null) {
      this.type = ResponseURI.TYPE_POST;
    }

    if (this.uri == null) {
      this.uri = Buffer.alloc(0);
    }

    this.assertPostType();
  }

  static fromUriString(str: string): RequestURI {
    return new RequestURI({ uri: Buffer.from(str, 'utf-8'), type: ResponseURI.TYPE_POST });
  }

  fromBuffer(buffer: Buffer, offset?: number): number {
    const newOffset = super.fromBuffer(buffer, offset);

    this.assertPostType();

    return newOffset;
  }

  static fromJson(json: RequestURIJson): RequestURI {
    return new RequestURI({
      type: new BN(json.type, 10),
      uri: Buffer.from(json.uri, 'utf-8')
    });
  }

  private assertPostType() {
    if (!this.type.eq(ResponseURI.TYPE_POST)) {
      throw new Error("RequestURI type must be TYPE_POST");
    }
  }
}
