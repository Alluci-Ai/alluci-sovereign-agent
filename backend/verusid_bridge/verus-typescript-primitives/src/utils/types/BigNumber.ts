import { BN } from "bn.js";

// Hack to force BigNumber to get typeof class instead of BN namespace
const BNClass = new BN(0);

export type BigNumber = typeof BNClass;