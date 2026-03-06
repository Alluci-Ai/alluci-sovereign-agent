import { USER_DATA_REQUEST_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { UserDataRequestDetails, UserDataRequestJson } from "../data/UserDataRequestDetails";

export class UserDataRequestOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: UserDataRequestDetails;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<UserDataRequestDetails> = {
      data: new UserDataRequestDetails()
    }
  ) {
    super(
      {
        type: USER_DATA_REQUEST_VDXF_ORDINAL,
        data: request.data
      },
      UserDataRequestDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<UserDataRequestJson>): UserDataRequestOrdinalVDXFObject {
    return new UserDataRequestOrdinalVDXFObject({
      data: UserDataRequestDetails.fromJson(details.data)
    })
  }
}
