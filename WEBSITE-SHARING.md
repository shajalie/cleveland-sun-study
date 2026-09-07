# Email-controlled website sharing

Open Connection options in the PC dashboard. Website sharing lets approved emails open a dedicated HTTPS site and operate the live scene rendered by the PC. Viewers need only a browser. They enter their approved email and the login code Cloudflare sends them. Tailscale, Moonlight and Blender are unnecessary for this mode.

## First connection on a computer
Use Google Chrome and START-DAYLIGHT.cmd. Enter allowed email addresses, including your own. Under One-time Cloudflare connection, enter your Cloudflare account ID, active domain zone ID, an unused subdomain such as daylight.yourdomain.com, and a scoped API token. Complete a Cloudflare Zero Trust team setup once if you have not already. Then select Enable website sharing.

The API token needs Account permissions: Cloudflare Tunnel Edit; Access: Apps and Policies Edit; Access: Organizations, Identity Providers, and Groups Edit. Zone permissions: Zone Read; DNS Edit. Restrict account resources to the chosen account and zone resources to the chosen domain. Do not paste credentials into chat or commit them.

The program creates its own email-code login policy, Access application, outbound tunnel, and DNS record. It refuses a hostname with an existing DNS record. It installs no inbound router forwarding. Creation starts only after input validation; Access protection is configured before DNS or a tunnel process starts. Failed partial setup remains disabled locally and retains the created IDs for a safe retry.

## Use and revoke access
Copy the generated website link or scan its QR code. Share this email-protected link directly with invited people; no secret pairing key appears in it. Save allowed emails updates access. Removed viewers are disconnected, and already-issued login tokens are rejected locally. Turn off stops the website connector and closes website sessions immediately. Local/Moonlight and optional Tailscale remain separate.

One renderer has one shared camera; approved viewers can operate its controls. Keep the PC running. The launcher prevents sleep during hosting. When a configured host restarts, its enabled connection resumes. If the connector cannot start, the dashboard reports that state.

## Credentials and transfer
Hosting credentials are protected with Windows DPAPI for the current Windows user. They are passed to the connector without putting secrets on its command line. The ZIP excludes every .runtime file, including email lists, IDs, credentials, profiles and local pairing keys. A different computer needs its own first-time connection and unused hostname. Do not share your account-wide API token with untrusted PC operators.

The bundled connector is Cloudflare cloudflared 2026.8.3, fetched from its official release and checked against SHA-256 recorded in remote/cloudflared-release.json. It is separate from the GPU renderer, which uses Chrome only.

## Website and authentication boundaries
The original chatgpt.site page is still an owner-controlled launcher. It can remember a dedicated HTTPS website link, but its own ChatGPT audience is managed separately. Share the new dedicated link with your allowed email list so those people do not need access to your original ChatGPT Site.

The dedicated website uses Cloudflare email-code authentication rather than ChatGPT sign-in. Cloudflare and the host verify signed Access tokens, including issuer, audience, expiration and allowed email. A separate loopback listener accepts the tunnel and cannot use local pairing cookies to bypass email authentication. Sharing settings and credentials can only be managed from the authenticated local PC dashboard. Network/authentication failure does not fall back to phone rendering or public access.

## Verification
npm run test:sharing verifies signed-token checks, malformed identities, allowlist removal, disable behavior and protection-before-DNS sequencing using a simulated Cloudflare API. node tests/sharing-isolation.mjs checks the running host rejects pairing bypasses and remote administration and verifies Windows credential encryption. Live activation was verified on the RTX 2060 host: Cloudflare provisioning, a healthy tunnel, email-code sign-in in Chrome, received images and remote floor controls. See sharing-validation.json. An RTX 5090 and a physical phone were not available for this validation.

Technical references: https://developers.cloudflare.com/tunnel/ ; https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/ ; https://developers.cloudflare.com/api/resources/zero_trust/access/policies/ ; https://github.com/cloudflare/cloudflared/releases/tag/2026.8.3
