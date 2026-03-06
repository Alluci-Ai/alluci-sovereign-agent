import { ApiResponse } from "../../ApiResponse";

export class GetInfoResponse extends ApiResponse {
  result: {
    version: number;
    protocolversion: number;
    VRSCversion: string;
    notarized: number;
    prevMoMheight: number;
    notarizedhash: string;
    notarizedtxid: string;
    notarizedtxid_height: string;
    KMDnotarized_height: number;
    notarized_confirms: number;
    blocks: number;
    longestchain: number;
    timeoffset: number;
    tiptime: number;
    connections: number;
    proxy: string;
    difficulty: number;
    testnet: boolean;
    paytxfee: number;
    relayfee: number;
    errors: string;
    CCid: number;
    name: string;
    p2pport: number;
    rpcport: number;
    magic: number;
    premine: number;
    eras: number;
    reward: string;
    halving: string;
    decay: string;
    endsubsidy: string;
    veruspos: number;
    chainid?: string;
    notarychainid?: string;
  };
}