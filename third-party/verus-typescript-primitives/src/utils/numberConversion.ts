import { BN } from 'bn.js';
import { BigNumber } from '../utils/types/BigNumber';

/**
 * Converts a BN instance to a number with 8 decimal places.
 * @param value BN instance representing the integer value (multiplied by 1e8)
 * @returns number with 8 decimal places
 */
export function bnToDecimal(value: BigNumber): string {
    var input = new BN(value);
    const divisor = new BN('100000000');
    const isNegative = input.isNeg();
    const absInput = input.abs();

    const integerPart = absInput.div(divisor).toString();
    let decimalPart = absInput.mod(divisor).toString();

    // Remove trailing zeros from decimal part
    while (decimalPart.length < 8) {
        decimalPart = '0' + decimalPart;
    }

    if (decimalPart === '00000000') {
        return (isNegative ? '-' : '') + integerPart;
    } else {
        // Remove trailing zeros from the right of decimalPart
        decimalPart = decimalPart.replace(/0+$/, '');
    }

    const resultStr = (isNegative ? '-' : '') + integerPart + '.' + decimalPart;
    return resultStr;
}

/**
 * Converts a decimal number (string or number) to a BN instance representing the integer value (multiplied by 1e8)
 * Uses string manipulation to avoid floating point errors.
 * @param value number or string representing a number with up to 8 decimal places (e.g., "1000000000.11111111" or 1000000000.11111111)
 * @returns BN instance
 */
export function decimalToBn(value: string | number): BigNumber {
    const valueStr = typeof value === 'number' ? value.toString() : value;
    const isNegative = valueStr.startsWith('-');
    const absValue = isNegative ? valueStr.slice(1) : valueStr;
    const [integerPart, decimalPart = ''] = absValue.split('.');
    const paddedDecimal = (decimalPart + '00000000').slice(0, 8);
    const bnStr = integerPart + paddedDecimal;
    const bn = new BN(bnStr);
    return isNegative ? bn.neg() : bn;
}