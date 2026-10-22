# Second wire mapping (v2) and in-place update of published records

Date: 2026-10-20. Status: accepted. Extends [ADR 0013](0013-bulk-draft-and-publication-route.md);
its review, release, journal and reconcile rules apply unchanged except where this record
says otherwise.

## Context

By the evening of 2026-10-20 the bulk route had published 2,515 records into the PICES
community with the v1 wire. FGDC-2599 was a verified v1 draft, and about 1,308 approved
records had not been drafted yet. When Brett looked at the published records in the
browser, he expected more of the FGDC content to appear as Zenodo fields. The v1 wire
publishes:

- the title, with the suffix " - FGDC XML metadata artifact" on some records;
- the creators and the description;
- the subjects, which include a `pices-metadata-only` keyword;
- resource type `other`;
- the metadata date (`metd`) as the publication date;
- one additional description holding a JSON block of the remaining FGDC fields.

The XML file is restricted.

Brett answered eight questions on 2026-10-20:

1. The XML is public with no license. The use-constraint text becomes a rights statement.
2. FGDC content goes into real fields and the JSON block is dropped. The XML stays attached.
3. The publication date is the citation `pubdate` when it is an exact date, otherwise `metd`.
4. Each record is typed Dataset or Publication›Report by AI classification. The title
   suffix is removed.
5. Map everything:
   - time period to dates (collected);
   - bounding box to a map location;
   - point of contact to contributor `contactperson`, and distributor to `distributor`,
     with names and organisations only and never emails, phones or addresses;
   - purpose, status and update, supplemental information and data quality to additional
     descriptions;
   - use and access constraints to rights;
   - `onlink` to related identifiers;
   - `othercit` to references;
   - place keywords to subjects.
6. The publisher stays "Zenodo".
7. Keep the "Deposited content: descriptive metadata only…" sentence. Drop the
   `pices-metadata-only` keyword.
8. Apply the change to the records already published, by in-place edit (same DOI, new
   revision), after the remaining records are done.

## Decision

### Mapping: `scripts/modern_wire_v2.py`

`build(v1_wire, xml, source_ids, resource_type)` starts from the reviewed v1 wire and the
original XML. It never re-derives a reviewed field. The creators, description and keyword
subjects are carried over, and place keywords were already subjects in v1.

| FGDC | Zenodo (v2) | Rule |
|---|---|---|
| citation title | `title` | v1 title without the artifact suffix |
| citation `pubdate`, else `metainfo/metd` | `publication_date` | exact dates only: YYYY, YYYYMM, YYYYMMDD, MMYYYY when YYYYMM is not a year, "Month YYYY"; years 1800 to 2026 |
| `timeperd` | `dates` (`collected`) | a range becomes an interval; several single dates become their span, with the count noted; a begin date without an end date (499 records) becomes that date, described as "begin date only, no end date in the FGDC record", because the provider accepts only closed EDTF intervals; an unparsed value stays as text |
| `spdom/bounding` | `locations` | Point (only a box of zero width AND height) or Polygon; 180 and -180 are one meridian, so a west bound of 180 reads as -180 and an east bound of -180 as 180 (W 180 / E -180 is the globe); a box of zero width or zero height but not both is a line and stays as text; a box across the date line becomes two Polygon features that meet at ±180, because Zenodo refuses MultiPolygon ("Unsupported value: MultiPolygon", canary of 2026-10-21); an invalid box stays as text, and so do the placeholder box 0, 0, 0, 0 (92 records) and a date-line box wider than 200°, whose west and east bounds are swapped or mis-signed (31 records) |
| `ptcontac`, `distrib` | `contributors` | `contactperson`, then a distinct `distributor`; names and organisations only; a name containing a replacement mark is skipped. An organisation-primary contact is always an organisation, commas included. A person-primary contact is a person when written "Family, Given", or in natural order beside its organisation; without an organisation, a several-word value is an organisation in the person slot ("NOAA Central Library"). All 82 such values follow this rule |
| purpose, `supplinf` | additional description `notes` | labelled paragraphs |
| data quality, process steps | additional description `methods` | labelled paragraphs |
| status and update, native, `resdesc`, ordering, `techpreq`, catalogue identifiers | additional description `technical-info` | labelled paragraphs; also holds any value that did not parse, labelled "as given" |
| `useconst`, `accconst`, `distliab` | `rights` (free text, no license id) | title "Use and access constraints (from the FGDC record; no license is granted)" |
| citation `onlink` | `related_identifiers` (`url`, `describes`) | plain URLs only |
| citation `othercit` | `references` | |
| classification | `resource_type` | `dataset` or `publication-report` |
| none | `access` | `{"record": "public", "files": "public"}` |

An e-mail address inside new free text (additional descriptions and rights) is replaced by
"[e-mail address: see the attached FGDC XML]". This affects four use or access constraints
and one ordering note. The description is carried over from v1 unchanged.

Every v2 record is validated against the pinned InvenioRDM schema when it is built.
`compare` checks the stored record against the wire using the provider tolerances of
`same_text` and `same_plain`, and allows the display title the provider adds to vocabulary
entries.

Offline check over all 3,823 publishable records:

- every record builds and passes the schema;
- every record survives an exact emulation of the provider's sanitiser (marshmallow-utils
  0.15.4, ftfy 6.3.1, bleach 6.4.0) unchanged under `compare`.

### Resource types

Eight reviewer agents classified the 3,830 approved records by what the catalogue entry
describes. A report that mainly presents data counts as a report when the entry describes
the publication.

[docs/readiness/2026-10-20/resource_types.json](../readiness/2026-10-20/resource_types.json)
consolidates their calls: 1,952 dataset and 1,878 publication-report. 188 calls are low
confidence. Eight entries were harmonised where the reviewers typed one group differently:

- library-holding books;
- bibliographic databases;
- one AFSC data report;
- one EPIC system description.

The manifest is pinned by SHA256 in `modern_bulk.RESOURCE_TYPES_SHA`, so changing it needs
a reviewed code change.

### Review

`modern_bulk plan-v2 --base-review <v1 review>` writes the sheet `<batch>-v2`. It holds the
approved members of the v1 review with their v2 wires. Excluded and protected sources are
left out and listed under `skipped`. Membership, twins and duplicates were already settled
by the base review.

Each row keeps:

- the v1 flags, apart from the metadata-date flag, which v2 replaces;
- the v2 flags: `time_period_not_mapped`, `no_map`, `report_with_collection_dates`,
  `value_kept_as_text`, `publication_date_reformatted`, `wide_box` (a map wider than 180°),
  `contact_details_removed`;
- a `v2` summary of the new fields, with each contributor's type and the map's longitude span.

`plan-v2` also requires the live v1 wire to equal the one the base review approved.

A reviewer agent other than the builder records the decisions with `review`, as before.
The review's members carry `wire_version` 2.

### New records

`drafts` with a v2 review creates each pending member directly in the v2 form, and records
`wire_version` 2 in its journal. `release` and `publish` then run as before. The draft and
publication checks compare with the v2 rules and expect public files.

### In-place update of published v1 records

1. `release --action update` names approved v2 members whose record is published with
   wire version 1 from the same original. A release document carries its `action`;
   releases written earlier publish.
2. `update --release` then runs these steps for each record. All requests are journaled
   and paced as in ADR 0013.
   1. `POST /api/records/{id}/draft` (`edit`, 201). The edit draft must equal the published
      v1 wire, with the same identity, DOI pids, files, owner and PICES membership. A
      record somebody changed by hand holds here, before anything is saved.
   2. `PUT /api/records/{id}/draft` (`update`, 200). The body is the v2 wire plus the edit
      draft's own `pids` and `custom_fields`, so nothing else changes. The answer must show
      the v2 metadata, public files and no validation errors.
   3. `POST /api/records/{id}/draft/actions/publish` (`publish`, 202).
   4. `GET /api/records/{id}`. The record must show the v2 metadata, unchanged DOI pids and
      PICES as its default community.
   5. `GET .../files`, with `application/json`.
3. Journal phases: `editing`, `edit-open`, `edit-saved`, `edit-published`, then
   `published` with `wire_version` 2. The v1 hashes move to `update.previous`.
4. `edit`, `update` and `publish` are spent at most once per record. Records journaled
   before these kinds existed load with them unspent; this is the forward migration.
5. `rebind-update --source --review` is a recorded decision for a save the provider refused in
   part. It uses GET only. The edit draft must still be open, the published record must still be
   v1, and no publish may have been sent. The step then points the held update at a newer
   reviewed v2 wire and allows one more save. The canary used it after Zenodo refused
   MultiPolygon.
6. `reconcile` observes a held update by GET only and moves it to the phase the provider
   shows:
   - an open v1 edit draft is `edit-open`;
   - an open v2 edit draft is `edit-saved`;
   - a published v2 record is `edit-published`;
   - a published v1 record with no draft is `editing`.

   A write whose effect is absent is allowed once more.
7. The token may come from the Keychain under the action `bulk-update`. Brett allowed this on 2026-10-21, for both the canary and the full run.

### Order

1. Canary: update one published record and show it to Brett in the browser before any
   scaled run.
2. The remaining batches: v2 sheets and reviews, then drafts and publication directly in
   v2. FGDC-2599 publishes from its existing v1 draft under its v1 release, then updates
   like the rest.
3. Update the 2,515 published records.

## Consequences

- Each of the 2,516 v1 records gets one new revision under the same DOI. DataCite receives
  the new metadata when each edit is published.
- An update costs five requests. At the 0.8-second pace, 2,516 updates take about three to
  four hours.
- The shape of an edit draft is an assumption about InvenioRDM that the canary verifies:
  - `is_published` true;
  - status `published`;
  - file entries listed.

  A record whose edit draft differs holds before its PUT, and its published version is
  untouched.
- Zenodo might demand something for public files that v2 does not send, such as a license.
  If so, the PUT reports validation errors and the record holds before publication.
- Each record has one update. Another mapping change would need new write kinds, or a
  reviewed reset of the edit counts.
- The 188 low-confidence types are AI calls. Brett can rule on any group, and a change is
  another in-place update.

## Canary, 2026-10-21

The first canary was FGDC-985, record 23508755. It ran these requests:

1. Opened the edit draft and checked it against the published v1 record.
2. Saved the v2 wire. Zenodo answered 200, listed one error, `metadata.locations.features.0.geometry.type: Unsupported value: MultiPolygon`, and stored everything else, without the geometry.
3. Compared the saved draft with the wire. The comparison failed and held the record before publication.

The published record was unchanged. The pinned storage schema accepts MultiPolygon; the service schema does not. Date-line boxes therefore became two Polygon features. The batch was re-sheeted as `bulk-005-v2b` and re-reviewed. `rebind-update` then pointed the held canary at the new wire.
