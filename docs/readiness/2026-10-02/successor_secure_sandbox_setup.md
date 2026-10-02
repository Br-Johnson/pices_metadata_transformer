# Successor sandbox access preparation

Status: instructions only. No credential provisioned, authenticated probe run,
or provider write authorized by this document. Proceed only after independent
review clears the combined code and Brett approves secure sandbox provisioning.

## User-only secure setup after clearance

1. Sign in to the intended account on https://sandbox.zenodo.org/ and open its
   Applications / personal access tokens settings. Create a dedicated sandbox
   token with **deposit:write only**. Do not select deposit:actions or use a
   production token. Zenodo documents deposit:write as permitting draft writes
   without publication; it also permits deletion, which remains unauthorized.
2. In this working cloud environment's configuration, select **Manage** beside
   **Network secrets**. Set **Key** to `ZENODO_SANDBOX_TOKEN`, enter the actual
   token only in the secure **Value** field, and set **Allowed domains** to
   `sandbox.zenodo.org` only. Do not create a same-named direct environment
   variable. Save the configuration; retain the resulting saved version identity
   and use a task running that version.
3. Report only that provisioning is complete and the saved configuration version.
   Never send the token or placeholder in chat, logs, files, `.env`, Library, or
   source code. Do not provision `ZENODO_PRODUCTION_TOKEN` at this stage.

Network secrets expose a placeholder to the process; the HTTPS proxy substitutes
its value for approved domains on port 443. The code validates printable ASCII
without whitespace, then forwards valid placeholder bytes unchanged in Bearer
headers. It does not invent or resolve placeholder syntax. If the platform's
placeholder does not pass validation, stop and inspect its format without
printing its value; never convert it or switch to raw credentials as a workaround.

## Post-approval read-only verification and write boundary

The integration owner first checks only configuration presence, then performs a
bounded authenticated `GET https://sandbox.zenodo.org/api/deposit/depositions`
with no redirects and no token/header/body logging. Require HTTP 200 and the
expected JSON collection shape; preserve a sanitized timestamp/status receipt.
A successful response establishes token substitution and API access, not intended
account ownership by itself. Verify the intended account using user confirmation
and owned-deposition inventory before selecting any write. Do not invoke the
module's generic test/create helpers. The normal client constructor performs a
GET, so client creation itself must wait for approval.

Before any provider write, independently verify the exact synthetic canary
payload and attachment checksums, unique run label, isolated durable ledger,
sandbox-only destination and zero publication/deletion actions. The first write
selection is **one synthetic draft**, followed by file upload, exact readback and
an unchanged retry proving zero second creates. A separately verified bounded
actual-source selection can follow; no production selection is authorized here.
A transport success does not clear source, rights, duplicate, identity or release
QA. Preserve five historical production identities and exclude poster 10042430.

## Official references checked 2026-10-02

- [Cloud environments: environment variables and network secrets](https://learn.chatgpt.com/docs/environments/cloud-environments#configure-environment-variables-and-network-secrets)
- [Zenodo developer documentation: personal access tokens and scopes](https://developers.zenodo.org/#authentication)

Current source-only cohort remains 1,406 supported / 2,794 held / six malformed.
The 585-member Contributor-or-Source question (582 access-only holds) awaits
Brett's interpretation; Contact Source approval does not extend to that wording.
