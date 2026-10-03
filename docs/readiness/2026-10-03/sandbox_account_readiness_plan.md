# Read-only Sandbox account readiness plan

Prepared for the sole provider executor; **not executed by the code owner**.
Both HTTP500 create attempts stay permanently spent. The separately authorized
two-GET creation-window reconciliation is a different task. This plan adds no
POST and resets no grant, state, journal, ledger or clock.

Zenodo documents `deposit:write` as required for creation and metadata updates,
and Sandbox accounts/tokens as separate. A successful owned-record GET does not
establish write scope. See [official API authentication and creation documentation](https://developers.zenodo.org/#authentication).
The [account instructions](https://help.zenodo.org/docs/get-started/create-an-account/)
require email confirmation before a first upload for the described local/ORCID
signup flows. These identify checks; they do not establish either HTTP500's cause.

Brett now reports that the Sandbox token has write access and that no email
verification option appears. Preserve that evidence as `USER_REPORTED`; do not
label email status as the cause or require guessed account setup before continuing
diagnosis. The optional UI inspection below can add visible evidence if available.
An absent email-status control is `not_visible`, not a new blocker.

No supported token-introspection or email-verification REST endpoint was found in
the reviewed public API documentation. Do not invent `/api/user`, introspection
probes or write-based tests. Read-only inspection of existing Sandbox account
settings is the supported user-interface alternative.

After parent dispatch, the provider executor can inspect its existing authenticated
Sandbox account session and Applications/personal-token entry. Establish which
already-known token label belongs to the configured credential using existing
private provenance, without opening, copying, printing, comparing or decoding the
token value. If label binding is unavailable, report `not_established`; a successful
GET cannot supply it. Read only visible scope and account status. Do not create or
revoke tokens, change settings, send confirmation mail or upload.

Return only a minimal sanitized receipt:

```json
{
  "environment": "sandbox",
  "check_mode": "existing_account_ui_read_only",
  "token_entry_binding": "verified_or_not_established",
  "deposit_write_scope": "user_reported_present",
  "visible_deposit_write_scope": "present_absent_or_not_visible",
  "email_confirmation": "confirmed_unconfirmed_or_not_visible",
  "account_matches_existing_private_owner_evidence": "verified_or_not_established",
  "provider_writes": 0,
  "new_create_attempts": 0,
  "failed_allowances_reset": false
}
```

Record time/provenance of visible labels/status privately. Share no token value,
email address, account page body, screenshot or unrelated account details. Missing
`deposit:write` or an explicitly contradictory visible account status can be
reported as new evidence; neither permits another POST. A control that is not
visible supplies no diagnosis and creates no guessed prerequisite. Server failure
remains unresolved; further provider execution belongs to the parent. No additional
API request is proposed by this plan.
