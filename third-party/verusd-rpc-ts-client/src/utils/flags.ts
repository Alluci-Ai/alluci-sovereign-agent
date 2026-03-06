export const checkFlag = (integer: number, flag: number): boolean => {
  return (flag & integer) == flag;
}

export const IS_TOKEN_FLAG = 0x20;
export const IS_FRACTIONAL_FLAG = 0x01;
export const IS_PBAAS_FLAG = 0x100;
export const IS_GATEWAY_FLAG = 0x80;
export const IS_GATEWAY_CONVERTER_FLAG = 0x200;