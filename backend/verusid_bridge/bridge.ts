import VerusIdInterface from "./verusid-ts-client/src/VerusIdInterface";
import {
    LoginConsentChallenge,
    LoginConsentResponse,
    RequestedPermission,
    RedirectUri,
    IDENTITY_VIEW,
    LOGIN_CONSENT_WEBHOOK_VDXF_KEY
} from "./verus-typescript-primitives/src";
import type { AxiosRequestConfig } from 'axios';

async function main() {
    const args = process.argv.slice(2);
    if (args.length < 2) {
        console.error("Usage: tsx bridge.ts <command> <json_payload>");
        process.exit(1);
    }

    const command = args[0];
    const payload = JSON.parse(args[1]);

    if (command === "create-request") {
        const { signing_id, wif, challenge_id, redirect_uri, rpc_url, rpc_user, rpc_pass } = payload;

        const config: AxiosRequestConfig = {
            auth: (rpc_user && rpc_pass) ? { username: rpc_user, password: rpc_pass } : undefined
        } as AxiosRequestConfig;

        const verusIdClient = new VerusIdInterface("i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV", rpc_url, config);

        const challenge = new LoginConsentChallenge({
            challenge_id: challenge_id,
            requested_access: [
                new RequestedPermission(IDENTITY_VIEW.vdxfid)
            ],
            redirect_uris: [
                new RedirectUri(redirect_uri, LOGIN_CONSENT_WEBHOOK_VDXF_KEY.vdxfid)
            ],
            created_at: Math.floor(Date.now() / 1000)
        });

        const request = await verusIdClient.createLoginConsentRequest(signing_id, challenge, wif);
        console.log(JSON.stringify({
            request: request.toJson(),
            deeplink: request.toWalletDeeplinkUri()
        }));
    } else if (command === "verify-response") {
        const { response, rpc_url, rpc_user, rpc_pass } = payload;

        const config: AxiosRequestConfig = {
            auth: (rpc_user && rpc_pass) ? { username: rpc_user, password: rpc_pass } : undefined
        } as AxiosRequestConfig;

        const verusIdClient = new VerusIdInterface("VRSC", rpc_url, config);
        const loginResponse = new LoginConsentResponse(response);

        const verified = await verusIdClient.verifyLoginConsentResponse(loginResponse);

        console.log(JSON.stringify({
            verified,
            signing_id: loginResponse.signing_id,
            decision: loginResponse.decision.toJson()
        }));
    } else {
        console.error("Unknown command:", command);
        process.exit(1);
    }
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
