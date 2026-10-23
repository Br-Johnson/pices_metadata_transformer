# Held records: evidence sheet

2026-10-22. This sheet covers the 45 records that are not published: 39 held and 6 malformed. It is a read-only review. I made no network calls and changed no files in the repository.

Sources: `docs/readiness/2026-10-04/residual_targets_remaining45.md` and `.json`, `docs/readiness/2026-10-03/pices-remaining31-exception-decisions.md`, `docs/readiness/2026-10-04/post4_remaining_decisions.md`, `docs/readiness/2026-10-03/source_scope_attestation.md`, `scripts/collection_qa.py`, `scripts/agent_qa.py`, the files `FGDC/<id>.xml`, and the production bulk journal, which I used to check precedents.

**What publishing a record does.** The pipeline copies the complete original XML into the public record notes, and Zenodo metadata is public under CC0. So every word in the XML becomes public, including the constraint text. The data files are not published.

**What a "yes" does.** A yes removes the hold. It does not publish the record. Each record must still pass AI review, validation and the bulk route, like the other 3,833.

---

## A. 23 access or policy-scope holds

**The rule.** `collection_qa.py:252-253` holds a record when the metadata access field (`metainfo/metac`) contains anything other than empty, "none", "no restrictions", "unrestricted", "open" or "public", unless a reviewed interpretation covers that text. `agent_qa.py:156-157` applies the same test to `idinfo/accconst`.

**One fact holds for all 23.** In each file, `metac` is a word-for-word copy of the data access field `accconst`, and `metuc` is a copy of `useconst`. No file has an FGDC security element (`secinfo`). The exporter copied the data terms into the metadata fields. So the rule triggers on a metadata field, but the words describe the data.

**Brett's 2026-10-03 answer:** "they reply to the underlying data. all these metadata records were public before." The code ties this answer to 821 exact records with three exact texts: "Check with Contributor", the ADF&G "Request/Republication" wording, and "Unknown". None of the 23 records is in that set, and each has different text. So the code does not apply the answer to them.
- The second sentence ("public before") is a fact about the old PICES GeoNetwork catalogue. Brett's 2026-10-02 rehosting statement (`rehosting_authority.json`) lists all 4,206 source hashes, and these 23 are among them. So "public before" plausibly covers all 23.
- The first sentence ("underlying data") needs a new yes for each new text.

Shared ADF&G texts:
- **T1** (572, 711, 758, 759, 761, 766): "Dependent on the nature and extent of request. Subject to provisions of Alaska Administrative Code on disclosure of public records and subject to Department of Fish and Game Standard Operating Procedure on public information."
- **T2** (710): "Subject to provisions of Alaska Administrative Code on dis-closure of public records and subject to Department of Fish and Game Standard Operating Procedure on public information."
- **T3** (870): the T2 wording, spelled "disclosure", followed by "Free hard copies are available."

Unless the table says otherwise, the use text is "Unknown" or the same as the access text.

| ID | Title | Text that triggers the hold (`accconst` = `metac`) | Describes | Why it is still held | Does "public before" cover it? | Precedent and content check |
|---|---|---|---|---|---|---|
| 227 | US Commercial Fishery Landing Statistics (PacFIN) | "Upon request". Use: "See http://www.psmfc.org/pacfin/6-4.htm#6.4.8%20Confidentiality%20of%20Data" | DATA. The abstract says "Data are available upon request." | Nobody has recovered the 1999 PacFIN §6.4.8 text. | Yes | 30 other "Upon request" records are published. FGDC-2230 ("State of Alaska protects confidentiality of fisheries information…") is published. |
| 288 | Stable C and N Isotopic Composition of Sediment Trap Samples and Plankton from the Southeastern Bering Sea | "SEBSCC Data Policy (see www.pmel.noaa.gov/bering)" | DATA. The text names a project data policy. | Nobody has recovered the policy text. | Yes | The XML describes sampling methods only. |
| 572 | Seal Harvest Data - EVOS | T1 | DATA. The text is about requests for public records. | Nobody has recovered the ADF&G SOP. | Yes | The abstract says "Subsistence seal kill locations…". The XML contains no locations. |
| 648 | August Shoreline Assessment Program | "Legal restrictions are as outlined in the Memorandum of Agreement and Consent Decree" | DATA. It covers the 1990 Exxon survey files. | The text does not name the instrument. Two 1991 decrees are candidates. | Yes | FGDC-679 is published. It is from the same ADEC oil-spill family and has the same use text. |
| 710 | Harbor and Spotted Seals Telemetry Data | T2 | DATA | ADF&G SOP not recovered. | Yes | It has a regional box only (53–58°N). It has no tag positions. |
| 711 | Moose Survey Data - CNF | T1 | DATA | ADF&G SOP not recovered. | Yes | It gives the survey method and region only. |
| 758 | Copper River Communities Subsistence | T1 | DATA | ADF&G SOP not recovered. | Yes | It lists community names only. It has no harvest sites. |
| 759 | EVOS Foodsites, Subsistence | T1 | DATA | ADF&G SOP not recovered. | Yes | It has a regional box only. |
| 761 | Subsistence Harvest Areas - Whittier, Hope, Cooper Landing | T1 | DATA | ADF&G SOP not recovered. | Yes | It has a community-level box. It has no household data. |
| 766 | Subsidence Harvest Areas for Valdez, Alaska, U.S.A | T1 | DATA | ADF&G SOP not recovered. | Yes | The box is one point, the town of Valdez. The XML says "50 households" but gives no names. |
| 802 | Digital Chart of the World (DCW) | "The DCW is commercially available on ISO 9660 formatted CD-ROM discs from ESRI. Consult ESRI for latest database acquisition costs." Use: "Use, duplication, and disclosure by the Government is subject to restrictions as set forth in FAR 52.227-14 Alternat III (g)(3)(JUN 1987), FAR 52.227-19 (c)(1)(ii)(OCT 1988), as applicable." | DATA. It covers the commercial CD product. | Nobody has recovered the ESRI licence or the FAR versions. | Yes | The XML describes the product only. |
| 862 | Alaska Biological Conservation Database | "Data can be obtained through written request form and formal data inquiry procedures that are in alignment with University of Alaska Draft". Use: "Some locational data relating to threatened and Endangerred Species or sensitive data have associated use restrictions." | DATA | The source sentence stops at "Draft". | Yes | It has a statewide box only. It has no species locations. |
| 870 | Special Areas ATLAS - ADF&G | T3 | DATA. It covers the atlas, and the text says hard copies are free. | ADF&G SOP not recovered. | Yes | It is an atlas of refuge boundaries, so the risk is low. |
| **909** | Results from the Naval Postgraduate School Arctic Modeling Effort | "Permission of Contributor required. Department of Defense Sensitive data" | DATA, from its words ("sensitive data") | No rule or note says what the DoD marker covers. | **Not alone. See the flag below.** | FGDC-905, 906, 907 and 1800 ("Permission of Contributor required") are published. Only the DoD words are different. Public NPS sources describe most of the model, but not the "1994-2002 operational products" forcing. |
| 1318 | Alaska Basemap CD, version 2.0 | "Must purchase the CD". Use: "Refer to vendor policy." | DATA (the CD). But the abstract says "These pages contain specific metadata about each of the maps, drawings, and tables on the CD." | Nobody has recovered the vendor policy (Resource Data, Inc.). The XML may copy text from the CD. | Likely | The abstract is a short product description. |
| 1770 | SeaWiFS Data by NASA Goddard | "See http://daac.gsfc.nasa.gov/data/dataset/SEAWIFS/ds_top_help.html#RESTRICTION" | DATA | Nobody has recovered the historical DAAC restriction section. | Yes | No issue found. |
| 1771 | Nimbus-7 Coastal Zone Color Scanner (CZCS) Data | The same SeaWiFS link | DATA | The same gap. Also, a SeaWiFS link sits on a CZCS record. | Yes | The abstract says "Data can be obtained directly at ftp://daac.gsfc.nasa.gov/data/czcs." The link is probably copied by mistake from 1770. |
| 1864 | POI Oceanographic Temperature and Salinity Database on the North Pacific Ocean | "IOC/IODE rules". Use: "None" | DATA. The text refers to data-exchange rules. | The text does not name the rule version. | Yes | No issue found. |
| 1994 | A Fish and Wildlife Resource Inventory of the Cook Inlet and Kodiak Areas | "Contact Source" | DATA, but here the "data" is a metadata product: "The metadata are maintained in digital format (ArcView 3.3, Excel 2002, and Procite) and are available from the Alaska Science Center, USGS". | Brett's 2026-10-02 "Contact Source" answer was not applied here, because the product is metadata. | Likely | The record cites a public 1977 ADF&G report. 814 other "Contact Source" records are published. |
| 3687 | CAS Ichthyology Primary Types Imagebase | "Review http://www.calacademy.org/research/ichthyology/Types/about_types.html#Use" | DATA. The terms cover the images. | Nobody has recovered the 2005 use terms. | Yes | The XML contains no images. |
| 4027 | JAMSTEC Global Chemical Weather Forecasting System Forecasting Air Pollution on a Global Scale | "See http://www.jamstec.go.jp/frsgc/gcwm/htdocs/disclaimer.html" | DATA. The disclaimer covers the forecast outputs. | Nobody has recovered the 2005 disclaimer. | Yes | No issue found. |
| 4039 | JAMSTEC Ocean General Circulation Model for the Earth Simulator (OFES) | "User registration required." Use: "Review http://www.jamstec.go.jp/site_policy_e.html" | DATA. Registration is for downloading model output. | Nobody has recovered the 2005 site policy. | Yes | FGDC-4037 is published with the same "User registration required." FGDC-4038 is published with the same site-policy link. |
| **4063** | Pacific Ocean Shelf Tracking (POST) Project | "May require password access". Use: "Contact Source" | DATA. The text refers to the data service. | This XML does not say what the password protects. | Yes | FGDC-4064, the POST Project Database, has the same four constraint texts and is published (10.5281/zenodo.23569964). Its abstract says "Password access is required for the most recent data." |

**Flags**
- **909: flag, high caution.** The content looks harmless. It is a description of an ocean and sea-ice model, and most of it is in public NPS sources. But the record carries a US Department of Defense sensitivity marker, and that marker would be published with it. We cannot remove the marker, because originals are not modified. Neither Brett nor PICES owns it. **Clear 909 only with written confirmation from NPS or the contributor, Dr Wieslaw Maslowski. Otherwise keep it held.**
- **4063: not flagged.** The XML has no password, no link, no endpoint and no coordinates (the box is all zeros). The word "password" appears only in the access text. Its sister record 4064 is already public with the same text.
- **Subsistence and wildlife records (572, 710, 758, 759, 761, 766 and 862): low risk.** They contain only community names, survey methods and regional boxes. They have no harvest sites, household names, tag positions or species locations. The published records 627, 754, 755, 757 and 760, which are subsistence and cultural-site layers, passed the same content check.

**Questions for group A**
- **A1. 19 records:** 227, 288, 572, 648, 710, 711, 758, 759, 761, 766, 802, 862, 870, 1770, 1771, 1864, 3687, 4027, 4039.
  *"Do these access and use texts restrict only the underlying data or product, and not the catalogue description that was public in the PICES GeoNetwork? Yes or no."*
- **A2. 1318 and 1994:** *"Is each FGDC record the public catalogue entry, and not a copy of the restricted product (the purchased CD pages for 1318, the USGS GEM metadata set for 1994)? Yes or no."*
- **A3. 4063:** *"Does 'May require password access' refer to the POST data service, as in FGDC-4064, and not to this project description? Yes or no."*
- **A4. 909:** *"Do you have written confirmation from NPS or Dr Maslowski that 'Department of Defense Sensitive data' covers only the model outputs? Yes or no."* If the answer is no, 909 stays held.

---

## B. 10 creator holds

**The rule.** `agent_qa.py:89-113` takes the creator only from the citation `origin`. The origin must be a person in "Surname, Given" form or a recognised organisation. A journal name, a publishing instruction or an empty origin fails with "Creator semantics are ambiguous". Contacts are never promoted to creators. Zenodo needs at least one creator.

| ID | Title | Origin text in the source | Why it is held | Best lead (not yet applied) |
|---|---|---|---|---|
| 1206 | Degenerative and Reduction Processes in Chum Juveniles Olfactory Epithelium (Oncorhynchus keta Walbaum: Salmoniformes) at Acute Effect of Copper and Zinc Salts | "Journal of Cytology" | The origin is a journal, not an author. The contact is Biryukova, Inga V. (TINRO). | A 2006 Curonian Spit National Park scientific collection (vol. 4, reference 5) gives "Бирюкова И.В., Матросов В.В., Евдокимов В.В." for Tsitologiia 1998, vol. 40, no. 1, pp. 5–9. A thesis gives the same three names in the same order. Nobody has checked this against the article. |
| 2586 | Maps of Upper-Level Heights for the Northern Hemisphere | "Published by direction of the Chief of Naval Operations." | The origin is an instruction to publish, not a named producer. | The NOAA/NCEI holding SN-240, box AA96144, confirms the 1953 title but names no author. |
| 2817 | Distribution Patterns of Urea in the Bering Sea and its Role in the Nitrogen Cycle | "Okeanologiya. Moscow" | The origin is a journal. The contact is Kavakina, S.V. | A 2008 paper cites "Kavakina SV, Sapozhnikov VV", Oceanology 33:768–773, the 1995 English edition. The source date is 1993-12-31. The related FGDC-2664 is published with the creator "Sapozhnikov, V. V.". |
| 3683 | Global Bathy Data in NEAR-GOOS Regional Delayed Mode Data Base (RDMDB) | `<origin />` (empty) | There is no creator. The contact is Okano, Hirofumi (JODC). | The RDMDB manual says "The Japan Oceanographic Data Center (JODC) operates the RDMDB", and JODC puts each month's reports into one file. |
| 3975 | Global Buoy Data in NEAR-GOOS Regional Delayed Mode Data Base (RDMDB) | empty | Same as 3683 | Same as 3683 |
| 3976 | Global Ship Data in NEAR-GOOS Regional Delayed Mode Data Base (RDMDB) | empty | Same as 3683 | Same as 3683 |
| 3977 | Global TESAC Data in NEAR-GOOS Regional Delayed Mode Data Base (RDMDB) | empty | Same as 3683 | Same as 3683 |
| 3978 | Global TRACKOB Data in NEAR-GOOS Regional Delayed Mode Data Base (RDMDB) | empty | Same as 3683 | Same as 3683 |
| 3919 | GTS Bathythermal Observation Data in NEAR-GOOS Regional Real Time Data Base (RRTDB) | empty | There is no creator. The contact is Yoshida, Takashi (JMA). | The RRTDB is the JMA site goos.kishou.go.jp. The JMA index does not credit a producer for the GTS report sets. |
| 3920 | GTS Oceanographic TESAC Data in NEAR-GOOS Regional Real Time Data Base (RRTDB) | empty | Same as 3919 | Same as 3919 |

Precedent: nine sibling NEAR-GOOS RDMDB records are published with the creator "Japan Meteorological Agency": 3951–3954, 3956 and 3966–3969. They received that creator because JODC documents say JMA developed those decoded products.

**Questions for group B**
- **B1. 1206:** *"Credit Biryukova, I.V.; Matrosov, V.V.; Evdokimov, V.V., in this order? Yes or no."* If you know the correct byline, you can give it instead.
- **B2. 2817:** *"Credit Kavakina, S.V.; Sapozhnikov, V.V., in this order? Yes or no."*
- **B3. 2586:** *"Credit the issuer, 'United States Navy, Office of the Chief of Naval Operations', as the creator? Yes or no."*
- **B4. 3683, 3975, 3976, 3977, 3978, 3919 and 3920:** *"Credit the operator of each database as creator: the Japan Oceanographic Data Center for the five RDMDB global sets, and the Japan Meteorological Agency for the two RRTDB sets? Yes or no."* You can also give one name for all seven.

---

## C. 6 metadata-date holds

**The rule.** `collection_qa.py:254-255` requires the metadata date (`metainfo/metd`) to be a full day, in the form `YYYYMMDD` or `YYYY-MM-DD`. This date becomes the Zenodo publication date. A blank value or a 7-digit value fails.

| ID | Title | `metd` | Other dates in the XML | Evidence for a value |
|---|---|---|---|---|
| 1422 | 2002 (29 Jan. - 9 Feb.) U.S. Bottom Trawl Survey Leg 1 Data for Moorings Retrieval and Deployment Around Kodiak Island and Shelikof Strait (Cruise ID: MF2002-01) | `<metd />` (blank) | pubdate "Unknown"; survey dates 20020202–20020209 | All 21 NOAA neighbours in 1410–1435 have `metd` 20030530. These include 1421, which is also a 2002 survey. |
| 1423 | 2002 (Jan. - Feb.) U.S. Bottom Trawl Survey Leg 2 Data for Arrowtooth Flounder on the Outter Continental Shelf and Upper Slope of the Gulf of Alaska West of Kodiak Island - R/V Miller Freeman (Cruise ID: MF2002-01) | `<metd />` (blank) | pubdate "Unknown"; survey dates 20020203–20020209 | Same as 1422 |
| 3850 | Benthic Habitats of Willapa Bay, Washington, 1995 | `<metd />` (blank) | pubdate 20000101; photos dated 19950628 | The neighbours are 3849 (20050225) and 3851 (20050321). There is no single neighbour value. A NOAA OCM record (InPort 47995) is a related lead only. |
| 4139 | Moored Sediment Trap Data - La Perouse, 1982-present | "2080207" | pubdate "Unpublished material"; 1982–present | The other 31 DFO Ocean Science and Productivity records have dates from 20070418 to 20080211. Seven of them have exactly 20080207, including the next-door records 4140 and 4180. |
| 4161 | Physical, Chemical and Biological Oceanography of the Haida Eddy, 1999-2000 | "2080207" | 1999–2000 | Same as 4139 |
| 4181 | Ship of Opportunity: Canada to Japan - 1980-present | "2080207" | 1980–present | Same as 4139 |

**Questions for group C**
- **C1. 4139, 4161 and 4181:** *"Is 2080207 a typo for 20080207 (7 February 2008)? Yes or no."* If yes, the original files stay unchanged. The corrected date goes into a reviewed correction with a note.
- **C2. 1422 and 1423:** *"Use 2003-05-30, the metadata date of the 21 neighbouring NOAA records, as their metadata date? Yes or no."*
- **C3. 3850:** *"Give one metadata date for 3850, or say 'keep held'."* The neighbouring dates put it between 2005-02-25 and 2005-03-21.

---

## D. 6 malformed files

**The rule.** At `collection_qa.py:154-155`, a file that does not parse as one XML document gets the status "failed". No record can be built from it.

| ID | What the file contains | Any content not already public? |
|---|---|---|
| 3373 | 5,624 bytes, all NUL (0x00). The file has been the same since the initial commit, and the `original_fgdc.zip` archive does not contain it. | Unknown. The file contains nothing to recover. |
| 3484 | 5,847 bytes, all NUL. Same history as 3373. | Unknown. |
| 21 | Two complete documents: (a) "Synoptic Flow and Density Observations near an Arctic Shelf Break" (Rutgers), `metd` 19990204, and (b) "Aquatic Sources and Sinks of CO2 and CH4 in the Polar Regions" (POI), `metd` 19990204. Between them is the row `58  8d93a3bb-…  fgdc-std  n  n  2008-10-16T19:30:58  2010-07-19T21:26:08`. | Yes. Neither title is in any other file. |
| 4077 | (a) "No. 194 - Stock assessment trawl surveys of Pandalid shrimps in the Kodiak Island and Chignik Districts of Alaska, 1985. …" (ADF&G), `metd` 19980716, and (b) "The database on distribution and morphological and physiological characteristics of Northern Fur Seal caught at the North Pacific" (TINRO), `metd` 20060412. The row between them is `4144 447c8bb4-… fgdc-std n y 2008-07-11… 2010-08-02…`. | Yes. |
| 4184 | (a) "Strait of Georgia" (DFO Staff; CTD at about 70 stations), `metd` 20040609, and (b) "RCD Biology DB" (TINRO), `metd` 200603. The row between them is `4360 801ae7f3-… 2010-10-23… 2011-10-04…`. | Yes. Part (a) is different from the published records 3793–3795. |
| 4185 | (a) An exact copy of FGDC-6, which is published. (b) "tester 2 fgdc 1972 USSR Sablefish Tagging Survey", a test copy of 1658/1659, which are published. (c) "tester 2 Meteorological Data from Station Duckjeokdo…", a test copy of 3911, which is published. The rows 4369 and 4370 were both created on 2011-09-27, and their fourth field is "y". | No. All of its content is already public. |

The rows between documents look like GeoNetwork database rows: id, uuid, schema, two y/n flags, created date and changed date. The row ids do not match the FGDC file numbers; FGDC-58 and FGDC-4144 are different records. So the rows cannot tell us which ID each part belongs to.

**Questions for group D**
- **D1. 3373 and 3484:** *"Do you have another copy of these two records, from the old GeoNetwork database or a backup? If not, do we retire both IDs as unrecoverable and keep the files unchanged? Yes or no."*
- **D2. 4185:** *"Exclude 4185 as a duplicate and test file? Yes or no."*
- **D3. 21, 4077 and 4184:** *"Publish each document in these files as its own record, with a suffixed ID such as FGDC-21-a and FGDC-21-b, and keep the original file unchanged? Yes or no."* Each part then goes through the normal checks. Part 4184-b has `metd` 200603 (month only), so the date rule will hold it.

---

## All questions on one page

| Q | Records | Question | If yes |
|---|---|---|---|
| A1 | 19 policy-scope records | Do the texts restrict only the data or product, and not the catalogue description? | The hold is removed for 19. |
| A2 | 1318, 1994 | Is each FGDC file the public catalogue entry, and not the restricted metadata product? | The hold is removed for 2. |
| A3 | 4063 | Does "password" refer to the POST data service, as in 4064? | The hold is removed for 1. |
| A4 | 909 | Is there written confirmation from NPS or Maslowski that the DoD marker covers only the outputs? | The hold is removed for 1. Without it, 909 stays held. |
| B1 | 1206 | Credit Biryukova; Matrosov; Evdokimov? | A creator is set. |
| B2 | 2817 | Credit Kavakina; Sapozhnikov? | A creator is set. |
| B3 | 2586 | Credit the US Navy Office of the Chief of Naval Operations? | A creator is set. |
| B4 | 3683, 3975–3978, 3919, 3920 | Credit JODC for the RDMDB sets and JMA for the RRTDB sets? | Creators are set for 7. |
| C1 | 4139, 4161, 4181 | Is 2080207 a typo for 20080207? | The date is corrected for 3. |
| C2 | 1422, 1423 | Use 2003-05-30? | The date is set for 2. |
| C3 | 3850 | What is its metadata date? | The date is set for 1. |
| D1 | 3373, 3484 | Is there another copy? If not, retire both? | 2 records are closed. |
| D2 | 4185 | Exclude it as a duplicate and test file? | 1 record is closed. |
| D3 | 21, 4077, 4184 | Split each file into suffixed records? | 6 new records go to review, and 4184-b will meet the date rule. |
