import { DATA_PACKET_REQUEST_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";
import { DataPacketRequestDetails, DataPacketRequestDetailsJson } from "../data/DataPacketRequestDetails";

export class DataPacketRequestOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: DataPacketRequestDetails;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<DataPacketRequestDetails> = {
      data: new DataPacketRequestDetails()
    }
  ) {
    super(
      {
        type: DATA_PACKET_REQUEST_VDXF_ORDINAL,
        data: request.data
      },
      DataPacketRequestDetails
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<DataPacketRequestDetailsJson>): DataPacketRequestOrdinalVDXFObject {
    return new DataPacketRequestOrdinalVDXFObject({
      data: DataPacketRequestDetails.fromJson(details.data)
    })
  }
}
