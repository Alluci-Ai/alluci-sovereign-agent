"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.IS_GATEWAY_CONVERTER_FLAG = exports.IS_GATEWAY_FLAG = exports.IS_PBAAS_FLAG = exports.IS_FRACTIONAL_FLAG = exports.IS_TOKEN_FLAG = exports.checkFlag = void 0;
const checkFlag = (integer, flag) => {
    return (flag & integer) == flag;
};
exports.checkFlag = checkFlag;
exports.IS_TOKEN_FLAG = 0x20;
exports.IS_FRACTIONAL_FLAG = 0x01;
exports.IS_PBAAS_FLAG = 0x100;
exports.IS_GATEWAY_FLAG = 0x80;
exports.IS_GATEWAY_CONVERTER_FLAG = 0x200;
