import { AUTHENTICATION_REQUEST_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { AuthenticationRequestDetails, AuthenticationRequestDetailsJson } from "../login/AuthenticationRequestDetails";

export class AuthenticationRequestOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: AuthenticationRequestDetails;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<AuthenticationRequestDetails> = {
      data: new AuthenticationRequestDetails()
    }
  ) {
    super(
      {
        type: AUTHENTICATION_REQUEST_VDXF_ORDINAL,
        data: request.data
      },
      AuthenticationRequestDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<AuthenticationRequestDetailsJson>): AuthenticationRequestOrdinalVDXFObject {
    return new AuthenticationRequestOrdinalVDXFObject({
      data: AuthenticationRequestDetails.fromJson(details.data)
    })
  }
}