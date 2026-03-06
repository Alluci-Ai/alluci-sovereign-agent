import { APP_ENCRYPTION_RESPONSE_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { AppEncryptionResponseDetails, AppEncryptionResponseDetailsJson } from "../appencryption/AppEncryptionResponseDetails";

export class AppEncryptionResponseOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: AppEncryptionResponseDetails;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<AppEncryptionResponseDetails> = {
      data: new AppEncryptionResponseDetails()
    }
  ) {
    super(
      {
        type: APP_ENCRYPTION_RESPONSE_VDXF_ORDINAL,
        data: request.data
      },
      AppEncryptionResponseDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<AppEncryptionResponseDetailsJson>): AppEncryptionResponseOrdinalVDXFObject {
    return new AppEncryptionResponseOrdinalVDXFObject({
      data: AppEncryptionResponseDetails.fromJson(details.data)
    })
  }
}