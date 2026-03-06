import { BN } from "bn.js"

export const VERUSPAY_VERSION_3 = new BN(3, 10)
export const VERUSPAY_VERSION_4 = new BN(4, 10)
export const VERUSPAY_VERSION_CURRENT = new BN(4, 10)

export const VERUSPAY_VERSION_FIRSTVALID = new BN(3, 10)
export const VERUSPAY_VERSION_LASTVALID = new BN(4, 10)

export const VERUSPAY_VERSION_SIGNED = new BN('80000000', 16)
export const VERUSPAY_VERSION_MASK = VERUSPAY_VERSION_SIGNED;