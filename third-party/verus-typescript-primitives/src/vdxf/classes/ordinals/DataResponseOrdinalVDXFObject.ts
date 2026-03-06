import { DATA_RESPONSE_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { DataResponseDetails, DataResponseDetailsJson } from "../data/DataResponseDetails";

export class DataResponseOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: DataResponseDetails;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<DataResponseDetails> = {
      data: new DataResponseDetails()
    }
  ) {
    super(
      {
        type: DATA_RESPONSE_VDXF_ORDINAL,
        data: request.data
      },
      DataResponseDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<DataResponseDetailsJson>): DataResponseOrdinalVDXFObject {
    return new DataResponseOrdinalVDXFObject({
      data: DataResponseDetails.fromJson(details.data)
    })
  }
}