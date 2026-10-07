# PICES26 draft batch on production — 2026-10-07

The 26 PICES-authored singletons in
[modern_pices_singletons26.json](../2026-10-06/modern_pices_singletons26.json)
now exist on zenodo.org as unpublished drafts owned by Zenodo user 266679,
except FGDC-1938, whose create returned 201 and whose row is `started` and
resumable. Nothing was published, submitted or deleted. The per-record
identities, grant and proof hashes are in
[pices26_draft_batch.json](pices26_draft_batch.json); the original journals,
grants, proofs and raw receipts stay in the production root on Brett's Mac.

## What ran

Every record went through the single-record chain of the
[first-record runbook](../2026-10-06/first_pices_record_runbook.md) from the
Terminal pane with the token read from the Keychain item
`pices-zenodo-production`, under runtime
`74e3a233de0f2b56ca573a8ea3613a6c37c87a45356ec495e7ae1ded0e2e85a5`
(main at `e8bc897`, CI green at 04:17:48 UTC):

1. FGDC-1319 was resumed at 04:24:57 UTC under the resume route: the retained
   201 body re-validated, identity 23201173 (parent 23201172) bound, file
   uploaded and verified at revision 5.
2. One owner inventory was captured at 04:17:45 UTC
   (`inventory-20261007T041745Z-e90cec.json`, SHA256
   `1316d5f5075e0243451f25723267df05da842ea5160e481b95a472a4a9f313db`,
   21 records, two listing pages and three detail receipts). An independent
   reviewer agent checked all 25 remaining sources against it (title variants,
   report number, ISBN, file name, file MD5, XML digests, source-id mentions)
   and signed it as
   `Independent reviewer agent (Claude, session 3b1f13) 2026-10-07; inventory 1316d5f5 for the PICES26 batch`.
3. For each source, in order: `prepare`, `mint-create` (ten-minute grant and
   duplicate proof over that inventory), `preflight`, then `execute`
   (create, file init, content upload, five-GET readback), five seconds apart.
   Each record took about twelve seconds and nine provider requests.

| Source | Record | Parent | Created (UTC) | State |
|---|---|---|---|---|
| FGDC-1319 | 23201173 | 23201172 | 02:17:36, resumed 04:24:57 | verified, revision 5 |
| FGDC-1915 | 23202974 | 23202973 | 04:34:47 | verified, revision 5 |
| FGDC-1916 | 23202976 | 23202975 | 04:34:59 | verified, revision 5 |
| FGDC-1917 | 23202978 | 23202977 | 04:35:11 | verified, revision 5 |
| FGDC-1918 | 23202984 | 23202983 | 04:35:23 | verified, revision 5 |
| FGDC-1919 | 23202988 | 23202987 | 04:35:35 | verified, revision 5 |
| FGDC-1921 | 23202992 | 23202991 | 04:35:47 | verified, revision 5 |
| FGDC-1922 | 23202997 | 23202996 | 04:35:58 | verified, revision 5 |
| FGDC-1923 | 23203002 | 23203001 | 04:36:10 | verified, revision 5 |
| FGDC-1924 | 23203006 | 23203005 | 04:36:22 | verified, revision 5 |
| FGDC-1925 | 23203014 | 23203013 | 04:36:34 | verified, revision 5 |
| FGDC-1926 | 23203018 | 23203017 | 04:36:47 | verified, revision 5 |
| FGDC-1927 | 23203024 | 23203023 | 04:36:59 | verified, revision 5 |
| FGDC-1928 | 23203028 | 23203027 | 04:37:11 | verified, revision 5 |
| FGDC-1929 | 23203035 | 23203034 | 04:37:23 | verified, revision 5 |
| FGDC-1930 | 23203037 | 23203036 | 04:37:35 | verified, revision 5 |
| FGDC-1932 | 23203039 | 23203038 | 04:37:48 | verified, revision 5 |
| FGDC-1933 | 23203042 | 23203041 | 04:38:00 | verified, revision 5 |
| FGDC-1934 | 23203046 | 23203045 | 04:38:12 | verified, revision 5 |
| FGDC-1935 | 23203048 | 23203047 | 04:38:25 | verified, revision 5 |
| FGDC-1936 | 23203052 | 23203051 | 04:38:37 | verified, revision 5 |
| FGDC-1937 | 23203060 | 23203059 | 04:38:49 | verified, revision 5 |
| FGDC-1938 | 23203062 (untrusted candidate) | 23203061 | 04:39:01 (create) | started; resumable |
| FGDC-1939 | 23203129 | 23203128 | 04:44:02 | verified, revision 5 |
| FGDC-1940 | 23203131 | 23203130 | 04:44:14 | verified, revision 5 |
| FGDC-2708 | 23203133 | 23203132 | 04:44:26 | verified, revision 5 |

Every verified row has counts `create 1, init 1, content 1, commit 0, get 5`
(the upload completed on the PUT), `publication_approved: false`, owner
266679, and its grant hash recorded in the journal.

## The FGDC-1938 hold

Zenodo answered the create with 201 and record 23203062, but the executor held
before binding the identity: the description in the retained body differs from
the sent wire at one position, where the source's mojibake character U+FF92
(HALFWIDTH KATAKANA LETTER ME, in "Peopleﾒs Republic") came back as U+30E1
(KATAKANA LETTER ME). The create count is spent, the file steps did not run,
and the complete 201 body is in the hash-bound sidecar beside the journal,
exactly the shape the resume route completes.

The cause is the provider's text sanitiser. InvenioRDM declares `title` and
`publisher` as `SanitizedUnicode` and `description` and the additional
descriptions as `SanitizedHTML` (invenio-rdm-records
`services/schemas/metadata.py`); marshmallow-utils' `sanitize_unicode` runs
`ftfy.fix_text(value.strip())`, drops characters that are invalid in XML and
removes U+200B, and `sanitize_html` then runs bleach with `strip=True`. ftfy's
defaults (6.3.1) include `fix_character_width`, `fix_latin_ligatures`,
`uncurl_quotes`, `remove_control_chars`, `unescape_html='auto'` and NFC
normalisation; the quote decoding seen on FGDC-1319 and the width folding seen
here are two of those steps.

Measured offline over all 4,204 prepared inputs in `output/data/zenodo_json.zip`:
ftfy would change 101 descriptions and no title. One hundred change only by
width folding (U+FF92, U+FF96, U+FFD7, U+FFB1 and similar half-width forms,
all mojibake of Windows-1252 punctuation in the source XML) and one also by
control-character removal. No input contains curly quotes or leading or
trailing whitespace. Rebuilding ftfy's width map (the NFKC form of U+FF01 to
U+FFEE plus the ideographic space) and composing to NFC reproduces ftfy's
result for all one hundred, dakuten and jamo composition included.

The comparison is therefore widened by exactly that step: `same_text` decodes
the five quote entities, folds half-width and full-width forms to their
standard forms with the same map, and compares the NFC form of both sides.
Titles and publishers stay byte-exact. Tags, ampersands, angle-bracket
entities, curly quotes, ligatures, other compatibility characters, control
characters and whitespace are still not repaired, so the
one description with a control character will hold when its turn comes and
needs its own evidence. The batch runtime `74e3a233…` is listed in
`RESUME_RUNTIMES` and as `PICES26_DRAFTS_RUNTIME` in the publication bridge,
so the FGDC-1938 row can be resumed under the new runtime with its original
preparation packet, and the 24 verified rows can later bridge to publication.
The retained 23203062 body passes the new comparison offline.

## The inventory bound

The post-batch inventory capture at 04:46:25 UTC held after both listing pages
(46 records, page 2 empty; receipts kept as `.partial`): the legacy deposit
listing shows no `files` for RDM drafts, so 28 records needed a detail GET
against the bound of 25. Every draft this chain creates will look like that,
so the capture now skips the detail GET for records the journal already pins
(`--output-dir`), and for ids passed as `--known-record`; the summary names
them under `skipped_details`, keeps its provider-only shape, and the matcher
already treats known ids as verified another way. The bound of 25 now applies
to unknown records only, which is what it was for.

## Still open after this batch

- Resume FGDC-1938 under the new runtime after CI and independent review:
  fresh inventory, reviewer signature, `mint-create --preparation
  --resume-candidate 23203062`, `preflight`, `resume`.
- Post-batch duplicate check from a fresh inventory: each of the 26 ids
  present once, owner 266679, no repeated title, and the provider's file
  listing for each new draft (one capture with the three pre-batch records as
  `--known-record` fetches exactly the 25 new details).
- The reviewer's note A: FGDC-1924 (Scientific Report No. 9) and FGDC-2708
  describe the same October 1997 CCCC workshop with different XML, titles,
  descriptions and metadata dates; both drafts exist, as the 26-record scope
  decided. Brett decides before release whether both are published; the
  inventory matcher cannot see intra-batch twins and the journal does not
  compare sources with one another yet.
- Capture, QA, release and publication for the 26 remain the community-first
  sequence; nothing here grants them.
- Zenodo support ticket 3327790 still describes an IP block (Brett).
