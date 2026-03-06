import { DATA_DESCRIPTOR_VDXF_ORDINAL } from "../../../constants/ordinals/ordinals";
import { DataDescriptor, DataDescriptorJson } from "../../../pbaas";
import { SerializableDataEntity } from "../../../utils/types/SerializableEntity";
import { OrdinalVDXFObjectInterfaceTemplate, OrdinalVDXFObjectJsonTemplate } from "./OrdinalVDXFObject";
import { SerializableEntityOrdinalVDXFObject } from "./SerializableEntityOrdinalVDXFObject";

export class DataDescriptorOrdinalVDXFObject extends SerializableEntityOrdinalVDXFObject implements SerializableDataEntity {
  data: DataDescriptor;

  constructor(
    request: OrdinalVDXFObjectInterfaceTemplate<DataDescriptor> = {
      data: new DataDescriptor()
    }
  ) {
    super(
      {
        type: DATA_DESCRIPTOR_VDXF_ORDINAL,
        data: request.data
      },
      DataDescriptor
    );
  }

  static fromJson(details: OrdinalVDXFObjectJsonTemplate<DataDescriptorJson>): DataDescriptorOrdinalVDXFObject {
    return new DataDescriptorOrdinalVDXFObject({
      data: DataDescriptor.fromJson(details.data)
    })
  }
}