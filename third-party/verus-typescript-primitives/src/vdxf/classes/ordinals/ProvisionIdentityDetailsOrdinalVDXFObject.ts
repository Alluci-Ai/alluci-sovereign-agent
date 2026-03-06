import { PROVISION_IDENTITY_DETAILS_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { ProvisionIdentityDetails, ProvisionIdentityDetailsJson } from "../provisioning/ProvisionIdentityDetails";

export class ProvisionIdentityDetailsOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: ProvisionIdentityDetails;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<ProvisionIdentityDetails> = {
      data: new ProvisionIdentityDetails()
    }
  ) {
    super(
      {
        type: PROVISION_IDENTITY_DETAILS_VDXF_ORDINAL,
        data: request.data
      },
      ProvisionIdentityDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<ProvisionIdentityDetailsJson>): ProvisionIdentityDetailsOrdinalVDXFObject {
    return new ProvisionIdentityDetailsOrdinalVDXFObject({
      data: ProvisionIdentityDetails.fromJson(details.data)
    })
  }
}