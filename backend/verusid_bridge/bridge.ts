import { VerusIdInterface } from 'verusid-ts-client';
import {
  LoginConsentChallenge,
  LoginConsentResponse,
  RequestedPermission,
  IDENTITY_VIEW,
  RedirectUri,
  LOGIN_CONSENT_WEBHOOK_VDXF_KEY,
  toBase58Check
} from 'verus-typescript-primitives';

const I_ADDR_VERSION = 102;
import { randomBytes } from 'crypto';
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
        const { signing_id, wif, redirect_uri, rpc_url, rpc_user, rpc_pass, system_id } = payload;

        const config: AxiosRequestConfig = {
            auth: (rpc_user && rpc_pass) ? { username: rpc_user, password: rpc_pass } : undefined
        } as AxiosRequestConfig;

        // Use system_id if provided, default to VRSC iaddress
        const verusIdClient = new VerusIdInterface(system_id || "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV", rpc_url, config as any);

        const randID = randomBytes(20);
        const challengeId = toBase58Check(randID, I_ADDR_VERSION);

        const challenge = new LoginConsentChallenge({
            challenge_id: challengeId,
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
            deeplink: request.toWalletDeeplinkUri(),
            challenge_id: challengeId
        }));
    } else if (command === "verify-response") {
        const { response, rpc_url, rpc_user, rpc_pass, system_id } = payload;

        const config: AxiosRequestConfig = {
            auth: (rpc_user && rpc_pass) ? { username: rpc_user, password: rpc_pass } : undefined
        } as AxiosRequestConfig;

        const verusIdClient = new VerusIdInterface(system_id || "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV", rpc_url, config as any);
        
        // verusid-ts-client handle verification directly with the raw response
        const verified = await verusIdClient.verifyLoginConsentResponse(response);

        console.log(JSON.stringify({
            verified: verified,
            signing_id: response.signing_id,
            decision: response.decision ? response.decision.toJson() : null
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
