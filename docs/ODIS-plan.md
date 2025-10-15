# ODIS Metadata Publishing Options

The following alternatives outline different ways to expose PICES Zenodo records so they can be harvested and associated with the Ocean Data and Information System (ODIS) and the Ocean InfoHub (OIH).

## Plan A — Static HTML Landing Pages with Embedded JSON-LD
1. **Harvest Zenodo metadata:** Use the Zenodo REST API to pull the latest JSON for targeted records, capturing identifiers for PICES materials and any ODIS-relevant facets (geography, organizations, themes).
2. **Transform to schema.org JSON-LD:** Map Zenodo fields to schema.org/Dataset (and related types) in JSON-LD, preserving authoritative identifiers and linking to the North Pacific Marine Science Organization (PICES) as `creator`/`publisher` where appropriate.【F:docs/ODIS-Book.md†L367-L401】
3. **Render lightweight HTML landing pages:** For each record, generate a static HTML page that embeds the JSON-LD snippet in a `<script type="application/ld+json">` block inside the page head so Gleaner and similar harvesters can extract the markup.【F:docs/ODIS-Book.md†L380-L419】
4. **Publish with sitemap support:** Host the pages on a stable domain (e.g., GitHub Pages, institutional web server) and expose `robots.txt` plus `sitemap.xml` that enumerate each landing page with `lastmod` metadata for crawler discovery.【F:docs/ODIS-Book.md†L389-L393】【F:docs/ODIS-Book.md†L54-L113】
5. **Enable automated refresh:** Schedule the pipeline (GitHub Actions, cron job) to detect Zenodo changes, regenerate affected pages, and republish the sitemap so ODIS harvesters stay in sync.

**Pros:** Full control over schema markup, can add cross-links to regional/thematic hubs, aligns with ODIS guidance for HTML + structured data. **Cons:** Requires hosting and build automation outside Zenodo.

## Plan B — JSON-LD Record Directory Served via Stable URLs
1. **Generate standalone JSON-LD files:** Transform Zenodo records into schema.org-aligned JSON-LD documents stored as individual files in a version-controlled directory.【F:docs/ODIS-Book.md†L367-L401】
2. **Host the files on a persistent web endpoint:** Publish the directory through GitHub Pages or similar static hosting, optionally fronted by a persistent redirect (e.g., w3id) so ODIS sees durable URLs while PICES retains control.
3. **Expose a sitemap for harvesting:** Produce an XML sitemap that lists each JSON-LD file URL and update the `lastmod` timestamps whenever records change, following the ODIS web architecture guidance.【F:docs/ODIS-Book.md†L389-L393】
4. **Offer content negotiation for JSON-LD:** Configure hosting (or use simple HTTP headers) to advertise `application/ld+json` so tools like Gleaner can request the JSON-LD serialization directly.【F:docs/ODIS-Book.md†L470-L472】
5. **Automate validation and publication:** Use CI to run JSON-LD validation before pushing updates and regenerate the sitemap so the directory stays aligned with Zenodo releases.

**Pros:** Lightweight to host, mirrors the reference pattern shared by ODIS nodes, and keeps JSON-LD under direct PICES governance. **Cons:** Requires maintaining a public web endpoint and redirect strategy in addition to Zenodo.

## Plan C — Enhanced Zenodo Landing Pages with Supplemental Discovery Aids
1. **Author JSON-LD payloads per record:** Create schema.org JSON-LD snippets that reference the Zenodo DOI landing page and encode PICES affiliations and thematic details.【F:docs/ODIS-Book.md†L367-L401】
2. **Embed or attach markup within Zenodo:** Where Zenodo allows HTML, inject the JSON-LD snippet into the record description using the `<script type="application/ld+json">` pattern, or upload it as a clearly labelled supplemental file for harvesters to fetch.【F:docs/ODIS-Book.md†L380-L419】
3. **Publish an external sitemap of DOIs:** Maintain a minimal static sitemap (outside Zenodo if necessary) that lists each DOI landing URL so ODIS harvesters know which pages to crawl.【F:docs/ODIS-Book.md†L389-L393】
4. **Coordinate with ODIS on crawling constraints:** Share the sitemap location and confirm that Gleaner or alternate harvesters can fetch the Zenodo pages and detect the embedded JSON-LD; adjust formatting if Zenodo sanitizes tags.
5. **Monitor validation and fallbacks:** Periodically verify that the embedded JSON-LD remains accessible and valid; if Zenodo stripping occurs, fall back to attaching JSON-LD files plus pointing to them from the sitemap.

**Pros:** Keeps the DOI landing page as the authoritative HTML surface, minimizes external infrastructure. **Cons:** Dependent on Zenodo’s support for embedded script tags or discoverable attachments; still needs an auxiliary sitemap for reliable harvesting.

---

**Recommendation for review:** Start with Plan A or B for quickest alignment with the ODIS publishing guidance, then evaluate whether Plan C is warranted for long-term federation or advanced thematic linking.
