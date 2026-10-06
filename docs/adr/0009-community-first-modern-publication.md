# Community-first modern singleton publication

Date: 2026-10-06. Status: implemented; focused checks passed, final PR review/CI recorded separately.
Scope: one reviewed production singleton per invocation. This decision replaces
the publish-then-inclusion sequence in [ADR 0006](0006-finite-modern-singleton-publication.md).
It changes neither finite source coverage nor provider authorization.

## Source evidence and decision

RDM commit `d4a4ef21ef5cd99b6d1350b537c82581799296a3` defines the
[draft review and submit-review routes](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/resources/config.py#L247).
Its [review service](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/services/review/service.py#L124)
can replace an existing review during update. Submission checks draft management
and community submission permissions; `require_review:false` may proceed to
community inclusion. Its [community-submission acceptance action](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/requests/community_submission.py#L36)
adds the selected community/default and an applicable parent before publishing.
The pinned [draft status mapping](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/records/systemfields/draft_status.py#L29)
requires `draft_with_review` after attachment.
These pinned implementation facts support the route; they do not prove actual
production policies, permissions or deployed behavior.

Choose the community before submission can publish. Require actual independently
reviewed Mac PICES identity/hierarchy/permission captures, saved-response record QA,
independent program review, separate human release and a new bounded v2 grant
before either write. The initial five-GET draft/XML fence must show no existing
record or parent review. Permit one PUT to attach the exact PICES review, then
five GETs that preserve metadata/XML/identity and the known review while observing
a stable, nondecreasing draft revision. Assume no fixed revision increment or
server-side compare-and-swap; retain exclusive-writer authority.

Only then permit one submit-review POST with `require_review:false`. Observe the
known request, and require accepted status plus a full five-GET published
record/file fence with exact original XML, metadata, record/parent/file identities
and actual PICES membership/default. Callers must require `release_complete:true`;
submission, acceptance alone or returned DOIs do not complete release. DOI
registration remains a separate observation.

## State and recovery consequences

The v2 grant permits at most 22 GETs, one review PUT and one submission POST within
600 seconds. It binds the current preparation/runtime, original state root, exact
QA/release inputs and reviewed community authority. Keep the canonical v1
publication journal/intent paths and schema-1 container; new rows carry protocol
`community-first-v2`. Never migrate or reopen an old own-source attempt. Retain
the explicit PR39 draft-runtime bridge and original upload history.

Durably spend each action before dispatch. Pending or uncertain results stay
incomplete; GET-only recovery uses the same unexpired grant and remaining budget.
Pending beyond expiry requires separately reviewed read-only continuation that
preserves the original attempt/counts. This decision adds no such automatic
continuation, new write allowance, direct-publish fallback, accept/delete action
or request search. Positive remote XML matches preserve existing IDs/DOIs;
unknown history is not duplicate absence and cannot justify fabricated journals.

The [executable handoff](../readiness/2026-10-06/modern_pices_community_handoff.md)
owns CLI, evidence and exact fence details. Staged focused-test evidence is retained there; the PR owns final-head review and
actual CI results. This ADR grants no live action.
