# Morning source-meaning decision bundle

The existing archival rehosting authority and exact Contact Source /
Contributor-or-Source interpretations remain unchanged. No new blanket license
or permission is requested here. Source/hash memberships for the **90 retained
access holds** are in [the unchanged decision receipt](joint_collection_source_decisions.json),
SHA-256 `8b94c19e501c060c458a5a71cfe0ebd123701f8101f659f34406e77e394a9b37`.

For each of the nine bound partitions below, clarify whether the exact text
repeated in metadata access/use fields governs **only the underlying GIS/data
acquisition or use**, or **also restoration of the descriptive XML**. If it also
governs XML, identify the actual XML-specific conditions. Keep every original
wording, restricted access and blank license; a scope answer is not a reuse grant.

| Bound partition | Representative original | Exact terms needing scope |
| --- | --- | --- |
| Ecotrust — 30 | [FGDC-568](../../../FGDC/FGDC-568.xml) | `Data transfer costs will be based on staff time and media costs.` / `Data may not be sold.` |
| Ecotrust — 2 | [FGDC-567](../../../FGDC/FGDC-567.xml) | Same transfer costs / `The easiest transfer format is UNIX tar with 8mm tape.` |
| Ecotrust — 2 | [FGDC-638](../../../FGDC/FGDC-638.xml) | `Available upon request at cost of copy media.` / `Unknown` |
| Ecotrust — 1 | [FGDC-641](../../../FGDC/FGDC-641.xml) | `Contact Chugach National Forest` / `Unknown` |
| Ecotrust — 1 | [FGDC-707](../../../FGDC/FGDC-707.xml) | `Requestor must complete GIS Starter  Kit Data Agreement stating Terms and Conditions for use of Starter Kit Data.` / DNR scale/order wording |
| USDA/DNR — 29 | [FGDC-696](../../../FGDC/FGDC-696.xml) | Same agreement requirement with single-space `Starter Kit` / DNR scale/order wording |
| USDA/DNR — 1 | [FGDC-739](../../../FGDC/FGDC-739.xml) | All four source constraint fields are `Unknown` |
| USDA/DNR — 1 | [FGDC-799](../../../FGDC/FGDC-799.xml) | `Data available as part of DNR's GIS Starter kit in modular format.` / DNR scale/order wording |
| Unaami — 23 | [FGDC-545](../../../FGDC/FGDC-545.xml) | `Please acknowledge the Unaami Data Collection and the original source of the data.` |

The exact DNR use text is:

> DNR does not recommend use of this data at a larger scale. Greater detail for each layer is provided from DNR, Land Records Information Section, for each data module upon receipt of order.

The GIS agreement text itself is absent. If that agreement governs XML, supply
the relevant terms rather than guessing them. For Unaami, also identify the exact
original-data-source credit needed if acknowledgment applies to XML restoration.
No reviewed lineage/cross-reference supplies that source; point/distribution
contacts are not substitutes. All nine partitions remain held pending evidence
or a separately recorded narrow scope statement.

## Source evidence gaps for later batches

[The next-source receipt](residual_source_candidates.json) binds exact IDs/hashes:

- **21 empty primary origins:** authoritative per-record creator attribution is
  needed. Their `20050418` metadata day and registration/hosting context do not
  establish creators. Do not fill blanks from metadata contacts.
- **Six metadata dates:** FGDC-1422/1423/3850 have blank `metd`; FGDC-4139/4161/4181
  have literal `2080207`. None has a metadata review-date field (`metrd`) either.
  [FGDC defines review separately from metadata creation or last update](https://www.fgdc.gov/metadata/csdgm/07.html).
  Provide a verified metadata creation or last-update day; review dates, source
  publication dates and guessed `20080207` are not replacements.
- **BASIS roles/order:** primary [FGDC-3681](../../../FGDC/FGDC-3681.xml) says
  `Nancy Navis`, while the abstract reference says `N. Davis`. Keep the primary
  spelling/order unless authoritative report/catalogue evidence resolves it.
  Contacts, existing combined Organization objects and abstract order do not
  silently establish full after-images.

The 15 typed and 24 untyped literal-citation candidates subsequently passed
[separate source-bound implementation and offline validation](literal_citation_extension_229.md)
without answering these missing-name/date cases. Their 39 source-support additions
do not clear any of the nine access partitions or establish publication approval.

## Canonical identity evidence

The [456-entry alias candidate map](source_alias_candidates.json) recommends
neutral XML-byte hash groups and provisional display representatives only.
All authoritative provider IDs/DOIs stay unset. Before any production canonical
selection, obtain verified ownership and a source-to-existing-record crosswalk;
there is no direct retained production association for these aliases. Preserve
all original IDs/history and existing provider records/DOIs. Two title-only
collisions differ from FGDC-2043/ProCite104 and cannot inherit its DOI.

Source copies and all 4,194 complete metadata objects remain unchanged. The
extension changes 229 creator-policy references; 3,965 complete payload byte
sequences remain identical. The 90 access holds, 456 alias holds and spent
uncertain canary POST remain intact. No provider request or canary retry is
needed to prepare this decision bundle.
