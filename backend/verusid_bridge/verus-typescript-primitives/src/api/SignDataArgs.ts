export type SignDataArgs = {
    address?: string;
    filename?: string;
    message?: string;
    messagehex?: string;
    messagebase64?: string;
    datahash?: string;
    vdxfdata?: string;
    mmrdata?: Array<any>;
    mmrsalt?: Array<string>;
    mmrhashtype?: string;
    priormmr?: Array<string>;
    vdxfkeys?: Array<string>;
    vdxfkeynames?: Array<string>;
    boundhashes?: Array<string>;
    hashtype?: string;
    signature?: string;
    encrypttoaddress?: string;
    createmmr?: boolean;
}
