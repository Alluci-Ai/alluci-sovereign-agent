import { APP_ENCRYPTION_REQUEST_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { AppEncryptionRequestDetails, AppEncryptionRequestDetailsJson } from "../appencryption/AppEncryptionRequestDetails";

export class AppEncryptionRequestOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: AppEncryptionRequestDetails;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<AppEncryptionRequestDetails> = {
      data: new AppEncryptionRequestDetails()
    }
  ) {
    super(
      {
        type: APP_ENCRYPTION_REQUEST_VDXF_ORDINAL,
        data: request.data
      },
      AppEncryptionRequestDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<AppEncryptionRequestDetailsJson>): AppEncryptionRequestOrdinalVDXFObject {
    return new AppEncryptionRequestOrdinalVDXFObject({
      data: AppEncryptionRequestDetails.fromJson(details.data)
    })
  }
}