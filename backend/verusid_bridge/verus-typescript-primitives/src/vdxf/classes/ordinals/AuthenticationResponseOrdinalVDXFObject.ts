import { AUTHENTICATION_RESPONSE_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { AuthenticationResponseDetails, AuthenticationResponseDetailsJson } from "../login/AuthenticationResponseDetails";

export class AuthenticationResponseOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: AuthenticationResponseDetails;

  constructor(
    response: OrdinalVDXFObjectInterfaceTemplate<AuthenticationResponseDetails> = {
      data: new AuthenticationResponseDetails()
    }
  ) {
    super(
      {
        type: AUTHENTICATION_RESPONSE_VDXF_ORDINAL,
        data: response.data
      },
      AuthenticationResponseDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<AuthenticationResponseDetailsJson>): AuthenticationResponseOrdinalVDXFObject {
    return new AuthenticationResponseOrdinalVDXFObject({
      data: AuthenticationResponseDetails.fromJson(details.data)
    })
  }
}