# ODIS Book

_This document is an aggregated Markdown rendering of the ODIS book content defined in `book/_toc.yml`._



---

<!-- Begin: index.md -->

![splash](images/splash.png)

# The Ocean InfoHub Project & ODIS

## Introduction

The Ocean InfoHub aims to build a sustainable, interoperable, and inclusive digital 
ecosystem for all Ocean data centres. Existing and emerging data systems are linked, 
with the ultimate goal of coordinating action and capacity to improve access to Ocean 
data and knowledge.

The following video provide brief high level context to the Ocean InfoHub project.

[![Ocean Infohub YouTube video](https://img.youtube.com/vi/KrxeZrPg0u8/0.jpg)](https://www.youtube.com/watch?v=KrxeZrPg0u8)

*(read the original [ODIS Proposal](assets/IOC_OceanInfoHub_Proposal__summary.pdf))*

Organizations are increasingly exposing data and resources on the Web.   A popular 
approach to this is using web architecture to expose structured data on the web using 
the schema.org vocabulary.   Doing this makes resources discoverable by a range of 
organizations leveraging this architecture to build indexes.  These include major 
commercial indexes, large domain focused groups and community focused services.

The Ocean Data and Information System (ODIS) will provide a schema.org based 
interoperability layer and supporting technology to allow existing and emerging ocean 
data and information systems, from any stakeholder, to interoperate with one another. 
This will enable and accelerate more effective development and dissemination of digital 
technology and sharing of ocean data, information, and knowledge. As such, ODIS will 
not be a new portal or centralized system, but will provide a collaborative solution to 
interlink distributed systems for common goals. Together with global project partners and 
partners in the three regions, a process of co-design will enable a number of global and 
regional nodes to test the proof of concept for the ODIS.

The ODIS-architecture development is being supported by the Ocean InfoHub Project, and it 
has been tested initially on IOC and partner databases. However, the system and standards 
are open for any institution or initiative that is interested in accessing the global data 
ecosystem to adopt and implement.

## Guidance for the implementation of the ODIS-architecture

OIH is providing guidance on the various stages of such an
architecture including authoring, publishing, indexing and interfaces.

The basics of this approach can be described as:

* Providers publish HTML pages for a resource.  This may be a publication, course 
  description, research instrument or other.   The core themes for OIH are described 
  in the Authoring section below.
* A HTML page then has a small JSON based snippet added to the HTML.  This is
  described in the Including JSON-LD in your resource page in the Publishing
  resource below. 
* If you wish a resource to be included in the OIH index, then you need to
  include it in a sitemap file.  This is a small XML document that lists links
  to the resources you wish to be part of the index.  This approach is shown in
  the sitemap.xml section of the Publishing resource.   
* Once the above is done the publishing phase is over.  At this point, OIH or
  other groups can now access and index your resources.   OIH is using some
  existing software to index and generate the graph and expose a simple
  reference interface to them.  This software is open and available and others
  are free to implement the approach with other software.  Links to other
  software are at the repository.  
* The OIH index/graph and a simple interface is current at a development site
  and in a later phase of OIH a production interface will be developed.  

![image1](images/intro1.png)

Additionally, software to aid in validating and checking the resources is under
development and will be available at the repository.   This will aid providers
in expressing the information needed to address interfaces and services of
interest to the community.

The result is a sustainable architecture to address discovery and access to
various resources published by the community and a shared graph of these
resources.  That shared graph can be used by all members to link and discover
across groups.  

## Key links to the OIH GitHub repository

Interested groups can review material addressing these stages at the OIH GitHub
repository.  Links and descriptions of these stages are described below.  

### [Authoring Thematic Patterns](thematics/index.md)

The ODIS OIH is working across five major thematic areas; Experts and
Institutions, Documents, Projects, Training, Vessels.   Examples of these
thematic concepts are being hosted and developed with input from the community.
Additionally, methods for validation and simple tooling for authoring and
testing are hosted at this repository.  Alongside these five thematic topics
guidance on connecting services and spatial context on resources. 

### [Publishing](publishing/publishing.md)

Guidance on implementation the web architecture approach is also available.
This includes approaches on leveraging robots.txt and sitemaps.xml file for
expressing hosted resources to the net.  

### [Indexing](indexing/index.md)

The architecture approach is open and standards based.  As such, many
organizations will be able to leverage the authoring and publishing approaches
above to index a providers resources.  OIH will be providing reference
implementations of software that can generate the index.

### [Interfaces and Services](users/index.md)

During the development of the OIH a basic reference implementation for an
interface has been generated.  This is a development site meant to test and
exercise the above elements.   It serves to demonstrate how others could also
implement this approach and how future interfaces could be developed.  

An example of the value of implementing a lightweight can be seen with the
Government of Canada:

* The Federal Geospatial Platform is a intra-governmental data catalogue
  implementing the Harmonized North American Profile of ISO 19115 (HNAP), with
  content exposed externally via OGC CSW (Catalogue Services Web).
* This content is harvested by the public facing Open Maps platform, which
  includes a catalogue component that is fed in part by the Federal Geospatial
  Platform. DCAT-based metadata is derived from the original ISO 19115 based
  metadata. As this markup is recognized by web crawlers such as those hosted by
  Google, content is harvested and is subsequently visible through Google
  Dataset Search. Furthermore, the cited publication for the data is also link
  via a complementary link to Google Scholar.

![image1](images/intro2.png)
<!-- End: index.md -->


---


# Part: Introduction



---

<!-- Begin: content.md -->

# Structured Data on the Web

## About

Structured data on the web is a way to provide semantics and linked data in an
approachable manner.  This approach expresses concepts in JSON-LD which is a
JavaScript notation popular among developers which easily expresses  concepts
(terms) and links to related resources (things).   This structured data on the
web approach has been popularized by the large commercial search providers like
Google, Bing, Yandex and others via schema.org  As described at schema.org:
"Schema.org is a collaborative, community activity with a mission to create,
maintain, and promote schemas for structured data on the Internet, on web pages,
in email messages, and beyond."

The popularity of leveraging the schema.org approach in the earth sciences can
be attributed to both this ease of developer adoption and also to its
foundational use of web architecture. A web architecture foundation aids
adoption by the operations side as well as the developer side.  It also takes
advantage of the scale and resilience of the web.  

The broad nature of schema.org even scopes to the concepts of Datasets.  It is
the existence of schema.org/Dataset that was a focus of several EarthCube
projects (Project 418, Project 419 and the Resource Registry) from which spun up
the ESIP Science on Schema work.  

Additionally, Google leveraged schema.org/Dataset to develop and populate the
Google Data Set Search and provides guidance to developers to facilitate this.  


## Web architecture approach

OIH is focused on leveraging the web architecture as the foundation for this
approach.  There are several key reasons for this vs approaches like OAI-PMH or
others.

A key point is that in the processes of establishing a web presence, a standard
step for groups, they have already begun to build the infrastructure needed for
structured data on the web.  Setting up special servers or establishing and
maintaining special APIs to support harvesting is not required.  

Also, a large collection of tooling already exists around JSON that is directly
usable in JSON-LD.  That scale extends to the use of schema.org patterns which
have become common in the commercial web.  Allowing us to bring those same
patterns and the tooling to the science community.

Additionally, this approach keeps the metadata and its representation a product
of the data providers.  The actor in the life cycle most aware of needed edits,
new records or other events.  That same record then serves multiple consumers
able to generate various value add products.  This benefits the provider by
facilitating multiple and varied discovery vectors for their holdings.  

Another key factor is the web native and semantic nature of this representation
of metadata.  Traditional metadata, such as ISO, by itself does not express a
web referenceable instance of concepts.  In doing this, structured data on the
web allow connections to be made and discovered by people and machines across
many holdings.  This aids in both serendipitous discovery and can also be
leveraged to aid discovery via semantic relations.

## Terminology

A CSV file is a text file containing spreadsheet information following a data
model that is encoded using a convention of rows and commas defining columns.  

A JSON-LD fle is a text file containing graph information following the RDF data
model that is encoded using a convention based on JSON syntax.

JSON-LD is a way to serialize RDF that uses JSON notation.  It is really no
different then than RDF-XML, turtle, n-triples, etc.  There are several ways to
represent the RDF data model in text files (and some emerging binary ones like
CBOR and parquet patterns).

Schema.org is a vocabulary for describing things similar to DCAT, FOAF, Dublin
Core.  It does this by using RDF as the underlying data model to represent this
"ontology".

The confusion comes from the collision of outcomes.  JSON-LD came about, partly,
to allow the use of the RDF data model by a broader audience.  This is done by
leveraging a more popular notation for the data model, JSON, in the form of
JSON-LD.  Schema.org also wanted to advance the use of structured [meta]data by
making it easier to use and connecting structured data to web pages.  At the
start, there were three approaches; RDFa, microformats and JSON-LD, to putting
schema.org in web pages.  However, the JSON-LD approach to incorporating this
structured data has grown in popularity far beyond the others. As the popularity
of both JSON-LD and schema.org grew,  they often got conflated with each other.

The term  "structured data on the web" is perhaps a more neutral way to discuss
the use of vocabularies encoding in JSON-LD used in web pages.  However,  the
phrase "schema.org" is starting to become the term for "structured data on the
web using JSON-LD as a serialization".    Even in cases where you combine other
vocabularies such as DCAT with JSON-LD with no schema.org involved, it seems the
way to convey this is to say: "We will use the schema.org 'pattern' with DCAT".

It is arguably not the best or most accurate communications strategy.  It can
 conflate data models, serialization and vocabularies.  However, it is concise
 and ubiquitous and not likely to change.

## Intellectual Merit

OIH leverages structured data on the web patterns in the form of 
Schema.org and JSON-LD encoding.  This means that much of what is done
to address OIH implementation by providers also is available both to existing
commercial indexing approaches as well as emerging community practices  

Additionally, both the publishing and indexing approaches are based
on several web architecture patterns.  Meaning that existing organization skills
are leveraged and staff experience is enhanced.   This helps to address both 
the sustainability of the OIH connection and the efficiency of 
organizational operation.   

## Broader Impacts

By leveraging existing technology and approaches a larger community is enabled
to engage and make more samples discoverable and usable.

The nature of structured data on the web also provides the ability to apply
semantic context to samples.  This means richer discovery and information about
samples, the past uses and potential future uses is more readily available.

Simplified architecture also means easier development of tools and interfaces to
present the data.  Allowing the presentation of samples and their information in
a manner aligned with a given community's needs.    A simplified architecture
aids sustainability from both a technical and financial perspective.  
<!-- End: content.md -->


---

<!-- Begin: personas/persona.md -->
<!-- Title from ToC: Personas -->

# Personas

## About 

During the design process of the Ocean InfoHub (OIH), many of the design approached leverage three
personas that help define the various archetypes of people who engage with OIH.  It should not be assumed
these scope all the potential persona or that a person or organization scope only one.  It is quite possible
to many.   These are simply design approaches representing potential models or characters.   They 
are tools used in the design process of OIH.

````{grid}

```{grid-item}
![](images/personna.svg) 

Publisher: A key persona whose activities are covered in detail in [Publishing patterns for OIH](publishing/publishing.md)
```

```{grid-item}
![](images/personna.svg) 

Aggregator: Leverages web architecture to retrieve structured data on the web and generate usable indexes.
```

```{grid-item}
![](images/personna.svg) 

User: The end user of the publishing and aggregation activities.  May leverage
the web for discovery or tools such as Jupyter for analytics and visualization.  
```

````


## Persona: Publisher

In OIH the Publisher is engaged authoring the JSON-LD documents and publishing them 
to the web.  This persona is focused on describing and presenting structured data on the web
to aid in the discovery and use the resources they manage. 
 Details on this persona can be found in the [Publisher](publishing/publishing.md) section.  
Additionally, this persona would be leveraging this encoding described in the [JSON-LD Foundation](foundation/foundation.md) section and the 
profiles described in the [Thematic Patterns](thematics/index.md).

## Persona: Aggregator

In OIH the Aggregator is a person or organization who is indexing resources on the 
web using the structured data on the web patterns described in this documentation.  
Their goal is to efficiently and effectively index the resources exposed by the Publisher 
persona and generate usable indexes.  Further, they would work to expose these indexes in 
a manner that is usable by the User persona.
Details on the approach used by OIH and potential alternatives can be found in the 
[Aggregator](indexing/index.md) section.

## Persona: User

The user is the individual or community who wished to leverage the indexes generated
as a result of the publishing and aggregation activities. The user may be using the 
developed knowledge graph or some web interface built on top of the knowledge graph or 
other index.  They may also use query languages like SPARQL or other APIs or even 
directly work with the underlying data warehouse of collected data graphs.  

User tools may be web sites or scientific notebooks.  Some examples of these 
user experiences are described in the [User](users/index.md) section.
<!-- End: personas/persona.md -->


---

<!-- Begin: publishing/publishing.md -->
<!-- Title from ToC: Publisher -->

# Publisher

## About

This page describes the publishing process for structured data 
on the web approach OIH will use.  

Note many software packages you are using might already 
implement this approach.  See the section: 
_Existing support in software_ at the bottom of this document.

```{seealso}
We also recommend reviewing the document: 
[Schema.org for Research Data Managers: A Primer](https://docs.google.com/document/d/1fay3uIqIO2rljVBTk6Sk6i1I3yRnVecn-UTl3JKXLnw/edit)
```

### Architecture Implementation

The Ocean Info Hub (OIH) will leverage structured data on the web and web
architecture patterns to expose metadata about resources of interest to the
community.  The primary tasks include:

* Authoring JSON-LD documents (https://json-ld.org/) aligned with ODIS OIH
  guidance to express the structured metadata for a resource.  This step will
  require experience with using the existing metadata resources within an
  organization.  So any necessary skills needed to access or query existing
  facility data systems will be needed to assemble the information to populate
  the JSON-LD data graph.  The JSON-LD documents need to be generated using the
  tools/languages at the previous reference or through other means.  
* Within the system architecture of the site, a JSON-LD document needs to be
  placed into the HTML DOM as a SCRIPT tag within the HEAD tag of each
  published resource.   The SCRIPT tag pattern is:
  
  ```html
  <script type="application/ld+json">JSON_LD content</script>
  ```

* Additionally these resources that are marked up with these tags and JSON-LD
  documents should be expressed in an XML sitemap file.  This should follow the
  guidance at https://www.sitemaps.org/.  It should also include a lastmod node
  element as described at https://www.sitemaps.org/protocol.html which should
  indicate the date the resource metadata was last updated and published to the
  web.  
* The process of aligning the JSON-LD is iterative at this stage as the OIH
  profile is evolved.  To aid this we can leverage existing validation tools
  including JSONSchema, W3C SPARQL and more to communicate structure changes.
  These tools exist and need only be implemented using knowledge of command
  line environments.  The results will then indicate revisions needed in the
  JSON-LD.  OIH will provide the necessary templates for the tools to use
  against the authored JSON-LD documents.  

Information on the sources, standards and vocabularies to be used can be found
at: https://github.com/iodepo/odis-arch/tree/schema-dev/docs 

### Including JSON-LD in your resource page

To provide detailed and semantically described details on a resource, OIH uses
a [JSON-LD](https://json-ld.org/) snippet or _data graph_.  This small document
provides details on the resource.  It can also express any explicate
connections to other resources an author may wish to express.  The semantic
nature of the document also means that connections may later be discovered
through graph queries.

Pages will need a JSON-LD data graph placed in it via a typed script
tag/element in the document head element like the following.  

```html
<script type="application/ld+json"></script>
```

An example data graph can be seen below.   However, check the various
thematic sections for more examples for a given thematic area.  

```json
{
    "@context": {
        "@vocab": "https://schema.org/",
        "endDate": {
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
        },
        "startDate": {
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime"
        }
    },
    "@id": "https://foo.org/url/to/metadata/representation",
    "@type": "Course",
    "description": "In this course you will get an introduction to the main tools and ideas in the data scientist's toolbox...",
    "hasCourseInstance": {
        "@type": "CourseInstance",
        "courseMode": [
            "MOOC",
            "online"
        ],
        "endDate": "2019-03-21",
        "startDate": "2019-02-15"
    }
}
```

This example is from the [training and courses thematic
section](https://github.com/iodepo/odis-arch/tree/master/book/thematics/training).  To view all the types
being developed reference
the [Thematic section](https://github.com/iodepo/odis-in/tree/master/dataGraphs/thematics).

These JSON-LD documents leverage schema.org as the primary vocabulary.
The examples in the thematic section provide examples for the various type.  

#### JSON-LD Tools and References

A key resource for JSON-LD can be found at [JSON-LD](https://json-ld.org/).
There is also an interactive _playground_ hosted there.  The [JSON-LD
Playground](https://json-ld.org/playground/) is useful when testing or
exploring approaches for JSON-LD data graphs.  It will catch basic errors of
syntax and use.  Note, it will not catch semantic issues such as using
properties on types that are out of range.  Tools like the [Structured Data
Testing Tool](https://search.google.com/structured-data/testing-tool) are
better at that.  Also the documents and validation material created here OIH
will also allow for that sort of testing and feedback.  

Providers may also wish to provide content negotiation for type application/ld+json 
for these resources. Some indexers,  like Gleaner, will attempt to negotiate for
the specific serialization and this will likely lighten the load on the servers going forward.

#### Validation With SHACL or ShEx

To help facilitate the interconnection of resource, some application focused validation
will be developed. Note, this validation does not limit what can be in the graphs.  
Rather, it simply provides insight on to how well a given graph can be
leveraged for a specific application.  For this project, the application will
be the OIH search portal.

Some initial development work for this can be found in the
[validation directory](validation/index.md)

##### Validation Tools and References
* [SHACL playground](https://shacl.org/playground/)
* [Schemarama](https://github.com/google/schemarama)
* [Schimatos.org](https://github.com/schimatos/schimatos.org)  
  * [demo](http://rsmsrv01.nci.org.au:8080/schimatos/)
* [Comparing ShEx and SHACL](https://book.validatingrdf.com/bookHtml013.html)

#### Validation Leveraging JSON Schema

We have been exploring the potential to use JSON Schema combined with various
on-line JSON editors (JSON Schema driven) to provide a potential approach to a
more visual editing workflow. The workflow presented here is very ad hoc but
exposes a potential route a group might take to develop a usable tool. Such a
tool might, for example, leverage the Electron app dev environment to evolve
this approach in a more dedicated tool/manner.

Using a JSON-LD document ([example](https://github.com/iodepo/odis-in/blob/master/dataGraphs/thematics/sdg/graphs/creativeWork.json)), one could
load this into something like 
the [JSONschema.net tool](https://jsonschema.net/).

The results of the above can then been loaded into the online JSON-Editor at
https://json-editor.github.io/json-editor/. (Ref:
[https://github.com/json-editor/json-editor](https://github.com/json-editor/json-editor))

The results of this then can be loaded into https://json-ld.org/playground/ to
validate that we have well formed JSON-LD.

Though this workflow is rather crude and manual it exposes a route to a defined
workflow based around established schema that leverages other tools and
software libraries to generate a workable tool.

## Basics

The basic activity can be seen in the following diagram:

![](publishing/images/example1Flow.png)

### Elements in detail

#### robots.txt

OPTIONAL: Providers may decide to generate or modify their robots.txt 
file to provide guidance to the aggregators. 
The plan is to use the Gleaner software (gleaner.io) as well as some 
Python based notebooks and a few other approaches in this test.

Gleaner uses an agent string of EarthCube_DataBot/1.0 and this can be 
used a robots.txt file to specify alternative sitemaps and guidance. 
This also allows a provider to provide guidance to Google and other potential 
indexers both for allow and disallow directives.

```
Sitemap: http://samples.earth/sitemap.xml

User-agent: *
Crawl-delay: 4
Allow: /

User-agent: Googlebot
Disallow: /id

User-agent: EarthCube_DataBot/1.0
Allow: /
Sitemap: https://example.org/sitemap.xml
```

#### sitemap.xml

Providers will need to expose a set of resource
landing pages using a `sitemap.xml` file. As noted above, providers 
can expose a sitemap file to just the target agent 
to avoid indexing test pages by commercial providers.  You may wish 
to do this during testing or for other reasons.  Otherwise, 
a sitemap.xml file exposed in general from somewhere in your site is 
perfectly fine.  

Information on the sitemap structure can be found at [sitemaps.org](https://www.sitemaps.org/).

```{tip}
The Google Search developer documentation also has [useful tips](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap#xml) 
for creating a sitemap.xml file.
```

It is encouraged to use the sitemap `<lastmod>` parameter 
to provide guidance to indexers on page updates.  You can also add the 
`<changefreq>` parameter, for how often you expect records in your sitemap 
to change - this will tell systems like ODIS how often to 
reindex your holdings - possible values are: `always`, `hourly`, `daily`, 
`weekly`, `monthly`,`yearly`, `never`.
Additionally, indexers may test ways to evaluate additions and 
removals from the sitemap URL set to manage new or removed resources.  

A sitemap file would look like the following.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://example.org/landingpage1</loc>
      <lastmod>2024-06-10</lastmod>
      <changefreq>monthly</changefreq>
   </url>
   <url>
      <loc>https://example.org/landingpage2</loc>
      <lastmod>2024-01-31</lastmod>
      <changefreq>monthly</changefreq>
   </url>  
</urlset> 
```

```{caution}
If you have more than 50,000 entries, you must break the sitemap up into 
multiple files of less than 50,000. You would link to these through 
a sitemap index, as follows.
```

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="https://www.sitemaps.org/schemas/sitemap/0.9">
   <sitemap>
      <loc>https://example.org/sitemap_a.xml</loc>
      <lastmod>2024-06-10</lastmod>
   </sitemap>
   <sitemap>
       <loc>https://example.org/sitemap_b.xml</loc>
      <lastmod>2024-01-01</lastmod>
   </sitemap>
</sitemapindex>
```

## Full Workflow 
![](publishing/images/flowv2.png)

The architecture defines a workflow for objects seen in the above diagram.

The documents flow from; authoring, publishing and indexing to
storage for the objects and the resulting graph.  These resources are
then ready for use in search and other functions.

Moving left to right we can review the image.

1. Providers are engaged in the process of developing the OIH example
   documents.  These provide a _profile_ to follow to represent the semantic
   metadata.  Note, these are not limiters, simply guidance on minimum and
   recommend elements to address the functional goals of the OIH portal. 

2. Providers use these documents to generate the JSON-LD data graphs.  
These can be either static documents or generated and placed in pages
dynamically with Javascript or server side templates.  These are the 
existing web pages for the resoruces, not enhanced with the 
semantic metadata snippets in the HTML source.  

3. These are published to the web and referenced in the `sitemap.xml` 
document that is also made available.  At this point this material is 
available to anyone who may wish to index it and provide discovery 
for these resources.  

4. OIH Portal will then index and validate these resources on a 
recurring bases to maintain a current index.  This index will include 
both the JSON-LD objects and the graph they form.  This graph can 
be used for search, connections and other value add services for the 
community. The graph is also directly available to the community for them
to use in support of services they may wish to provide. 

## Existing support in software

Many content management systems other web based data interfaces 
may already have support for the structured data on the web pattern and
schema.org specifically. While it is beyond the scope of this project to 
detail each one, a few starting points for exploration are provided below
for some of the more common ones.  

* [Drupal](https://www.drupal.org/docs/contributed-modules/schemaorg-metatag)
* [CKAN](https://ckan.org/2018/04/30/make-open-data-discoverable-for-search-engines/)
* [DSpace](https://journal.code4lib.org/articles/13191)
* [DKAN](https://dkan.readthedocs.io/en/latest/introduction/index.html)
* [ERDDAP (native support)](https://www.ncei.noaa.gov/erddap/index.html)
* [OPeNDAP (native support)](https://www.opendap.org/)
* [GeoNode](https://geonode.org/)
  * [schema.org issue ref](https://github.com/GeoNode/geonode/issues?q=schema.org+)
<!-- End: publishing/publishing.md -->


---

<!-- Begin: foundation/foundation.md -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# JSON-LD Foundation

## Introduction
JSON-LD is a way of encoding Linked Data in JSON, the popular data interchange
format used by many web APIs. Linked Data is a method of representing information
on the web in a way that allows it to be linked and interconnected with other data.
This allows data from different sources to be connected and used together in new
and powerful ways. JSON-LD uses a standardized syntax to represent Linked Data,
making it easier to integrate with other systems and tools. It is often used to
add structured data to web pages, making it easier for search engines and other
applications to understand and process the information on the page.

This document provide a very brief introduction to the JSON-LD serialization format.  
The [JSON-LD](https://json-ld.org) website has some detailed material and videos in
their [documentation section](https://json-ld.org/learn.html).

The material here is just a brief introduction.   For this page we will be using
a simplified version of a CreativeWork document. All the types used by OIH are defined
by Schema.org types.  In this case it is [CreativeWork](https://schema.org/CreativeWork).

At the Schema.org site you will find extensive details on what the various types mean and 
the full range of their properties. For OIH we are defining only a few of these properties 
as of interest in the [Thematic section](thematics/index.md).  You are free to use additional
properties to describe your resources.  It will not cause any issues, however, the OIH interfaces
may not leverage them.  However, if you feel others would, or you use them yourself, it's encouraged
to add them.  

We will use the following simple JSON-LD document to show the various features of the format. 

```{literalinclude} ../../odis-in/dataGraphs/foundation/graphs/simple.json
:linenos:
```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
sys.path.insert(0, currentdir)
from lib import jbutils

with open("../../odis-in/dataGraphs/foundation/graphs/simple.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```


```{note}
A small note on nomenclature. In Schema.org, as in ontologies, the class or type
names of Things will be uppercase.  So, for example, in the above JSON-LD data graph,
this is describing a resource of type `CreativeWork`.   So the type CreativeWork will
start with an uppercase letter.  The property `name` is a property of the type and 
properties like this will be lowercase. 
```



## The Context

The context is where the terms used in a document are connected to definitions and identifiers for them.
If you wish to dive into the details of the context check out the
[W3 JSON-LD 1.1 Recommendations Context section](https://www.w3.org/TR/json-ld/#the-context).

The context part of this document is highlighted below. 




```{literalinclude} ../../odis-in/dataGraphs/foundation/graphs/simple.json
:emphasize-lines: 2-4
:linenos:
```


```{note}
This @context section will be the same for all
the documents described in OIH documentation with the exception of the spatial patterns.  
```


As justed noted, for the spatial patterns we add in the OGC context 
to all us to use terms from that vocabulary.
Below we can see the addition of the geosparql context in line 4 and the use of the vocabulary, using the defined geosparql: prefix in lines 9, 11 and 15.

If we wanted to use other vocabularies like DCAT or FOAF, we would add them to the context with a 
prefix and then the vocabulary namespace.  We could then use terms from that vocabulary in our document
following the same prefix:term pattern.


```{literalinclude} ../../odis-in/dataGraphs/thematics/spatial/graphs/geosparqlsimple.json
:emphasize-lines: 4, 9, 11, 15
:linenos:
```


## Graph

The next section we will discuss is the graph part of the document seen in lines 5-9 below.  This is where the properties and 
values of our resource are described.  


```{literalinclude} ../../odis-in/dataGraphs/foundation/graphs/simple.json
:emphasize-lines: 5-9
:linenos:
```

First though, let's visit a couple special properties in our 
document.  

### Node identifiers (@id)

```{literalinclude} ../../odis-in/dataGraphs/foundation/graphs/simple.json
:emphasize-lines: 6
:linenos:
```

The first special property is the @id property.  This is the identifier for the top level node in the
graph and is typically the identifier for the record.  

```{note}
It should be noted this is the not the ID for the object being described but rather the record itself.
If you are describing a dataset with a DOI, for example, the @id is not that DOI.  Rather it is the 
ID, potentially the URL, for the metadata record about that dataset.  Your dataset ID would be included
in the metadata record using the the identifier property. 
```

```{tip}
@id should point to whatever resolves eventually to the JSON-LD - if you only
have an external JSON-LD file (and not embedded into the html `<script>` tag)
then the @id should point to the .json file itself. Otherwise, @id should point
to the landing page of the record (HTML page), that embeds the JSON-LD.
```

It's good practice to ensure all your records have an @id property.  If there is no value then the 
resource is identified by what is known as a blank node.  Such identifiers do not allowing use in 
a Linked Open Data approach and are generally not recommended.  

The @id should be the URL for the metadata record itself.  Not the HTML page the record is in.  However, 
these might be the same if use use content negotiation to select between HTML and JSON-LD representations
of the record.

### Type identifiers (@type)

```{literalinclude} ../../odis-in/dataGraphs/foundation/graphs/simple.json
:emphasize-lines: 5
:linenos:
```

The next property to focus on is the @type property.  This describes the type of record we are describing. 


```{note}
In Schema.org and in most vocabularies, types will be named with a capitol letter.  Properties on these
types will be all lower case.  So, CreateWork, as a type, starts with a upper case C.  Then, name, as 
a property on the CreateWork type, starts with a lower case n.  
```

For OIH these type for the various thematic profiles are defined in the documentation for the types.  


### Other properties

At this point we can return to look at the other properties for our type.  

```{literalinclude} ../../odis-in/dataGraphs/foundation/graphs/simple.json
:emphasize-lines: 7-9
:linenos:
```

As noted, we are using Schema.org type for OIH.  In this case, as mentioned,
this is type  [CreativeWork](https://schema.org/CreativeWork).  So any of the properties 
seen at the Schema.org site can be used.   The key properties of value to the OIH implementation can then 
be found, for this type, in the [Documents thematic type](thematics/docs/index.md).

For the OIH implementation, we will use the following properties as core properties we 
want all OIH documents to have.  These include:

> name:  The name of the document or item being described
> 
> description:  A description of the document or item being described
> 
> url: A URL for the document or item being described. 


### Domain and range

The domain of a property identifies the type of object it can be applied to.  
So if the domain of a property like [schema.org/knowsAbout](https://schema.org/knowsAbout)
is Person and Organization.  Then that property can only be used on those types.
For example, it would not be correct to use knowsAbout on a resource of type Dataset.

The range of a property identifies the type of object the property can point to.  In 
the case of knowAbout, we see its range as Text, Thing or URL.  This means the property 
can point to a Text, Thing or URL object.  

In schema.org, the domain will be identified as "Used on these types", and the 
range will be identified as "Values expected to be one of these types".  You can see
this at the [schema.org/knowsAbout](https://schema.org/knowsAbout) page.

### Thing and DataType

The [Thing](https://schema.org/Thing) and [Datatype](https://schema.org/DataType) types 
are two special types we should mention.  Thing is the upper level and most generic
type in schema.org.   Everything in schema.org is descended from Thing.  So when
knowsAbout says its range includes Thing, it means you can use any type in schema.org
as the value of that property.

DataType is the basic data type Thing in schema.org and is a subclass of rdfs:Class.
A DataType includes things like Integers, Strings, DateTime, etc.  So, using again
knowsAbout, we see the range includes not only Thing by also the DataTypes Text 
and URL, where URL is actually a sub-type of Text. 
<!-- End: foundation/foundation.md -->


---


# Part: Getting Started



---

<!-- Begin: gettingStarted.md -->
<!-- Title from ToC: Connecting to the ODIS Federation -->

# Getting Started with ODIS: How to Join the ODIS Federation

## Quick Steps

1. Register your portal in ODIS Catalogue 
   * make sure you (or someone in your organization) has an OceanExpertID (<a href=#oceanexpert>jump</a> to that below)
   * add your entry into ODIS Catalogue (<a href=#registering-your-meta-data-node-s>jump</a> to that below)
2. Prepare your JSON-LD metadata (<a href=#preparing-content>jump</a> to that below)
3. Create your sitemap (<a href=#creating-a-sitemap>jump</a> to that below)
4. Register your sitemap in your ODIS Catalogue entry (<a href=#coming-full-circle-registering-your-sitemap-in-odiscat>jump</a> to that below)
5. Review the FAQ (<a href=#frequently-asked-questions-faq>jump</a> to that below)

## Hello World

This page describes - at a high level - how a digital system with access to the 
Web can link itself into the ODIS Federation.

![ODIS network](images/odisNetworkSmall.png)

Any system providing data (in a broad sense, including documents, software code, 
etc) and/or services that are relevant to ocean science, management, policy, 
commerce, or other ocean-relevant activities is welcome to connect to ODIS. A 
light curation of ODIS nodes is performed by IODE's team, and the entire Federation 
self-regulates, voicing concern if they believe nodes are sharing data that is 
invalid, misleading, or otherwise of concern.

## Background

In an increasingly data-driven digital landscape, sharing information about your 
resources on the web has become a vital endeavor. Structured data, presented 
through JSON-LD, offers an approachable means to achieve this goal, providing 
context and linked data in a format easily understood by both humans and machines. 
Through the incorporation of the [schema.org](https://schema.org/) framework, 
a collaborative initiative designed to create, maintain, and promote schemas for 
structured data on the internet, this guide will help you navigate the process of 
sharing JSON-LD for your web resources. In this guide, we'll walk you through the key 
steps to effectively share JSON-LD on the web for your resource, empowering you to 
enhance discoverability and semantic context for your valuable content.

```{note}
Learn more about [Structured Data for the Web](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data) 
and [JSON-LD](https://json-ld.org/)
```

The importance of sharing (meta)data about your digital assets - in a form that 
others can understand - cannot be underemphasised: without a common approach, digital 
assets are often invisible to one another, harming collaboration, due diligence, 
and informed action.  The International Oceanographic Data and Information Exchange 
(IODE) helps provide ODIS as way for ocean data entities around the world to share
oceans information through a common platform.

```{tip}
[ODIS](https://odis.org) is one of the 3 core Programme Components of IOC-UNESCO's [IODE](https://iode.org/), along with [OBIS](https://obis.org/) and [OTGA](https://classroom.oceanteacher.org/).
```

## Registering Your Organisation

Organisations which contribute to the ODIS Federation need an unambiguous identity 
on the web. This is not (necessarily) the same as your organisation's website: A 
web identifier is focused on machine-readable metadata and will not change (even 
if your organisation changes its name). It's important that this digital identity 
is sanctioned by your organisation's leadership and administration, such that it 
is an official identifier and kept up to date (like an ORCID for your organisation).

### OceanExpert 

![OceanExpert banner](images/oceanExpert.png)

We recommend that your organisation creates and maintains an OceanExpert ID. 
[OceanExpert](https://oceanexpert.org/) (OE) is maintained by the IODE and is deeply 
integrated into ocean data flows. For example, OE is - itself - an ODIS node, thus 
any data you add there will automatically be shared through the ODIS Federation.

Creating an entry is a matter of a few minutes, and requires no technical skill 
beyond using a web browser. However, it is key that your organisation is aware 
of the OE entry and approves its creation. Additionally, an individual should be 
nominated to maintain the entry. 

```{caution}
After initially creating your OceanExpert ID, please give 1 business day before
trying to use that login in other tools, such as when logging into the ODIS Catalogue 
(as your OE account must first be approved).
```

## Registering your (meta)data node(s)

![ODISCat logo](images/odiscatLogo.png)

Now that your organisation has an identifier on the web (OceanExpert ID), you can 
register the data systems you wish to connect as ODIS nodes. The ODIS Catalogue of Sources 
(ODISCat) is the system that we use to register, describe, and interlink data sources 
that feed into ODIS.

```{note} 
One organisation can operate many such nodes (e.g. for different types of 
data, services, etc).
```

To register a source, simply go to the [ODISCat website](https://catalogue.odis.org/), 
login with your OE credentials, and create an entry. This should take around 10 minutes.

ODISCat has a dedicated field to let the ODIS Federation know where your metadata 
is. Leave that blank for now: we'll come back to this after we prepare content to 
share via ODIS.

```{note} 
If the person responsible for maintaining your ODISCat entry changes, they should 
<a href="mailto:info@odis.org">contact the ODIS team</a> to transfer the role to another OceanExpert account.
```

## Preparing content 

All ODIS nodes share metadata about their holdings (datasets, documents, 
organisational information, etc) and services (APIs, portals) by exposing structured 
metadata catalogues over the web. 

The first step towards joining ODIS is to generate metadata about your digital 
holdings as JSON-LD files, using schema.org Types and properties. Guidelines 
on how to shape these files is available [here](https://book.odis.org/foundation/foundation.html), and we provide 
a library of examples in the [odis-in](https://github.com/iodepo/odis-in/tree/master/dataGraphs/thematics) repository, 
and templates in this book to help nodes shape their submissions. Note, however, 
that any valid [schema.org](https://schema.org/) Type can be used to share metadata 
through the Federation. 

```{tip} 
Watch a video on "What is JSON-LD?" [here](https://www.youtube.com/watch?v=vioCbTo3C-4)
```

```{note} 
To create and test an initial link to ODIS, you don't need to create 
metadata for all your holdings - a small test set will do.
```

Additional semantics (i.e. beyond what schema.org can offer) can be embedded 
into these files using schema.org's [additionalProperty](https://schema.org/additionalProperty), [DefinedTerm](https://schema.org/DefinedTerm), 
or similar property. An example JSON-LD template for ODIS that leverages 
the additionalProperty parameter can be found [here](https://github.com/iodepo/odis-in/blob/master/dataGraphs/thematics/dataset/graphs/krillMetadata.json).

You can store these files anywhere on the web (under your control), as long 
as they are accessible using standard web protocols. Many ODIS partners that 
have landing pages for their data sets or other digital assets choose to 
embed the JSON-LD inside the record's HTML landing page, such as:

```html
  <script type="application/ld+json">
  {
    "@context": "https://schema.org/",
    "@type": "Dataset",
    "@id": "https://incois.gov.in/essdp/ViewMetadata?fileid=524fd72e-6b2f-4025-94ea-361dce0e9165",
    "name": "Role of Antarctic krills in the biogeochemical cycle in the Indian Ocean sector of Southern Ocean",
    "description": "The Antarctic krill is the largest euphausiid, widely distributed in the Southern Ocean...",   
    ....
  }
  </script>
```

```{tip} 
Today there exists many catalogue software that automatically generates & embeds
the necessary JSON-LD into the record's landing page for you, such as: [GeoNetwork](https://geonetwork-opensource.org/) 
(since version 3.10), [pygeoapi](https://pygeoapi.io/) (since version 0.15.0), 
CKAN (with the [DCAT extension](https://extensions.ckan.org/extension/dcat/) enabled for the "schemaorg" profile),
and many others.
```

### Reusing ODIS patterns

ODIS Partners have co-developed a [library](https://github.com/iodepo/odis-in/tree/master/dataGraphs/thematics) 
of JSON-LD/schema.org patterns (i.e. extended examples of how to format JSON-LD files 
using schema.org Types and properties) to help each other share content in a normative 
way. In general, these patterns give more complete examples of normative usage, 
beyond those offered by the schema.org pages. 

If you have digital assets that fall within the patterns in our book, then reusing 
them is typically just a question of copy, paste, "fill in the blanks" and then 
verifying the validity of the resulting files with, e.g., the [schema.org validator](https://validator.schema.org/).

We strongly recommend all partners keep their JSON-LD files as close to the recommended 
pattern as possible. The more "in pattern" your content is, the more likely it will 
be discovered and (re)used in predictable ways.


### Requesting modifications to existing ODIS patterns

Sometimes, an existing pattern is close you what you need, but there are modifications 
that would make it a better fit (e.g. modifying spatial metadata to include depth more 
explicitly). Many of these modifications are likely to be useful to the whole Federation, 
thus we encourage you to post an issue on our [odis-arch](https://github.com/iodepo/odis-arch/issues) 
GitHub repository. There, you can describe the modification and how it would help improve the description 
& discovery of ocean data, and then the ODIS team can help shape, verify, and integrate 
it into the core recommendations.

### Requesting new patterns

If there are no patterns that match your needs, or you feel that you're stretching an 
existing pattern too far, you can request help from the ODIS coordination team to help 
craft a new one. This process is an excellent opportunity for the  broader ODIS partnership 
to help review and co-develop the pattern, promoting wider interoperability. As above, 
post an issue on our [odis-arch](https://github.com/iodepo/odis-arch/issues) GitHub repository 
describing the need, and ideally providing some example (meta)data that can be adapted.

What follows will be a few rounds of specification development, before we add the new 
pattern to the ODIS Book for all to benefit from and interoperate over.

## Creating a Sitemap

Now that you have content to share, you'll have to tell other agents on the web where 
to find it. This should be done by setting up a sitemap, that points to each JSON-LD 
file you wish the ODIS Federation to be aware of. 

An example sitemap from an ODIS node can be seen [here](https://dataportal.leibniz-zmt.de/sitemap.xml)

```{note}  
If you have many thousands of entries, or you have subsets of links to share, 
you can use a 'sitemap of sitemaps' approach, where one sitemap can point to several 
others.  Here is an example ODIS node with a [sitemap index](https://pacificdata.org/organization/sitemap.xml).
```

### Frequency of change

Add the `<changefreq>` metadata for each sitemap record, for how often you expect 
records in your sitemap to change - this will tell systems like ODIS how often to 
reindex your holdings. Possible values are: `always`, `hourly`, `daily`, `weekly`, `monthly`,
`yearly`, `never`.  Here is a snippet from a sitemap:
:

```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <urlset xmlns="https://www.sitemaps.org/schemas/sitemap/0.9">
     <url>
       <loc>https://example.org/landingpage1</loc>
       <lastmod>2024-06-10</lastmod>
       <changefreq>monthly</changefreq>
     </url>
     <url>
       <loc>https://example.org/landingpage2</loc>
       <lastmod>2024-01-31</lastmod>
       <changefreq>monthly</changefreq>
     </url>  
   </urlset> 
```

```{tip} 
There are many sitemap validator websites that you can leverage, to make sure that
you have generated your sitemap properly, and that it can be read by machines.
```

## Coming full circle: Registering your Sitemap in ODISCat

This is arguably the most important step, as the connection between your node & ODIS 
will be made through the ODISCat entry that you setup earlier through the steps above, but
there are 2 critical fields to fill for the ODIS connection, as follows:

 - log back into [ODISCat](https://catalogue.odis.org/) with your OceanExpert ID
 - click on the "search" link in the top-left
 - click on the "Show my records" link on the Search page
 - click on the "edit record" icon (the pencil) for your record
 - click on the "Basic Description" tab
 - in the "Startpoint URL for ODIS-Arch" field, paste the url to your sitemap.xml file
 - in the "Type of ODIS-Arch URL" field, select "Sitemap"
 
![ODISCat entry](images/odiscatEntry.png)

That's it, now your node's records can be harvested by ODIS! &#x2705;

```{note}  
If your new entry in ODISCat states that `This resource is offline`: ODISCat checks your 
"Datasource URL" daily, so if you have just created a new entry in ODISCat, give it a day 
and check back then to see if the online/offine status is correct.
```

## Frequently asked questions (FAQ)

### How to provide feedback to ODIS?

You can use the [odis-arch](https://github.com/iodepo/odis-arch/issues) issue tracker 
on GitHub, to file any issues or questions for the ODIS team.

### How do I see my records, after completing my ODISCat entry?

The ODIS [Dashboard](http://dashboard.odis.org/) can be used to monitor your node 
inside the ODIS graph.

In terms of seeing your records in the results of the ODIS front-end [search](https://odis.org): 
we will use the frequency values set in your sitemap, to automated the harvesting 
and display of your records in the search results.

### Where are JSON-LD examples that I can use?

The ODIS [Book](https://book.odis.org/thematics/index.html) has good 
examples of each of the ODIS patterns of JSON-LD.  Another excellent resource is 
the [odis-in](https://github.com/iodepo/odis-in/tree/master/dataGraphs/thematics) 
repository where all of the JSON-LD templates often drafted together with partners are stored,
for example see a [datasetTemplate](https://github.com/iodepo/odis-in/blob/master/dataGraphs/thematics/dataset/graphs/datasetTemplate.json) 
there.

### Does ODIS have a SPARQL endpoint?

Yes, the SPARQL endpoint for ODIS is: http://graph.oceaninfohub.org/blazegraph/namespace/oih/sparql

You can find more help on how to use the ODIS SPARQL endpoint [here](https://book.odis.org/users/sparql.html). 
An interface such as [Yasgui](https://yasgui.triply.cc/) can be used to generate your queries.

### Does ODIS have a JSON endpoint?

A JSON endpoint is in discussion for ODIS.  ODIS does have Parquet files that are 
automatically generated for each node (you can get the url for that Parquet file
by selecting a node in the "ODIS Node Summary" section of the [Dashboard](http://dashboard.odis.org/).

### How often does ODIS index my records?

ODIS will use the frequency values set in your sitemap, to automate the harvesting 
and display of your records in the search results.
<!-- End: gettingStarted.md -->


---


# Part: Profiles



---

<!-- Begin: thematics/index.md -->

# Thematic Patterns

## Introduction

These thematic patterns are managed by OIH and the community to add in the discovery and use 
of ocean related resources.  The patterns are simple examples of Schema.org types, with a focus
on the properties and type relations of value to the Ocean InfoHub and the community it engages. 

These "profiles" provide both a starting point for new users and a catalysis for discussion and 
extension with the community.

## Thematic Profiles

These profiles represent a reference implementation of schema.org<n/> [Types](https://schema.org/docs/full.html) 
related to the identified ODIS thematic areas.  They provide a set of minimal elements 
and notes on more detailed elements.  

These are not final and will evolve with community input.  As this process moves forward we will implement
versioning of the profiles to provide stable implementations providers can reliably leverage in their workflows.

### Core Profiles

Six key categories of interest:

1. [Experts and Institutions](thematics/expinst/index.md)
2. [Documents](thematics/docs/index.md)
3. [Spatial Maps](thematics/docs/index.md)
4. [Projects](thematics/projects/index.md)
5. [Training](thematics/training/index.md)
6. [Vessels](thematics/vessels/index.md)


### Supporting Profiles

In support of these five thematic types above, these cross cutting types and properties were 
selected for attention.  They represent some key patterns people may wish to leverage when 
describing their resources.  

1. [Spatial Geometry](thematics/spatial/index.md)
2. [Services](thematics/services/index.md)
3. [Term Lists](thematics/terms/list.md)
4. [Languages](thematics/languages/languages.md)
5. [Linking to Principles](thematics/sdg/index.md)
6. [Identifier Patterns](thematics/identifier/id.md)

```{seealso}
For OIH the focus is on generic documents which can scope reports, data and other resources.
In those cases where the resources being described are of type Dataset you may wish to review
patterns developed for GeoScience Datasets by the ESIP
[Science on Schema](https://github.com/ESIPFed/science-on-schema.org/) community.

```
<!-- End: thematics/index.md -->


---

<!-- Begin: thematics/expinst/index.md -->
<!-- Title from ToC: Core 1: Experts and Institutions -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Experts and Institutions

## About


This thematic type provides a way to describe the experts and institutions. 
In this case the following definitions are used:
  
> Expert:  A person who has a deep understanding of a particular subject area.
>
> Institution: A group of people working together to provide a particular service.
> 
## Example: Person Graph

The following graph present a basic record we might use for a person.  
We will break down some of the key properties used in this graph.

As Ocean InfoHub is levergaing Schema.org we are 
using [schema.org/Person](https://schema.org/Person) for this type.
Any of the properties of Person seen there are valid to use in such a record.

While publishers are free to use as many elements as they wish, our goal 
with this documentation is provide a simple example that address some of the search
and discovery goals of OIH along with those properties most useful in the linking 
of resources between OIH participants.   


```{literalinclude} ../../../odis-in/dataGraphs/thematics/expinst/graphs/person.json
:linenos:
:emphasize-lines: 5-7, 10, 27-32
```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/expinst/graphs/person.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```


### Details: Identifier

For each profile there are a few key elements we need to know about.  One
key element is what the authoritative reference or canonical identifier is for 
a resource.  

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/expinst/graphs/person.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Person",
  "identifier": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```


### Details: nationality

Nationality provide connections to languages a person is
connected with.  The property, [schema.org/nationality](https://schema.org/nationality),
is used to present that.  In the OIH we need to state what the semantics of 
nationality are for our use case. 


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/expinst/graphs/person.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Person",
  "nationality": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```


```{note}
The visual above demonstrates an issue that can be seen in several of the graph.  Where we 
don't use an @id the graph will be represented as a ["blank node"](https://en.wikipedia.org/wiki/Blank_node).  
These will be uniquely identified in the graph, however, in the construction of the visual
this is a common blank node and results in the double arrows pointing to an underscore.
This is a visualization issue and not a proper representation of the graph structure. 
```



### Details: knowsLanguage

Knows about provide connections to languages a person is
connected with.  The property, [schema.org/knowsLanguage](https://schema.org/knowsLanguage),
is used to present that.   Multiple languages can be expressed using the JSON
array [] syntax.   

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/expinst/graphs/person.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Person",
  "knowsLanguage": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```



### Details: Knows About

Knows about provide connections to resources a person is
connected with.  The property, [schema.org/knowsAbout](https://schema.org/knowsAbout),
can connect a Person or Organization to Text, URL or any Thing type.  

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/expinst/graphs/person.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Person",
  "knowsAbout": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```


## Example: Institution Graph

Here we have an example of an data graph for type [schema.org/Organization](https://schema.org/Organization).  
For the identifier we are using the a GRID, but this could also be something like a ROR.  



```{literalinclude} ../../../odis-in/dataGraphs/thematics/expinst/graphs/organization.json
:linenos:
:emphasize-lines: 18-29
```

### On the property membership

Line 18-29 show the inclusion of a [schema.org/member](https://schema.org/member)
property.  There are issues to note here both for consumers (aggregators) and 
providers (publishers).   The Person type is show connected simply on a type and 
id.  This provides the cleanest connection.  If a member is added by type and id, as 
in the case of the "Organization A" link, there is the problem of additional triples
being added.  Here, the name and description properties are going to add triples to the
OIH KG.  In so doing, we run the risk or adding potentially un-authoritative information.
The aggregator doesn't know if triples here are or are not provided by an actor
authoritative for those properties.  This could be addresses with framing or validation 
workflows, or ignored.  The prov elements stored could be leveraged to later track
down sources, but don't provide further information on the issue of authority.  

It is recommended that best practice is to attempt to link only on ids (with a type in 
all cases) where possible.  If you are connecting with a type, do not provide additional 
properties.  In cases where such an id can not be provided, you may wish to fill out 
basic properties you can provide with confidence. 


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/expinst/graphs/organization.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```


### Details: Indentifier

For each profile there are a few key elements we need to know about.  One
key element is what the authoritative reference or canonical identifier is for 
a resource.  

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/expinst/graphs/organization.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Organization",
  "identifier": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```




## References

* [schema:Person](https://schema.org/Person)
* [scheme:Organization](https://schema.org/Organization)
* [Science on Schema Repository](https://github.com/ESIPFed/science-on-schema.org/blob/master/guides/DataRepository.md)
* [https://oceanexpert.org/](https://oceanexpert.org/)
  * [Example page expert](https://oceanexpert.org/expert/44151)
  * [Example page institution](https://oceanexpert.org/institution/10171)
  * [Ocean Expert: reference: Adam Leadbetter](https://gist.github.com/adamml/58ebdc7fc3f8ab8dad5d8852a28fb28c)
<!-- End: thematics/expinst/index.md -->


---

<!-- Begin: thematics/docs/index.md -->
<!-- Title from ToC: Core 2a: Documents -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Documents

## About

Documents: These include datasets, reports or other documents

```{seealso}
For OIH the focus is on generic documents which can scope reports, data and other resources.
In those cases where the resources being described are of type Dataset you may wish to review
patterns developed for GeoScience Datasets by the ESIP
[Science on Schema](https://github.com/ESIPFed/science-on-schema.org/) community.

```

## Creative works (documents)

 Documents will include maps, reports,
guidance and other creative works.  Due to this OIH will focus on a generic example
of [schema.org/CreativeWork](https://schema.org/CreativeWork) and then provide examples
for more focused creative work examples.

```{literalinclude} ../../../odis-in/dataGraphs/thematics/docs/graphs/creativeWork.json
:linenos:
```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils
with open("../../../odis-in/dataGraphs/thematics/docs/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```



### Details: Indentifier

For each profile there are a few key elements we need to know about.  One
key element is what the authoritative reference or canonical identifier is for 
a resource.  

```{code-cell}
:tags: [hide-input]
import json
from pyld import jsonld
import os, sys
import urllib

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)


with open("../../../odis-in/dataGraphs/thematics/docs/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "CreativeWork",
  "identifier": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```


### Publisher and provider

Our JSON-LD documents are graphs that can use framing to subset.  In this case
we can look closer at the `provider` and `publisher` properties, which are both 
of type `Organization`. 


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/docs/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "CreativeWork",
  "provider": {},
  "publisher": {}
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```


### Author type Person

Our JSON-LD documents are graphs that can use framing to subset.  In this 
case we can look closer at the author property which points to a type Person. 


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/docs/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "CreativeWork",
  "author": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### License


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/docs/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "CreativeWork",
  "license": {}
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

#### License as URL  

```json
{
  "@context": "https://schema.org/",
  "license": "https://creativecommons.org/licenses/by/4.0/"
}
```



#### License as CreativeWork 

```json
{
  "@context": "https://schema.org/",
  "license": {
    "@type": "CreativeWork",
    "name": "Creative Commons Attribution 4.0",
    "url": "https://creativecommons.org/licenses/by/4.0/"
  }
}

```
 

#### License as SPDX URL 

- Use a simple URL
- [SPDX](https://spdx.org/licenses/) creates URLs for many licenses including those that don't have URLs
- From a source that <em>harvesters</em> can rely on (e.g. use URL to lookup more information about the license)

```json
{
  "@context": "https://schema.org/",
  "license": "https://spdx.org/licenses/CC-BY-4.0"
}
```

OR, include both the SPDX and the Creative Commons URLs in an array:

```json
{
  "@context": "https://schema.org/",
  "license": ["https://spdx.org/licenses/CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/"]
}
```



### References

* For dataset we can use [SOS Dataset](https://github.com/ESIPFed/science-on-schema.org/blob/master/guides/Dataset.md)
* OBPS group is using JericoS3 API (ref:  https://www.jerico-ri.eu/)
  * Traditional knowledge points here
  * sounds like they use dspace  
* For other document these are likely going to be some [schema:CretiveWork](https://schema.org/CreativeWork) with there being many subtypes we can explore.   See also here Adam Leadbetter's work at [Ocean best practices](https://github.com/adamml/ocean-best-practices-on-schema)
  * This is a great start and perhaps helps to highlight why SHACL shapes are useful
  * https://irishmarineinstitute.github.io/erddap-lint/ 
  * https://github.com/earthcubearchitecture-project418/p419dcatservices/blob/master/CHORDS/DataFeed.jsonld
*[EMODnet](https://emodnet.ec.europa.eu/en)  (Coner Delaney)
  * ERDAP also
  * Are we talking links from schema.org that link to OGC and ERDAP services 
  * Are these methods?  
  * Sounds like may link to external metadata for interop they have developed in the community
* NOAA connected as well
  * Interested in OGC assets  
  * ERDAP data platform
<!-- End: thematics/docs/index.md -->


---

<!-- Begin: thematics/dataset/index.md -->
<!-- Title from ToC: Core 2b: Datasets -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Datasets

## About

Datasets

```{seealso}
For OIH the focus is on generic documents which can scope reports, data and other resources.
In those cases where the resources being described are of type Dataset you may wish to review
patterns developed for GeoScience Datasets by the ESIP
[Science on Schema](https://github.com/ESIPFed/science-on-schema.org/) community.

```

## Datasets

 Documents will include maps, reports,
guidance and other creative works.  Due to this OIH will focus on a generic example
of [schema.org/CreativeWork](https://schema.org/CreativeWork) and then provide examples
for more focused creative work examples.

```{literalinclude} ../../../odis-in/dataGraphs/thematics/dataset/graphs/datasetTemplate.json
:linenos:
```

```{tip}
@id around line#6 should point to whatever resolves eventually to the JSON-LD - if you only
have an external JSON-LD file (and not embedded into the html `<script>` tag)
then the @id should point to the .json file itself. Otherwise, @id should point
to the landing page of the record (HTML page), that embeds the JSON-LD.
```

```{note}
schema.org expects a lat long (Y X) coordinate order, so be aware of that when
you are defining your spatialCoverage, in the GeoShape polygon or box parameters.
```

Using a bounding box for your spatialCoverage is recommended, as it is easy to query 
& display downstream, such as:

```{literalinclude} ../../../odis-in/dataGraphs/thematics/dataset/graphs/datasetTemplate-Box.json
:linenos:
:lines: 56-68
:emphasize-lines: 4-6
```

## Demo area  please ignore

This area is being used to test out a new repository structure where the data graphs, 
frames and SHACL shapes are kept in a discrete location.  


```{code-cell}
:tags: [hide-input]

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore",category=DeprecationWarning)
    
import json
from pyld import jsonld
import os, sys
import urllib
import contextlib

devnull = open(os.devnull, 'w')
contextlib.redirect_stderr(devnull)

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

 
url = "https://raw.githubusercontent.com/iodepo/odis-in/master/dataGraphs/thematics/docs/graphs/map.json"
dgraph = urllib.request.urlopen(url)
doc = json.load(dgraph)

furl = "https://raw.githubusercontent.com/iodepo/odis-in/master/frames/mapFrameID.json"
fgraph = urllib.request.urlopen(furl)
frame = json.load(fgraph)


context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```
<!-- End: thematics/dataset/index.md -->


---

<!-- Begin: thematics/docs/maps.md -->
<!-- Title from ToC: Core 3: Spatial Maps -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Spatial Maps

## About

Map: A map represented by a static file or document



The schema.org type Map only offers one special property beyond
the parent CreativeWork.  That is a [mapType](https://schema.org/mapType) which is an
enumeration of types that do not apply to OIH use cases.  However, the use of the
Map typing itself may aid in narrowing search requests later to a specific creative work.

Schema.org type Map is a subtype of CreativeWork. As such, we can all the approaches 
described in the [Documents](thematics/docs/index.md) section for this type as well.  The use 
of type Map would be focused on documenting files such as KML, GeoJSON or others as a
creative work that may be downloaded and used either in a workflow or directly.  

A map in this context would be a static file or document of some sort.  Map services like 
those described by an OGC Catalogue Service or other GIS service would be described as a 
service.  Potential approaches for doing can be seen the service type.    

```{note}
In the current context, schema.org Map typically references maps as a document.
Here we are likely to reference a KML, Shapefile or GeoPackage.  We may wish to then 
indicate the type of document it is through a mimetype via encoding.  
```

```{literalinclude} ../../../odis-in/dataGraphs/thematics/docs/graphs/map.json
:linenos:
```

```{tip}
@id around line#6 should point to whatever resolves eventually to the JSON-LD - if you only
have an external JSON-LD file (and not embedded into the html `<script>` tag)
then the @id should point to the .json file itself. Otherwise, @id should point
to the landing page of the record (HTML page), that embeds the JSON-LD.
```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/docs/graphs/map.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```


### Details: Identifier

For each profile there are a few key elements we need to know about.  One
key element is what the authoritative reference or canonical identifier is for 
a resource.  

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/docs/graphs/map.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Map",
  "identifier": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### Keywords

We can see three different approaches here to defining keywords.


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/docs/graphs/map.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Map",
  "keywords": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```



### References

* For dataset we can use [SOS Dataset](https://github.com/ESIPFed/science-on-schema.org/blob/master/guides/Dataset.md)
* OBPS group is using JericoS3 API (ref:  https://www.jerico-ri.eu/)
  * Traditional knowledge points here
  * sounds like they use dspace  
* For other document these are likely going to be some [schema:CretiveWork](https://schema.org/CreativeWork) with there being many subtypes we can explore.   See also here Adam Leadbetter's work at [Ocean best practices](https://github.com/adamml/ocean-best-practices-on-schema)
  * This is a great start and perhaps helps to highlight why SHACL shapes are useful
  * https://irishmarineinstitute.github.io/erddap-lint/ 
  * https://github.com/earthcubearchitecture-project418/p419dcatservices/blob/master/CHORDS/DataFeed.jsonld
*[EMODnet](https://emodnet.eu/en)  (Coner Delaney)
  * ERDAP also
  * Are we talking links from schema.org that link to OGC and ERDAP services 
  * Are these methods?  
  * Sounds like may link to external metadata for interop they have developed in the community
* NOAA connected as well
  * Interested in OGC assets  
  * ERDAP data platform
<!-- End: thematics/docs/maps.md -->


---

<!-- Begin: thematics/projects/index.md -->
<!-- Title from ToC: Core 4: Projects -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Projects

## About

Project: An enterprise (potentially individual but typically
collaborative), planned to achieve a particular aim. Use properties from
Organization, subOrganization/parentOrganization to indicate project sub-structures.

## Research Project

This is what a basic research project data graph might look like.  We have
the full record below, but this shows some of the basics we would be 
looking for.

This type is based on the Schema.org type [Project](https://schema.org/Project) which 
has a sub-type of [ResearchProject](https://schema.org/ResearchProject).

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils


with open("../../../odis-in/dataGraphs/thematics/projects/graphs/proj.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "ResearchProject",
  "legalName": "",
  "name": "",
  "url": "",
  "description": "",
  "identifier": {} 
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```



### Details: Identifier

For each profile there are a few key elements we need to know about.  One
key element is what the authoritative reference or canonical identifier is for 
a resource.  

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/projects/graphs/proj.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "ResearchProject",
  "identifier": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

## Full Research Project

Here is what our full record looks like.  We have added in several 
more nodes to cover things like funding source, policy connections,
spatial area served and parent organization. 



```{literalinclude} ../../../odis-in/dataGraphs/thematics/projects/graphs/proj.json
:linenos:
```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/projects/graphs/proj.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

### References

* https://schema.org/Project
  
<!-- End: thematics/projects/index.md -->


---

<!-- Begin: thematics/training/index.md -->
<!-- Title from ToC: Core 5: Training -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Training

## About

A thematic type to describe potential training activities.  In Schema.org a Course
is a subtype of [CreativeWork](https://schema.org/CreativeWork) and [LearningResource](https://schema.org/LearningResource).

As defined from [https://schema.org/Course](https://schema.org/Course):

> Course: A description of an educational course which may be offered as distinct
> instances at which take place at different times or take place at different
> locations, or be offered through different media or modes of study. An
> educational course is a sequence of one or more educational events and/or
> creative works which aims to build knowledge, competence or ability of learners.

We can start by looking at a basic Course description.  

## Simple Course

A basic course might simply present the name and description of the course along 
with a few other key properties. 


```{literalinclude} ../../../odis-in/dataGraphs/thematics/training/graphs/course2.json
:linenos:
:emphasize-lines: 7, 10-15

```

```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils



with open("../../../odis-in/dataGraphs/thematics/training/graphs/course2.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

Here we can see the emphasized line 7 and lines 10-15 highlighting some
unique types.

_courseCode_:
The [courseCode](https://schema.org/courseCode) is used to provide the ID used by the provider for this course. 

_provider_:
The [provider](https://schema.org/provider) is the organization offering the course.
This property is from the CreativeWork supertype.  In this case the provider may
be of type Organization or Person.  For Ocean InfoHub these would be described in 
the [Experts and Institutions](thematics/expinst/index.md) section.

```{note}
In this case you can see we use a simple @id in the provider property.  You can 
see this same @id used in the  [Experts and Institutions](thematics/expinst/index.md) section.
By doing this, we connect this provider to the Organization described by that document.

As such these will be connected in the graph.  So there is no need to duplicate 
the information here.  This is a common graph pattern that allows us to simply 
connect resources.   If there was no existing Organization or Person resource you could
simply create one here.   However, you may also find it useful to create a given 
resource and link to it in the graph. 
```

## Detailed Course

There are a wide range of properties that can be used to describe a course. 
Many of these can be seen at the [Course](https://schema.org/Course) type as
the properties from Course and properties
from [LearningResource](https://schema.org/LearningResource).

We wont go into the details of each property here, but we will show a couple.

The example below present two.  


```{literalinclude} ../../../odis-in/dataGraphs/thematics/training/graphs/course1.json
:linenos:
:emphasize-lines: 4-9, 16, 23-56

```

```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/training/graphs/course1.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

Line 16 shows the [_teaches_](https://schema.org/teaches) property.  It 
should be noted while this propery can point to simple text, it is 
also possible to leverage [DefinedTerm](https://schema.org/DefinedTerm).  This 
means a controlled vocabulary can be used to describe what the course 
teaches.  Ocean InfoHub provides some more information and links to further
information on defined term in
the [Keywords and Defined Terms](thematics/terms/list.md) section. 

Lines 23-56 show using a [hasCourseInstance](https://schema.org/hasCourseInstance)
property to show instances where this course is being taught.  Also of note
in this example are the lines 4-9 in the context where we can type the
endDate and startDate as type dateTime.  By doing this we must provide the
dates in a format that is in line with the [XML Datatype] and in particular the
[ISO 8601 Data and Time Formats](https://www.w3.org/TR/xmlschema-2/#isoformats).

By doing this we can then later conduct searches on the graph that use date ranges
to allow us to find courses, or any resources, that are being taught in a
given time period.

## References

* [RDA Education and Training on handling of research data IG
](https://www.rd-alliance.org/groups/education-and-training-handling-research-data.html)
* [DC Tabular Application Profiles (DC TAP) - Primer](https://www.dublincore.org/groups/application_profiles_ig/dctap_primer/)
* https://www.w3.org/TR/xmlschema11-2/
  * Use YYYY-MM-DDThh:mm:ss or YYYY-MM-DD
* [http://www.marinetraining.eu/](http://www.marinetraining.eu/)
  * [Example page](http://www.marinetraining.eu/node/1001)
* [https://oceanexpert.org/](https://oceanexpert.org/)
* [Example page](https://oceanexpert.org/event/2859)
* [OCTO](https://www.octogroup.org/)
* https://oceansummerschools.iode.org/ 
* https://octogroup.org/webinars/
* https://catalogue.odis.org/search/type=16 
* https://clmeplus.org/
<!-- End: thematics/training/index.md -->


---

<!-- Begin: thematics/vessels/index.md -->
<!-- Title from ToC: Core 6: Vessels -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Vessels

## About

OIH is exploring how we might leverage schema.org to describe research vessels.  
Note that schema.org is a very broad vocabulary and as such specific concepts 
like research vessel is not well aligned to current types.

In Schema.org the type [Vehicle](https://schema.org/Vehicle) is described as a device that is designed 
or used to transport people or cargo over land, water, air, or through space.
We have used this broad scoping to cover research vessels.  We could go on to 
connect this type then to a descriptive property in a concept such as
the WikiData entry for [Research Vessel, Q391022](https://www.wikidata.org/wiki/Q391022).
We may also wish to leverage some of the approaches in [Keywords and Defined Terms](thematics/terms/list.md).


Our goal is to use schema.org as a simple upper level vocabulary that allows
us to describe research vessels in a simple manner and then connect to more 
detailed information on them.  

So the goal here is to show how we can use schema.org as a discovery layer
and then link more directly to detailed institutional metadata records.  

This may also leverage the approaches similar to what is shown in 
the [Publishing Principles](thematics/sdg/index.md) resources.

Observing Infrastructure in general represents an interesting challenge.  A
specified infrastructure could be referenced as a ResearchProject within Schema.org,
though other types would be explored.  One could also build off the base Thing class,
parent to all Schema.org types, then leverage the property schema.org/instrument, itself
of type Thing.  This approach provides an initial starting point to build out the
approach.

It should be noted that [schema.org/Observation](https://schema.org/Observation) also exists but can only
currently be used with the property [schema.org/diseaseSpreadStatistics](https://schema.org/diseaseSpreadStatistics).
However, if seen useful, there is the potential to connect Observation back to a
type of Infrastructure that does not currently exist in Schema.org but could be
proposed.

Addressing the challenge of Observation Infrastructure, and
potentially revisiting the current OIH type Vessel, may involve engagement with
Schema.org itself, something they encourage. 

```{literalinclude} ../../../odis-in/dataGraphs/thematics/vessels/graphs/ship.json
:linenos:
```

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import rdflib
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils


with open("../../../odis-in/dataGraphs/thematics/vessels/graphs/ship.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```


### Details: Indentifier

For each profile there are a few key elements we need to know about.  One
key element is what the authoritative reference or canonical identifier is for 
a resource.  

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/vessels/graphs/ship.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Vehicle",
  "identifier": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### Details: subjectOf

Like SOS, we are recommending the use of subjectOf to link a simple 
Schema.org type to a more detailed metadata description record.  This 
allows us to use the easy discovery layer in Schema.org but connect to 
domain specific metadata records. 

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/vessels/graphs/ship.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Vehicle",
  "subjectOf": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```


## References

* [ICES](https://vocab.ices.dk/?ref=315)
* POGO
* EurOcean
* https://vocab.nerc.ac.uk/search_nvs/C17/
* [SeaDataNet](https://www.seadatanet.org/)
* [Marine Facilities Planner](https://www.marinefacilitiesplanning.com/)
* [EuroFleets](https://www.eurofleets.eu/)
* Identifiers to use include NOCD Code, Call Sign, ICES Shipcode, MMSI Code, IMO Code 
<!-- End: thematics/vessels/index.md -->


---

<!-- Begin: thematics/spatial/index.md -->
<!-- Title from ToC: Support 1: Spatial Geometry -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Spatial Geometry

## About

For spatial geometry Ocean InfoHub guidance will be to use the OGC [GeoSPARQL](https://www.ogc.org/standards/geosparql)
vocabulary to express geometry using Well Known Text (WKT).  The schema.org spatial types and properties are not well 
defined and difficult at times to reliably translate to geometries for use in more Open Geospatial Consortium (OGC)
environments.  

```{note}
schema.org expects a lat long (Y X) coordinate order, so be aware of that when
you are defining your spatialCoverage, in the GeoShape polygon or box parameters.
```

## Simple GeoSPARQL WKT

The following is a simple example of how to embed a WKT string via GeoSPARQL into a JSON-LD record.  
Well Know Text (WKT) is a OGC standard referenced at: https://www.ogc.org/standards/wkt-crs.
A more accessible description and set of examples can be found at WikiPedia:
[Well-known text representation of geometry](https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry).


```{literalinclude} ../../../odis-in/dataGraphs/thematics/spatial/graphs/basic.json
:linenos:
:emphasize-lines: 4, 9-17
```

Line 4 declare the GeoSPARQL prefix for the vocabulary that we will leverage in this document.

Lines 9-17 are the GeoSPARQL node and property definitions.  In this case our type is a simple 
point geometry.  We then go on to declare the asWKT with a type and value.  The value 
is our actual WKT string for our geometry.   We can further 
declare the coordinate reference system (CRS) of the geometry using the crs property.


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/spatial/graphs/basic.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

### WKT Bounding Box

Note that WKT doesn't directly have a bounding box, in that case you 
would need to use a polygon.  The following is an example of a WKT string:

```
POLYGON((45.066730529474505 2.6430807905900235,47.395832091974505 2.6430807905900235,47.395832091974505 0.3588601145746598,45.066730529474505 0.3588601145746598,45.066730529474505 2.6430807905900235))
```

This following the pattern:

```
'POLYGON(x1 y1, x1 y2, x2 y2, x2 y1, x1 y1)'
```

## Classic Schema.org

Ocean InfoHub only recommends the use of Schema.org spatial geometries in 
the case where a provider wishes to be properly indexed by Google and to have the 
spatial information used by Google for maps.  Note, the lack of spatial information will
not prevent Google from indexing your resources.  

Schema.org spatial geometries are not well defined in comparison to OGC standards and 
recommendations.  Also, converting from Schema.org spatial to geometries in WKT or GeoJSON
can be problematic.  There are inconsistencies with
Schema.org guidance for textual geometry representation and that of Well 
Known Text (WKT).

That said, if you desire to leverage Schema.org geometries an example follows.  This 
is a simple example of the existing Schema.org pattern for a lat long value.   There is the 
pending [GeospatialGeometry](https://schema.org/GeospatialGeometry) which is a 
type Intangible (and not Place referenced by spatialCoverage).  This will be a 
subtype of [GeoShape](https://schema.org/GeoShape).   

Schema.org spatial relations are guided by [DE-9IM](https://en.wikipedia.org/wiki/DE-9IM).

```{literalinclude} ../../../odis-in/dataGraphs/thematics/spatial/graphs/sos.json
:linenos:
:emphasize-lines: 8-15
```

Using a bounding box for your spatialCoverage is recommended, as it is easy to query 
& display downstream, such as:

```{literalinclude} ../../../odis-in/dataGraphs/thematics/dataset/graphs/datasetTemplate-Box.json
:linenos:
:lines: 56-68
:emphasize-lines: 4-6
```

```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/spatial/graphs/sos.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```


## Option review, SOS Issue 105

There are several approaches to expressing spatial geometries in JSON-LD.
While Ocean InfoHub will recommend the use of GeoSPARQL, it is worth noting that there 
are alternative and solid cases for using them

One such case could be the case where your WKT geometry string are highly detailed and 
as a result quite long.  These might result in both very large JSON-LD documents that are hard to 
read and maintain.  It may also be that this imparts a performance penalty in your GeoSPARQL 
queries.  

It may be tha that you simplify your WKT geometry strings to a more basic form.  Then link out
to the detailed geometry in a separate document.   The simplified WKT (or Schema.org spatial)
make the documents smaller and easier to read and could help query performance.  The resource
can then point to a dereferencable URL for the detailed geometry.

ref Selfie:  When linking out to complex geometries we recommend following: https://docs.ogc.org/per/20-067.html


From the referenced SOS issue 105:


```{literalinclude} ../../../odis-in/dataGraphs/thematics/spatial/graphs/issue105.json
:linenos:
:emphasize-lines: 4-6, 12,18,28,39,46

```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/spatial/graphs/issue105.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```



## References

* [GeoAPI at GitHub](https://github.com/opengeospatial/geoapi)
* [Science on Schema Issue 105](https://github.com/ESIPFed/science-on-schema.org/issues/105)
  * Leverages [subjectOf](https://schema.org/subjectOf) to connect to a Thing / CreativeWork
* [https://www.unsalb.org/](https://www.unsalb.org/)
* [https://www.un.org/geospatial/](https://www.un.org/geospatial/)
* [schema.org/spatial](https://schema.org/spatial)
* [schema.org/GeospatialGeometry](https://schema.org/GeospatialGeometry)
* SOS patern follows:
  * [spatialCoverage](https://schema.org/spatialCoverage) -> [Place](https://schema.org/Place) -> [geo](https://schema.org/geo) -> [GeoCoordinates](https://schema.org/GeoCoordinates) OR [GeoShape](https://schema.org/GeoShape)
* Some groups are using [GeoNode](https://geonode.org)
  * [schema.org issues](https://github.com/GeoNode/geonode/issues?q=schema.org)
* [ICAN & Schema.org](https://docs.google.com/document/d/1Ya7SNm0h6b04nIVMQ_M65LopxZ6_jojXzTxjfaX5Mxw/edit)
* [OGC SELFIE](https://www.ogc.org/projects/initiatives/selfie)
* [Think broad](https://docs.google.com/presentation/d/1HhuL73g1Bi_d86yT9VGfhvO0Xef9nKhJVwEeRYZ9k0c/edit#slide=id.ga724934615_3_0)
* Science on Schema [spatial for dataset guidance](https://github.com/ESIPFed/science-on-schema.org/blob/master/guides/Dataset.md#spatial-coverage)
<!-- End: thematics/spatial/index.md -->


---

<!-- Begin: thematics/services/index.md -->
<!-- Title from ToC: Support 2: Services -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---
# Service


## About 

This section will provide information on the service type.  This is not 
one of the main OIH types.  However, we will provide guidance here on describing
services using schema.org.

It should be noted that this might be a simple link to an OpenAPI or some 
other descriptor document.  Also, schema.org is not rich enough for complex 
descriptions and itself borrows from the [Hydra](https://www.hydra-cg.com/spec/latest/core/)
vocabulary.  It may be required to leverage Hydra if complex descriptions are 
needed.

The graph describes a service than can be invoked with:

```bash
curl --data-binary "@yourfile.jpg" -X POST https://us-central1-top-operand-112611.cloudfunctions.net/function-1
```

This with POST a jpeg to the service and get back a simple text response with some information
about the image.


```{literalinclude} ../../../odis-in/dataGraphs/thematics/services/graphs/service.json
:linenos:
```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/services/graphs/serviceBase.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)
```

## References

* https://schema.org/docs/actions.html
* https://schema.org/Action
* https://www.w3.org/TR/web-share/
* https://www.hydra-cg.com/spec/latest/core/
<!-- End: thematics/services/index.md -->


---

<!-- Begin: thematics/terms/list.md -->
<!-- Title from ToC: Support 3: Keywords & Defined Terms -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Keywords and Defined Terms

## About
This section is looking at how the keywords could be connected 
with Defined Terms that point to external vocabularies that follow
a vocabulary publishing patterns like at the W3C
[Best Practice Recipes for Publishing RDF Vocabularies](https://www.w3.org/TR/swbp-vocab-pub/).

The pattern breaks down a bit when attempting to connect with things like 
the [Global Change Master Directory keywords](https://earthdata.nasa.gov/earth-observation-data/find-data/idn/gcmd-keywords).
This impedance is caused by publishing approaches for the terms that don't align well with 
the above publishing practices.  This does not mean we can not use these terms, rather that
we may find multiple ways to connect them used by the community.  This can result in some
ambiguity in linking in a community.  



A person could adapt the pattern to connect things like the [Global Change Observing System](https://public.wmo.int/en/programmes/global-climate-observing-system/essential-climate-variables)
or 
[EARTH SCIENCE > OCEANS > OCEAN CHEMISTRY](https://gcmd.earthdata.nasa.gov/KeywordViewer/scheme/all/6eb3919b-85ce-4988-8b78-9d0018fd8089?gtm_keyword=OCEAN%20CHEMISTRY&gtm_scheme=Earth%20Science).  The later of these does have a UUID (6eb3919b-85ce-4988-8b78-9d0018fd8089) but this is not a dereference-able PID.


```{note}
This topic of keyword linking with DefinedTerms is under review at the [Science on Schema](https://github.com/ESIPFed/science-on-schema.org)
work at ESIP.   Reference [Describing a Dataset](https://github.com/ESIPFed/science-on-schema.org/blob/master/guides/Dataset.md)
for the latest on their recommendations. 
```

## Keywords

The Schema.org [keywords](https://schema.org/keywords) property of [CreativeWork](https://schema.org/CreativeWork) can point to three different values.
These are: [DefinedTerm](https://schema.org/DefinedTerm), [Text](https://schema.org/Text) and [URL](https://schema.org/URL).  

We can see the three different approaches here to defining keywords.  Here, _Region X_ is a classic 
text keyword.  The other two are defined as a [DefinedTerm](https://schema.org/DefinedTerm).



```{literalinclude} ../../../odis-in/dataGraphs/thematics/terms/graphs/map.json
:linenos:
:emphasize-lines: 17-31
```

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/terms/graphs/map.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Map",
  "keywords": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)

jbutils.show_graph(framed)

```

### Text

Keywords can be defined as a [Text](https://schema.org/Text) value.  This is the most common approach though 
it doesn't provide some of the benefits of the other two approaches.  For example, it doesn't allow for terms to 
be dereferenced on the net or for connects in the graph to be made for common terms by their subject IRIs. 

```
{
  "@context": "https://schema.org/",
  "keywords": [
    "nitrous oxide", 
    "Central Pacific", 
    "headspace equilibration", 
    "SRI Greenhouse Gas Monitoring Gas Chromatograph", 
    "CTD profiler", 
    "Gas Chromatograph"
  ]
}
```

```{note}
Be sure to use the [] notation to define the keyword.  This defined an array of items vs a single items.  If you
use an approach like {"term1, term2, term4"} you have only created a single text string with comma separated values.  However
that is viewed as a single string in the graph.   The [] notation creates an array of strings all connected to the subject IRI
by the property _keywords_.
```

### URL

Keywords can also point to a URL.  This provides a way to link to a vocabulary entry that defines the term.  This approach 
has some benefits of linking to more details but does easily provide an easy descriptive text for humans.  There is nothing 
preventing putting in a text keyword followed up by another entry with a related URL.

### DefinedTerm

This is the most complex approach.  Keywords can point to a [DefinedTerm](https://schema.org/DefinedTerm) as
defined in a [DefinedTermSet](https://schema.org/DefinedTermSet) pointed to by
the property [inDefinedTermSet](https://schema.org/inDefinedTermSet).  It does offer the ability to present both a human
focused textual name and description of the term.  This is a great way to link to a vocabulary entry that defines the term.
It also allows for a URL to be used to link to the vocabulary entry.   While this approach is the most comprehensive, it does
incur a complexity during the query process to extract and present the information.  

## Defined Terms

During generation of the structured data a provide may wish to
either use or publish a set of controlled vocabulary terms or
a similar set.  

Within schema.org this could be done by leveraging the "DefinedTerm"
amd "DefinedTermSet" types.  

These types allow us both to define a set of terms and
use a set of terms in describing a thing.

Note that DefinedTerm is an intangible and can connect to most
types in Schema.org.  So we can use them in places such as:

* [CreativeWork](https://schema.org/CreativeWork) -> [keyword](https://schema.org/keywords)
* [CreativeWork](https://schema.org/CreativeWork) -> [learningResourceType](https://schema.org/learningResourceType)
* [LearningResource](https://schema.org/LearningResource) -> [teaches](https://schema.org/teaches)  (and many others)
* [LearningResource](https://schema.org/LearningResource) -> [competencyRequired](https://schema.org/competencyRequired)  (and many others)
* [PropertyValue](https://schema.org/PropertyValue) -> [valueReference](https://schema.org/valueReference)

The following example is from the Schema.org [DefinedTermSet](https://schema.org/DefinedTermSet)
reference.

```{literalinclude} ../../../odis-in/dataGraphs/thematics/terms/graphs/term.json
:linenos:
```


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/terms/graphs/map.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

## References

* [schema.org/DefinedTerm](https://schema.org/DefinedTerm)
* [schema.org/DefinedTermSet](https://schema.org/DefinedTermSet)
<!-- End: thematics/terms/list.md -->


---

<!-- Begin: thematics/languages/languages.md -->
<!-- Title from ToC: Support 4: Languages -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---
# Languages

## About

JSON-LD fully support the identification of the language types.  For the canonical 
guide refernece [JSON-LD 1.1 Language-indexing section](https://www.w3.org/TR/json-ld/#language-indexing).

Properties such as label, description, keyword and others can be 
extended in the context with a container language attribute notation.

For example:

```json
{
  "@context": "https://schema.org/",
  "@type": "Person",
  "name": {"@value": "Jane Doe","@language": "en"},
  "jobTitle": "Professor",
  "telephone": "(425) 123-4567",
  "url": "http://www.janedoe.com"
}
```

Shows the name _Jane Doe_ as typed english.  

Use standard language codes (fr, es, en, de, etc) to
be used when describing these properties.   A list of codes can be seen
at the [Online Browsing Platform (OBP)](https://www.iso.org/obp/ui/#search and)
and [Popular standards ISO 3166 Country Codes](https://www.iso.org/iso-3166-country-codes.html).
Additional use the 2-letter codes is demonstrated below.  



```{literalinclude} ../../../odis-in/dataGraphs/thematics/languages/graphs/language.json
:linenos:
```


```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils


with open("../../../odis-in/dataGraphs/thematics/languages/graphs/language.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

In graph space the resulting triples from the above are:

```
<http://example.com/queen> <http://example.com/vocab/label> "Die Königin"@de .
<http://example.com/queen> <http://example.com/vocab/label> "Ihre Majestät"@de .
<http://example.com/queen> <http://example.com/vocab/label> "The Queen"@en .
```

with language encoding attributes in place.  These can be used in
searching and result filters.

Note, this can cause issues in query space since the concept of

```
"Semua orang dilahirkan merdeka dan mempunyai martabat dan hak-hak yang sama. 
Mereka dikaruniai akal dan hati nurani dan hendaknya bergaul satu 
sama lain dalam semangat persaudaraan."
```

and
 
 ```
 "Semua orang dilahirkan merdeka dan mempunyai martabat 
 dan hak-hak yang sama. Mereka dikaruniai akal dan hati nurani 
 dan hendaknya bergaul satu sama lain dalam semangat persaudaraan."@id
 ``` 
 
are different and so care must be taken the creation of the SPARQL 
queries not to accidentally imposed implicate filters through the use 
of language types. 
 

When trying to note the language of a distribution, the approach is a bit different.
Here we are not noting the encoding of the literal value in a record. Rather, we are
providing information about a remote resource.  So for example:

```json
"distribution": [
    {
      "@type": "DataDownload",
      "contentUrl": "https://www.example-data-repository.org/dataset/3300/data/larval-krill.tsv",
      "encodingFormat": "text/tab-separated-values",
      "datePublished": "2010-02-03",
      "inLanguage": "de"	
    }
  ],
```

The above snippet is using the schema.org/inLanguage property to note the resources is in German.

Multiple distributions with multiple languages would look like

```json
"distribution": [
    {
      "@type": "DataDownload",
      "contentUrl": "https://www.example-data-repository.org/dataset/3300/data/larval-krill_de.tsv",
      "encodingFormat": "text/tab-separated-values",
      "datePublished": "2010-02-03",
      "inLanguage": "de"	
    },
   {
      "@type": "DataDownload",
      "contentUrl": "https://www.example-data-repository.org/dataset/3300/data/larval-krill_en.tsv",
      "encodingFormat": "text/tab-separated-values",
      "datePublished": "2010-02-03",
      "inLanguage": "en"	
    }
  ],
```

There is also the schema.org/knowsLanguage for use on other types like Person and Organization.

There you could use the short form like:

```json
"knowsLanguage" : "de"
```

or a more detailed approach like:

```json
"knowsLanguage" : {
      "@type": "Language",
      "name": "Spanish",
      "alternateName": "es"
    }
```
<!-- End: thematics/languages/languages.md -->


---

<!-- Begin: thematics/sdg/index.md -->
<!-- Title from ToC: Support 5: Linking To Principles -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---
# Linking to documents and resources

Leveraging the ability to link between resources can serve many goals.  We may
wish to demonstrate connections between people and courses they have taken or
or organizations they are connected with.   We may be wishing to link documents
to people or organizations.   

This section will review two key thematic profiles and some examples of how to
express links from them to other resources.   Our goal will be different in various
cases.  The two profiles are type CreativeWork and type Organization. 

In the case of _Organization our purpose may be to express alignment to various
principles and policies_.  These might provide people with an understanding of
the goals of an organization when they are searching for or assessing them.

In the case of _CreativeWork we are looking to express connections to the
publisher and provider of the creative work_.   This is mostly to connect these
works with the responsible party associated with them but may also serve to
connect to the principles they are associated with. 



## Organization link options

In the following section we will look at three different options for expressing
links between an organization and resources that describe the policy and 
principles of the subject organization.

First we will see the full data graph.  We have highlighted the sections we 
we will review here.  Namely the subjectOF and publishingPrinciples 
predicates. 



```{literalinclude} ../../../odis-in/dataGraphs/thematics/sdg/graphs/org.json
:linenos:
:emphasize-lines: 31-53
```

```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils


with open("../../../odis-in/dataGraphs/thematics/sdg/graphs/org.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```


### subjectOf


````{card}
Values expected to be one of these types
 
* [Event](https://schema.org/Event)
* [CreativeWork](https://schema.org/CreativeWork)
 

Used on these types
 
* [Thing](https://schema.org/Thing)
 
````

Lets take a look at subjectOf.  In this case we are using subjectOf to express
a connection to a UN SDG.  This, subjectOf, could also be used to connect 
documents describing the policy and principles of an organization or additional 
metadata for a creative work.  When we look at [subjectOf](https://schema.org/subjectOf)
we can see we are allowed are allowed to use it on any type Thing, but must point
to a CreativeWork or Event.  


```{note}
Recall that in the case of OIH types, the type CourseInstance or EducationEvent are both
subtype of Event.  Given that we can use subjectOf to connect a Thing to these types
as well.  Also, Course is a subtype of CreativeWork, so we are good there too in the 
context of the range of subjectOf.   Reference thematic type [Training](thematics/training/index.md)
```

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/sdg/graphs/org.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Organization",
  "subjectOf": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### publishingPrinciples

````{card}
Values expected to be one of these types
 
* [CreativeWork](https://schema.org/CreativeWork)
* [URL](https://schema.org/URL)
 

Used on these types
 
* [CreativeWork](https://schema.org/CreativeWork)
* [Organization](https://schema.org/Organization)
* [Person](https://schema.org/Person)
 
````

Lets take a look at [publishingPrinciples](https://schema.org/publishingPrinciples).  This can be used 
to connect CreativeWork, Organization, or Person to either of CreativeWork or URL.  So this 
allows us to link a CreativeWork to a policy or principle statement.  This has some very useful
use cases where resources can be grouped based on their connection to those principles and policies.  



```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/sdg/graphs/org.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "Organization",
  "publishingPrinciples": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

## Sustainable Development Goals


The following example provides an an approach to connecting 
Sustainable Development Goals 
(SDGs) could be linked to via [subjectOf](https://schema.org/subjectOf).  

Other potential links could be made to things such 
as the [UNDRR-ISC Hazard Definition & Classification](https://www.undrr.org/publication/hazard-information-profiles-supplement-undrr-isc-hazard-definition-classification)

As this is a CreateWork, we can now use one more linking property, the 
Schema.org citation property.  By comparison, the 
[publishingPrinciples](https://schema.org/publishingPrinciples) or 
[subjectOf](https://schema.org/subjectOf) 
connections carry a bit more semantic meaning. 

```{literalinclude} ../../../odis-in/dataGraphs/thematics/sdg/graphs/doc.json
:linenos:
:emphasize-lines: 14-20

```

```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/sdg/graphs/doc.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

### citation

````{card}
Values expected to be one of these types
 
* [Text](https://schema.org/Text)
* [CreativeWork](https://schema.org/CreativeWork)
 

Used on these types
 
* [CreativeWork](https://schema.org/CreativeWork)
 
````

Schema.org [citation](https://schema.org/citation) provides a way to link to another creative work.
This property can be pointed to either Text or CreativeWork.  It should also be noted that citation 
can only be used on type [CreativeWork](https://schema.org/CreativeWork).  

Due to the limit to use on CreateWork only, this example is not seen in the 
above examplewhich is of type Organization.  

The actual semantics of citation is rather vague stating it is a method to 
cite or reference another creative work.   

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/sdg/graphs/doc.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "CreativeWork",
  "citation": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```


## Refs

* [SDGs](http://www.ontobee.org/ontology/SDGIO?iri=http://purl.unep.org/sdg/SDGIO_00000000_)
* [SDG targets](http://www.ontobee.org/ontology/SDGIO?iri=http://purl.unep.org/sdg/SDGIO_00000001)
* [SDG indicators](http://www.ontobee.org/ontology/SDGIO?iri=http%3A%2F%2Fpurl.unep.org%2Fsdg%2FSDGIO_00000003)
<!-- End: thematics/sdg/index.md -->


---

<!-- Begin: thematics/identifier/id.md -->
<!-- Title from ToC: Support 6: Identifier -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Source and Prov Approaches


## About

This section will present an identifier discussion and then focus 
on approaches publishers can use to provide more source and provenance 
information.This section is heavily influenced 
by {cite:ps}`49385` {cite:ps}`googledataset`  and the reader is highly
encouraged to read these references.  

It is not uncommon for a single resource to be described at multiple locations.
The following items represent properties that can help address the 
disambiguation of resources as the Ocean InfoHub graph grows.  

We will look at the following seven properties:
identifier, provider, publisher, sameAs, isBasesOn, subjectOf and its 
inverse, about.  

It should be noted that only subjectOf and sameAs can be used on type
Thing.  That is, these properties can be used on any Schema.org type.

The others have their domain and range values listed.  All these 
properties work on CreativeWork. So they are all valid for that type
and subtypes like Dataset and Map.  



### Example Graph

The following example graph shows some of the properties we can use
to provide source and provenance information about a resource. 


```{literalinclude} ../../../odis-in/dataGraphs/thematics/identifier/graphs/creativeWork.json
:linenos:
:emphasize-lines: 8-34
```

```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/identifier/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```

### identifier

This is the main subject of the start of this section.  Please
refer there for details on this property.  


````{card}
Values expected to be one of these types

* [PropertyValue](https://schema.org/PropertyValue)
* [Text](https://schema.org/Text)
* [URL](https://schema.org/URL)

Used on these types

* [Thing](https://schema.org/Thing)

````


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/identifier/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "CreativeWork",
  "identifier": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

#### propertyID

A commonly used identifier for the characteristic represented by the property, e.g. a manufacturer or a standard code for a property. propertyID can be (1) a prefixed string, mainly meant to be used with standards for product properties; (2) a site-specific, non-prefixed string (e.g. the primary key of the property or the vendor-specific id of the property), or (3) a URL indicating the type of the property, either pointing to an external vocabulary, or a Web resource that describes the property (e.g. a glossary entry). Standards bodies should promote a standard prefix for the identifiers of properties from their standards. 

#### value

The value of the quantitative value or property value node. For PropertyValue, 
it can be 'Text;', 'Number', 'Boolean', or 'StructuredValue'.

#### url (pointing to type URL)

URL of the item.


### provider

schema.org/provider

> The service provider, service operator, or service performer; the goods
> producer. Another party (a seller) may offer those services or goods on behalf
> of the provider. A provider may also serve as the seller.

For OIH this is the agent that is responsible for distributing the resource
and the descriptive metadata.  That is, the provider actually runs and supports
the services that presents the resource on the net or otherwise makes the 
data available. 

````{card}
Values expected to be one of these types

* [Organization](https://schema.org/Organization)
* [Person](https://schema.org/Person)


Used on these types

* [CreativeWork](https://schema.org/CreativeWork)
* [EducationalOccupationalProgram](https://schema.org/EducationalOccupationalProgram)
* [Invoice](https://schema.org/Invoice)
* [ParcelDelivery](https://schema.org/ParcelDelivery)
* [Reservation](https://schema.org/Reservation)
* [Service](https://schema.org/Service)
* [Trip](https://schema.org/Trip) 

````

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/identifier/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "CreativeWork",
  "provider": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### publisher

See: [schema.org/publisher](https://schema.org/publisher) 

The publisher is defined as "The publisher of the creative work".  This is 
viewed as the agent that is primarily responsible for making the content described
by the structured metadata.  

````{card}
Values expected to be one of these types

* [Organization](https://schema.org/Organization)
* [Person](https://schema.org/Person)

Used on these types

* [CreativeWork](https://schema.org/CreativeWork)

````

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/identifier/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "CreativeWork",
  "publisher": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### sameAs

See: [schema.org/sameAs](https://schema.org/sameAs)

The sameAs property links a Thing to a URL.  It is expected that the
URL is a resource that is the the most canonical URL for the original.  

In cases where your resource is not the canonical URL, you can use the
sameAs property to link to the canonical URL.  This is useful when you wish
to publish a resource and give credit to the original resource.  Note, 
in this case the resource must not be altered, but actually be the same 
as the canonical URL resource. 

The sameAs property should always point to only one resource.  It is not 
logically consistent to point to multiple sameAs resources.

````{card}
Values expected to be one of these types

* [URL](https://schema.org/URL)

Used on these types

* [Thing](https://schema.org/Thing)
````

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/identifier/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "CreativeWork",
  "sameAs": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### isBasedOn

See: [schema.org/isBasedOn](https://schema.org/isBasedOn)

Where sameAs is used to link to the canonical URL of the resource, isBasedOn
provides a means to link derivative works to the original resource this new
resources is based on.  

The isBasedOn property can be used to link to multiple resources if more 
than one was used in the generation of this new resource.  

````{card}
Values expected to be one of these types

* [CreativeWork](https://schema.org/CreativeWork)
* [Product](https://schema.org/Product)
* [URL](https://schema.org/URL)

Used on these types

* [CreativeWork](https://schema.org/CreativeWork)

````



### subjectOf and inverse about

See: [schema.org/subjectOf](https://schema.org/subjectOf)

The property subjectOf of can be used to indicate a resource that is related to
the described resource, although not necessarily a part of it. The subjectOf
property can be used in an educational framework to indicate the field(s) of
science or literature the dataset relates to.

````{card}
Values expected to be one of these types

* [CreativeWork](https://schema.org/CreativeWork)
* [Event](https://schema.org/Event)

Used on these types

* [Thing](https://schema.org/Thing)

````

The subjectOf property has an inverse-property [about](https://schema.org/about).
The property about can be used to:

> indicate the subject matter this thing is about

````{card}
Values expected to be one of these types

* [Thing](https://schema.org/Thing)

Used on these types

* [CreativeWork](https://schema.org/CreativeWork)
* [Event](https://schema.org/Event)
* [CommunicateAction](https://schema.org/CommunicateAction)

````


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/identifier/graphs/creativeWork.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@requireAll": "true",
  "@type":     "CreativeWork",
  "subjectOf": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```
<!-- End: thematics/identifier/id.md -->


---

<!-- Begin: thematics/variables/index.md -->
<!-- Title from ToC: Support 7: EOVs -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Essential Ocean Variables

This section details initial documentation of approaches for describing elements of a 
[schema:Dataset](https://schema.org/Dataset) with a focus on approaches supporting Essential 
Ocean Variables.   

A rough description of these links leveraging pseudo schema.org terms follows with a detailed
and valid data graph as an example after that.  

Reference image:

![notes image](thematics/variables/eov.png)


The image above details out some of the key points to be encoded.  These include:

* Links to and description of methods
* QA/QC references
* Links to GOOS Specification sheets
* Information on variables measured
* Connections to the event measured and potential associated instruments
* Spatial coverage
* Temporal coverage

The valid data graph follows the reference section and details follow that.  The highlighted lines
in the data graph represented the detailed sections.   

## References:

* [GOOS reference](https://www.goosocean.org/index.php?option=com_content&view=article&layout=edit&id=283&Itemid=441)
* [GOOS example spec sheet](https://www.goosocean.org/index.php?option=com_oe&task=viewDocumentRecord&docID=17465) and
* [OBIS examples](https://manual.obis.org/examples.html)


```{literalinclude} ../../../odis-in/dataGraphs/thematics/variables/graphs/obisData2.json
:linenos:
:emphasize-lines: 6,10,13,14-30,31,32-50,56-67,77-101,104
```

```{tip}
@id around line#6 should point to whatever resolves eventually to the JSON-LD - if you only
have an external JSON-LD file (and not embedded into the html `<script>` tag)
then the @id should point to the .json file itself. Otherwise, @id should point
to the landing page of the record (HTML page), that embeds the JSON-LD.
```

## license

As licenses are an important cross-cutting item there is a separate section on licenses
at:  [License chapter](thematics/license/index.md)

## keywords

As keywords are an important cross-cutting item there is a separate section on keywords
at:  [Keywords chapter](thematics/terms/list.md)

## variableMeasured

A key section detailing approaches to describing variables.  This property expects either of text or
the more detailed [schema:PropertyValue](https://schema.org/PropertyValue).

```{note}
There can be multiple links in the proertyID property.  Preference should be given to those with semantic descriptions.
```

```{note}
In cases where a single value can be associated with a variable, or a min max value, this can be provided along with a
unitCode property.   In cases where a variable represents a large collection of data this can be omitted and the data obtained
in a distribution reference.  
```



```{seealso}
See also:  [Science on Schema variable](https://github.com/ESIPFed/science-on-schema.org/blob/master/guides/Dataset.md#variables)
```

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils


with open("../../../odis-in/dataGraphs/thematics/variables/graphs/obisData2.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Dataset",
  "variableMeasured": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

## measurementTechnique

[https://schema.org/measurementTechnique](https://schema.org/measurementTechnique) is used to provide either
text about or a URL to information about the techniques or technology used in a Dataset.

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/variables/graphs/obisData2.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Dataset",
  "measurementTechnique": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

## publishingPrinciples

As defined in the [Linking to Principles](https://book.odis.org/thematics/sdg/index.html#publishingprinciples) 
section on publishing principles, This can be used to connect CreativeWork, Organization, or Person to either of 
CreativeWork or URL. So this allows us to link a CreativeWork to a policy or principle statement. 
This has some very useful use cases where resources can be grouped based on their connection to those principles and policies.

For this section on EOVs, it is used to link in the specification sheets for the measured variables.  This can also be used to link
in QA/QC documentation.  There is no direct connection between the creative works linked here and the measured variables though convention 
would be to keep the order the same if possible.  Such order is not maintained through potential serialization of the JSON-LD records though 
list order can be maintained with an @list keyword.  

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/variables/graphs/obisData2.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Dataset",
  "publishingPrinciples": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

## spatialCoverage

More details on spatial elements are found
at:  [Spatial Geometry](https://book.odis.org/thematics/spatial/README.html)

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/variables/graphs/obisData2.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Dataset",
  "spatialCoverage": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

## about

This section is an attempt to leverage schema.org to link instrument information.  This is done via the Event type with a
connected Action type.  


```{seealso}
See also [Identifier and Prov subjectOf and inverse about](https://book.odis.org/thematics/identifier/id.html#subjectof-and-inverse-about).
[schema:about](https://schema.org/about) connects the subject matter of the content.
```


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/variables/graphs/obisData2.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Dataset",
  "about": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

## temporalCoverage

Representation of temporal coverage follows [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) patterns.  ESIP Science on Schema
as has patterns for Deep Time (geologic time) patterns.  

```{seealso}
This section is based on the 
[Science on Schema Temporal Coverage](https://github.com/ESIPFed/science-on-schema.org/blob/master/guides/Dataset.md#temporal-coverage)
```


```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/thematics/variables/graphs/obisData2.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/"},
  "@explicit": "true",
  "@type":     "Dataset",
  "temporalCoverage": ""
}

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)

jbutils.show_graph(framed)

```

### Science on Schema temporalCoverage

Example from Science on Schema recommendations:


```{literalinclude} ../../../odis-in/dataGraphs/thematics/variables/graphs/temporalCoverage.json
:linenos:
```
<!-- End: thematics/variables/index.md -->


---

<!-- Begin: thematics/license/index.md -->
<!-- Title from ToC: Support 8: Licenses -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---

# Licenses


## Schema.org License

- https://schema.org/license
    - `URL`
    - `CreativeWork`

### License as URL  

<pre>
{
  "@context": "https://schema.org/",
  <strong>"license": "https://creativecommons.org/licenses/by/4.0/"</strong>
}
</pre>

### License as CreativeWork  

<pre>
{
  "@context": "https://schema.org/",
  <strong>"license": {
    "@type": "CreativeWork",
    "name": "Creative Commons Attribution 4.0",
    "url": "https://creativecommons.org/licenses/by/4.0/"
  }</strong>
}
</pre>

### License as SPDX URL  

- Use a simple URL
- [SPDX](https://spdx.org/licenses/) creates URLs for many licenses including those that don't have URLs
- From a source that <em>harvesters</em> can rely on (e.g. use URL to lookup more information about the license)

<pre>
{
  "@context": "https://schema.org/",
  <strong>"license": "https://spdx.org/licenses/CC-BY-4.0"</strong>
}
</pre>

OR, include both the SPDX and the Creative Commons URLs in an array:

<pre>
{
  "@context": "https://schema.org/",
  <strong>"license": ["https://spdx.org/licenses/CC-BY-4.0", "https://creativecommons.org/licenses/by/4.0/"]</strong>
}
</pre>
<!-- End: thematics/license/index.md -->


---

<!-- Begin: thematics/depth/index.md -->
<!-- Title from ToC: Support 9: Depth -->

# Depth

## Introduction

This document, in draft form,  presents approaches for the representation of depth in schema.org and
geoSPARQL, via WKT, to aid in the broad and domain-neutral discovery and filtering of resources of interest based
on depth.  


> Note that the term "resource" is used here to mean any digital asset, such as a dataset, software code, applications, etc. The guidance below is focused on describing datasets, but depth can also be used to qualify the regions where software (such as model) is applicable to (e.g. via the areaServed property in Schema.org: https://schema.org/areaServed)

## Scope

The goal is to provide guidance to publishers of metadata records focused on the representation of
depth and elevation values (used interchangeably unless otherwise noted, noting that values may be inverted) that can be used for the discovery and filtering of metadata records in a domain- and discipline-agnostic manner for more global utility.

> It should be noted this guidance is not focused on the representation of depth/elevation in subject data records (i.e. data records of primary interest to an agent), which is typically
> a domain-specific concern. This guidance is concerned with a way to represent those values in the metadata intended for global interoperability.  

We will address two forms of depth representation. The first is a positioning claim: it associates depth metadata to an entire resource, such as the point, collection of points, or lines that describe the entire depth range a dataset pertains to.  These values should be associated with spatial metadata for the orthogonal plane (x,y, latitude, longitude, and similar measures) for full spatial positioning of a resource's relevance or applicability.

The second form is the reporting of a result, such as a series of depth measurements taken by a device. These should be represented as a measured or calculated variable within an appropriate metadata component.

These two approaches can be summarized as:

1) Where depth is a spatial property on some geometry associated with the resource.
2) Where depth is expressed in a variable measured.

Note that a resource might have multiple depth values, say min and max, with multiple
variables measured.  It might also then have some other depth associated with the
geometry or a spatial feature associated with the resource. In each case, depth may be accurately and interoperably expressed, as shown below.


### Depth WKT Open GeoSpatial Consortium (OGC) Encoding

For more precise representation of spatial information, it is recommended to use the 
[OGC geoSPARQL standard](https://www.ogc.org/standard/geosparql/).  This approach leverages
Well Known Text (WKT) for the geometry.  While it is more common to see WKT used to represent 
geometry in two dimension such as:

```text
POINT (0 0)

LINESTRING (0 0, 0 1, 1 2)

POLYGON ((0 0, 1 0, 1 1, 0 1, 0 0))

MULTIPOINT ((0 0), (1 1))

MULTILINESTRING ((0 0, 1 1), (2 2, 3 3))

MULTIPOLYGON (((1 1, 1 3, 3 3, 3 1, 1 1)), ((4 3, 6 3, 6 1, 4 1, 4 3)))
```

There are approaches to representing both elevation, Z, and measurement, M.  

For the Z value an example for POINT would be:

```text
POINT Z (longitude latitude elevation)
```

In the Well-Known Text (WKT) format, the "M" in "POINT M" represents a linear referencing system or a measure value associated with the point geometry. The M value is an additional coordinate used to store a measurement or linear reference along a linear geometry like a line or curve. For points, the M value can represent things like:

* Distance along a path or route
* Time value
* Any other linear measurement or attribute

The format for representing a point with an M value in WKT is:

```text
POINT M (x y m)
```


There is also a 4D representation that includes a measurement M. M is 'measure' an extra axis of information not associated with the cartesian x/y/z space. The most common use for 'measure' is actually for 'measurements', the adding of physically known measurements about a feature to the abstract 'feature' represented in x/y space in the GIS.  This can be seen as:

```text
POINT ZM (longitude latitude elevation depth)
```

For other geometry types like LineString, Polygon, etc., you can follow a similar pattern by including the Z or M values after each coordinate pair. For example, a 3D LineString:

```text
LINESTRING Z (lon1 lat1 elev1, lon2 lat2 elev2, ...)
```

The examples below include cases for a basic POINT, a POINT Z with Z (elevation), a POINT M with M (measurement)
and an example with POINT ZM which includes both elevation and measurement.  


A simple point reference expressed in JSON-LD/schema.org:

```json
{
    "@context": {
        "@vocab": "https://schema.org/",
        "geosparql": "http://www.opengis.net/ont/geosparql#" 
    },
    "@id": "https://example.org/permanentUrlToThisJsonDoc",
    "@type": "Dataset",
    "name": "Data set name",
    "spatialCoverage": {
        "@type": "Place",
        "geo":  
            {
                "@type": "GeoShape",
                "url": "http://marineregions.org/mrgid/4252/geometries?source=25&attributeValue=16",
                "description": "an example POINT Z entry",  
                "geosparql:asWKT": {
                    "@value": "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT Z (30.5 75.2 125.8)",
                    "@type": "geosparql:wktLiteral"
                }
            } 
    }
}
```

It should be noted that it is possible to represent multiple geo entries in various formats in order to align with
potential downstream users.  An intentionally verbose example follows.  

```json
{
    "@context": {
        "@vocab": "https://schema.org/",
        "geosparql": "http://www.opengis.net/ont/geosparql#" 
    },
    "@id": "https://example.org/permanentUrlToThisJsonDoc",
    "@type": "Dataset",
    "name": "Data set name",
    "url": "http://example.org/dataset/X",
    "spatialCoverage": {
        "@type": "Place",
        "geo": [
            {
                "@type": "GeoShape",
                "description": "a basic POINT entry",  
                "geosparql:asWKT": {
                    "@value": "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT (30.5 75.2)",
                    "@type": "geosparql:wktLiteral"
                }
            },
            {
                "@type": "GeoShape",
                "description": "an example POINT Z entry",  
                "geosparql:asWKT": {
                    "@value": "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT Z (30.5 75.2 125.8)",
                    "@type": "geosparql:wktLiteral"
                }
            },
            {
                "@type": "GeoShape",
                "description": "an example POINT M entry",  
                "geosparql:asWKT": {
                    "@value": "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT M (30.5 75.2 404.8)",
                    "@type": "geosparql:wktLiteral"
                }
            },
            {
                "@type": "GeoShape",
                "description": "an example POINT ZM entry",  
                "geosparql:asWKT": {
                    "@value": "<http://www.opengis.net/def/crs/OGC/1.3/CRS84> POINT ZM (30.5 75.2 125.8 404.8)",
                    "@type": "geosparql:wktLiteral"
                }
            }
        ]
    }
}


```




### Depth schema.org

It is also possible to use the elevation property in Schema.org (ref: [https://schema.org/elevation](https://schema.org/elevation)).  
This property is valid for types https://schema.org/GeoCoordinates and https://schema.org/GeoShape.

An example for GeoCoordinate follows.

```json
{
    "@context": {
        "@vocab": "https://schema.org/"
    },
    "@id": "https://example.org/permanentUrlToThisJsonDoc",
    "@type": "Dataset",
    "name": "Data set name",
    "spatialCoverage": {
        "@type": "Place",
        "geo": {
            "@type": "GeoCoordinates",
            "name": "Depth at a point",
            "description": "An example of expressing a depth as a negative elevation for type GeoCoordinates",
            "elevation": -1146,
            "latitude": 16.76203,
            "longitude": -25.10367
        }
    }
}
```

In this example we are using -1146.0 which would imply a depth measurement in meters.

The property elevation can be either a Number or Text.  In the case of Number, it would be taken as an elevation value following 
[WGS 84](https://en.wikipedia.org/wiki/World_Geodetic_System).  

For Text, from the schema.org documentation on elevation, the value of the property may be of the form
'NUMBER UNIT_OF_MEASUREMENT' (e.g., '1,000 m', '3,200 ft') while numbers alone should 
be assumed to be a value in meters. 

We strongly recommend reporting depth in metres, for more global and immediate interoperability.

Note that in this approach elevation would tend to scope an entire geometry and not the individual points that
make up a geometry.    

### Depth Measurement

In cases where the depth information is in the data itself and not connected to a reference geometry 
that can be associated with the resource described by a metadata set, there are still approaches to include depth at the metadata level to aid in discovery.

In this case you can use a stanza in the value space of the schema.org `variableMeasured` property to describe or express the depth variables in your dataset.

variable measured example:

```json
   {
  "@context": {
    "@vocab": "https://schema.org/"
  },
  "@id": "https://example.org/permanentUrlToThisJsonDoc",
  "@type": "Dataset",
  "variableMeasured": [
    {
      "@type": "PropertyValue",
      "name": "depth",
      "description": "Depth (spatial coordinate) relative to water surface in the water body. Definition: The distance of a sensor or sampling point below the sea surface",
      "value": "123.4",
      "propertyID": "https://vocab.nerc.ac.uk/collection/P01/current/ADEPZZ01/",
      "measurementTechnique": "description of technique used or link to full method",
      "unitText": "m",
      "unitCode": [
        "https://qudt.org/vocab/unit/M",
"https://vocab.nerc.ac.uk/collection/P06/current/ULAA/",
        "http://dbpedia.org/resource/Metre"
      ]
    }
  ]
}
```

Note that in the above the type https://schema.org/PropertyValue is presented with a value.  This is not necessary if the goal is to describe the variable, rather tham report its values. However, it is recommended that the range of depth values measured is reported. In the following example, the value has been replaced with the properties
minValue and maxValue.  

```json
   {
  "@context": {
    "@vocab": "https://schema.org/"
  },
  "@id": "https://example.org/permanentUrlToThisJsonDoc",
  "@type": "Dataset",
  "variableMeasured": [
    {
      "@type": "PropertyValue",
      "name": "depth",
      "description": "Depth (spatial coordinate) relative to water surface in the water body. Definition: The distance of a sensor or sampling point below the sea surface",
      "minValue": "34.4",
      "maxValue": "123.4",
      "propertyID": "https://vocab.nerc.ac.uk/collection/P01/current/ADEPZZ01/",
      "measurementTechnique": "description of technique used",
      "unitText": "m",
      "unitCode": [
        "https://qudt.org/vocab/unit/M", "https://vocab.nerc.ac.uk/collection/P06/current/ULAA/",
        "http://dbpedia.org/resource/Metre"
      ]
    }
  ]
}
```


## Appendix

### Links and Resources

- Example NERC term for depth: [NVS](http://vocab.nerc.ac.uk/collection/P01/current/ADEPZZ01/)   (Noted to be narrower than "depth")
- Parameter search at BCO-DMO showing the various depth observations: [Parameter Search | BCO-DMO](https://www.bco-dmo.org/search/parameter/depth)
- [METS RCN Examples](https://github.com/NicoGEOMAR/METS-RCN/tree/main/Examples/Events)
- Some work proposed for this [Extending the GeoSPARQL ontology with full-featured 3D support · Issue #19 · opengeospatial/ogc-geosparql · GitHub](https://github.com/opengeospatial/ogc-geosparql/issues/19) 
- Min max depth URL examples: http://vocab.nerc.ac.uk/collection/P01/current/MAXWDIST/ and http://vocab.nerc.ac.uk/collection/P01/current/MINWDIST/
<!-- End: thematics/depth/index.md -->


---


# Part: Aggregation



---

<!-- Begin: indexing/index.md -->

# Aggregator

## Intoduction


This section introduces the OIH approach to indexing. Currently,  OIH is 
using the [Gleaner](https://github.com/earthcubearchitecture-project418/gleaner) software to do the indexing and leverages the Gleaner IO 
[gleaner-compose](https://github.com/gleanerio/gleaner-compose) Docker 
Compose files for the server side architecture.  For more information on Docker Compose files visit the 
[Overiew of Docker Compose](https://docs.docker.com/compose/).  The gleaner-compose repository holds Docker compose files that can set up 
various environments that Gleaner needs. 

The figure below gives a quick overview of the various compose options for setting up 
the supporting architecture for Gleaner. A fully configured system where all the indexing
and data services are running and exposing services to the net, a total of five containers are run.  In many case
you may run fewer than this.

```{figure} ./images/composeOptions.png
---
name: Compose Options for Gleaner
---
The various compose options for Gleaner
```

### Container overview

* S3 (Minio / AWS): This is the only container that is required in all cases to run.  Gleaner needs an S3 compatible object store.  By default, we use the [Minio](https://min.io/) object store
* Chrome Headless: In cases where providers place the JSON-LD documents into the pages with Javascript, we need to render the page before 
  reading and accessing the DOM.  This is done using Chrome Headless
* Graph database:  Gleaner extracts JSON-LD documents from resources.  These JSON-LD documents are representations of the RDF data mode.  To
  queries on them at scale, it easiest to load the triples into a compatible graph database.  Sometimes we call this a triplestore.  For OIH we
  use the [Blazgraph triplestore](https://github.com/blazegraph/database).  
* Router: If we wish to deploy this setup onto the net, we will route to route all the services through a single domain.  To do this network routing 
  we use [Traefik](https://traefik.io/).  This router is not required for local use and alternative routers like [Caffdy](https://caddyserver.com/) 
  or [nginx](https://www.nginx.com) are also valid options. 
* Web Server: If you wish to serve a web UI for the index, then you can also leverage this setup to serve that.  Again, this is optional and your web site
  may be hosted elswhere and simply call to the index in compliance with CORS settings.  There is an example web server that leverages the object store
  available in this setup.  


### Gleaner

As mentioned Gleaner is a single binary app (ie, one file).  It can be run on Linux, Mac OS X or Windows.  It does
not need to be run on the same machine as the supporting services as it can connect to them 
over the network.  So, for example, they could be hosted in commercial cloud services or 
on remote servers.  

You can download and compile the code from the previously mentioned github repository or 
the [releases page](https://github.com/earthcubearchitecture-project418/gleaner/releases). 

A single configuration file provides the settings Gleaner needs.  Additionally, a local 
copy of the current schema.org context file should be downloaded and available to the app.  This file is needed
for many operations and access it over the net is slow and often rate limited depending on the 
source.   You can download the file at the [Schema.org for Developers](https://schema.org/docs/developers.html) page.  


This setup show in the above figure is the typical setup for Gleaner and is 
detailed in the [Quick Start](indexing/qstart.md) section.


### Indexing Services

This is the basic indexing service requirements.  At a minimum we need the object store and the Chrome headless containers
scoped in the _Indexing Sevices_ box above. More details on this set can be found in [Indexing Servives](indexing/indexingservices.md).

### Data Services

A more expanded set of services is defined in the [Data Services](indexing/dataservices.md) section.  This section discussion a setup more 
designed to address a server setup tht will support indexing and also present the resulting indexes to the broader internet.  
### Web UI

As mentioned, if you wish to serve a web UI for the index, then you can leverage this setup to serve that.  Again, this is optional and your web site
can be hosted elsewhere and simply call to the index in compliance with CORS settings.

### Alternatives

Note, the Gleaner ecosystem is not a requirement.  OIH follows the structured data on the web and data on the web best practices patterns.  Being web architecture based, there are many open source tools and scripting solutions you might use.  You may wish to explore the [Alternative Approaches](indexing/alternatives.md) section for more on this.

What follows is a bit more detail on the setup used by Gleaner.  Experienced users will 
see where they can swap out elements for their own preference.  Like a different 
triplestore, or wish to leverage a commercial object store?  Simply modify the architecture
to do so.  

## ODIS Catalog as Index Source

Before we discuss indexing source a key question is what source will be indexed.
OIH is not a web crawl in that it doesn't move from source to source based on 
the content of those sources. 

Rather, the OIH index is based on a list of sources selected ahead of time.  At
this time that set of sources if based on those partners engaged in the 
development phase of OIH.  As the work moves to a more routine operation 
the sources will come from the [ODIS Catalog](https://catalogue.odis.org/).  

The ODIS Catalog will then act as a curated source of domains for inclusion 
in the Ocean InfoHub.   This will provide a level of curation and vetted of sources
and ensure sources are aware of the technical requirements for inclusion in the 
OIH index.  
<!-- End: indexing/index.md -->


---

<!-- Begin: indexing/qstart.md -->

# Indexing with Gleaner 

![compose options](indexing/images/composeOptions.png)

## Gleaner (app)

The Gleaner applications performs the retrieval and loading of JSON-LD documents 
from the web following structured data on the web patterns.  Gleaner is available for Linux, Mac OS X and Windows.  

While Gleaner is a stand alone app, it needs to interact with
an object store to support data storage and other operations.  These dependencies are met within the 
Gleaner Indexing Services or Data Service Docker compose files.

```{warning}
This documentation is in development.  The primary testing environments are Linux and other UNIX based platforms
such as Mac OS X.   If you are on Windows, there may be some issues.  If you can use a Linux subsystem on Windows, 
you may experience better results.  We will test with Windows eventually and update documentation as needed. 
```

### Quick Start steps

This quick start guide is focused on setting up and testing Gleaner in a local environnement.  It is similar to
how you might run Gleaner in a production environment but lacks the routing and other features likely desired for 
such a situation.


```{note}
This documentation assumes a basic understanding of Docker and experience with basic Docker activities like
starting and stopping containers.  It also assumes an understanding of using a command line interface and 
editing configuration files in the YAML format. 
```

```{admonition} Command
:class: tip
From this point down, the documentation will attempt to put all commands
you should issue in this admonition style box. 
```

In the end, this is the table of applications and config files you will need.  In this guide we will go through 
downloading, setting them up and running Gleaner to index documents from the web.  

```{list-table} Required Applications and Their Config Files
:header-rows: 1

* - Gleaner
  - Docker
  - Minio Client
* - config.yaml
  - ```setenv.sh ``` 
  - ```load2blaze.sh``` 
* - schemaorg-current-https.jsonld
  - gleaner-DS-NoRouter.yml
  - 
```

#### Grab Gleaner and the support files we need

We will need to get the Gleaner binary for your platform and also the Gleaner configuration file 
template.  To do this, visit the [Gleaner Releases page ](https://github.com/earthcubearchitecture-project418/gleaner/releases) 
and pick the release _Ocean InfoHubdev rc1_.  Under the _Assets_ drop down you should see the files we need.  Get:

* Gleaner for your platform
* Gleaner config template: template_v2.0.yaml
* Gleaner indexing service compose file: gleaner-IS.yml
* Helper environment setup script: setenvIS.sh

For this demonstration, we will be running on linux, so this would look something like:

:::{admonition} Command
:class: tip
```bash
curl -L -O https://github.com/earthcubearchitecture-project418/gleaner/releases/download/2.0.25/gleaner
curl -L -O https://github.com/earthcubearchitecture-project418/gleaner/releases/download/2.0.25/gleaner-IS.yml
curl -L -O https://github.com/earthcubearchitecture-project418/gleaner/releases/download/2.0.25/setenvIS.sh
curl -L -O https://github.com/earthcubearchitecture-project418/gleaner/releases/download/2.0.25/template_v2.0.yaml
```
:::

```{note}
You can download these with any tool you wish or through the browser.  Above we downloaded used the command
line curl tool.  For GitHub, be sure to add the -L to inform curl to follow redirects to the object to download.
```

:::{admonition} Command
:class: tip

You may need to change the permission on your gleaner file to ensure it can be run.   On Linux this would 
look something like the following.  

```bash
chmod 755 gleaner
```
:::


We then need to visit [Schema.org for Developers](https://schema.org/docs/developers.html) to pull down the 
appropriate JSON-LD context.  For this work we will want to pull down the _schemaorg-current-https_ in JSON-LD format.  
It also should work to do something similar to the following:

:::{admonition} Command
:class: tip
```bash
curl -O https://schema.org/version/latest/schemaorg-current-https.jsonld
```
:::

#### About the compose file(s)

The above steps have collected the resources for the indexer.   We now want to set up the services that
Gleaner will use to perform the indexing.  To do that we use Docker or an appropriate run time alternative like
Podman or others.   For this example, we will assume you are using the Docker client. 

As noted, a basic understanding of Docker and the ability to issue Docker cli commands to start and stop
containers is required. If you are new do Docker, we recommend you visit and read: 
[Get Started with Docker](https://www.docker.com/get-started).

We need to select the type of services we wish to run.  The various versions of these Docker compose
file can be found in the [Gleaner-compose deployment directory](https://github.com/gleanerio/gleaner-compose/tree/master/deployment).

Why pick one over the other?

> Choose Gleaner IS if you simply wish to retrieve the JSON-LD into a data warehouse to use in your own workflows


> Choose Gleaner DS if you wish to build out a graph and want to use the default contains used by Gleaner.  


```{note}
We wont look at this file in detail here since there will hopefully be no
required edits.  You can see the file in detail in the Index Services
section.
```  


#### Edit environment variables setup script

We have Docker and the appropriate compose file.  The compose files require a set of environment variables
to be populated to provide the local hosts information needed to run.  You can set these yourself or
use or reference the setenv.sh file in the Gleaner-compose repository in the  
[Gleaner-compose deployment directory](https://github.com/gleanerio/gleaner-compose/tree/master/deployment).
You may also need to visit information about permissions at
[Post-installation steps for Linux](https://docs.docker.com/engine/install/linux-postinstall/) if you are
having permission issues.

Let's take a look at the script.

```{literalinclude} ./docs/setenvIS.sh
:linenos:
```

You may wish to edit file to work better with your environment.  By default it will attempt to
use localhost to resolve with and host local runtime data in a /tmp/gleaner directory.  

#### Spin up the containers

Load our environment variables to the shell:

:::{admonition} Command
:class: tip
```bash
source setenv.sh
```
:::

Then start the containers:

:::{admonition} Command
:class: tip
```bash
docker-compose -f gleaner-IS.yml up -d
```
:::

If all has gone well, you should be able to see your running containers with 

:::{admonition} Command
:class: tip
```bash
docker ps
```
:::

and see results similar to:

```bash
CONTAINER ID        IMAGE                            COMMAND                  CREATED             STATUS              PORTS                    NAMES
c4b7097f5e06        nawer/blazegraph                 "docker-entrypoint.s…"   8 seconds ago       Up 7 seconds        0.0.0.0:9999->9999/tcp   test_triplestore_1
ca08c24963a0        minio/minio:latest               "/usr/bin/docker-ent…"   8 seconds ago       Up 7 seconds        0.0.0.0:9000->9000/tcp   test_s3system_1
24274eba0d34        chromedp/headless-shell:latest   "/headless-shell/hea…"   8 seconds ago       Up 7 seconds        0.0.0.0:9222->9222/tcp   test_headless_1
```

#### Edit Gleaner config file

We have all the files we need and we have our support services running.  The next and
final step is to edit our Gleaner configuration file.  This will let Gleaner know
the location of the support services, the JSON-LD context file and the locations
of the resources we wish to index.  

Let's take a look at the full configuration file first and then break down each section.  

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
```


##### Object store

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
:lines: 2-8
```

The minio section defines the IP and port of the object store.  For this case, we are 
using minio and these are the IP and port from our docker compose steps above.  Note,
if you were to use Ceph or AWS S3, this section is still labeled minio.  You simply
need to update the property values.

##### Gleaner

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
:lines: 9-12
```

This passes a few high level concpets.

* runid:
* summon
* mill

##### Context sections

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
:lines: 13-19
```

Comments for the context sections

##### Summoner section

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
:lines: 20-25
```

Comments for the summoner sections

##### Millers section

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
:lines: 26-28
```

Comments for the miller sections


##### Site graphs section

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
:lines: 29-35
```

Comments for the sitegrpah sections


##### Sources section

```{literalinclude} ./docs/gleaner-cfg.yml
:linenos:
:lines: 36-66
```

Comments for the sources sections


#### Run gleaner

For this example we are going to run Gleaner directly.  In a deployed instance you may 
run Gleaner via a script or cron style service.  We will document that elsewhere.

We can do a quick test of the setup.

:::{admonition} Command
:class: tip
```bash
 ./gleaner -cfg template_v2.0 -setup
```
:::


For now, we are ready to run Gleaner.  Try:

:::{admonition} Command
:class: tip
```bash
 ./gleaner -cfg template_v2.0
```
:::


```{note}
Leave the suffix like .yaml off the name of the config file.  The config system can also read
json and other formats.  So simply leave the suffix off and let the config code inspect the 
contents. 
```

### Load results to a graph and test

You have set up the server environment and Gleaner and done your run.  Things look good
but you don't have a graph you can work with yet.    You need to load the JSON-LD into
the triplestore in order to start playing.

#### Minio Object store

To view the object store you could use your browser and point it on the default minio 
port at 9000.  This typically something like localhost:9000.  

If you wish to continue to use the command line you can use the Minio client at
[Minio Client Quickstart guide](https://docs.min.io/docs/minio-client-quickstart-guide.html).

Once you have it installed and working, you can write an entry for our object store with:

:::{admonition} Command
:class: tip
```bash
 ./mc alias set minio http://0.0.0.0:9000 worldsbestaccesskey worldsbestsecretkey
```
:::

#### Load Triplestore

We now want to load these objects, which are JSON-LD files holding RDF based graph
data, into a graph database.  We use the term, triplestore, to define a graph database
designed to work with the RDF data model and provide SPARQL query support over that
graph data.  

* Simple script loading
* Nabu
* Try out a simple SPARQL query

## References

The following are some reference which may provide more information on the various
technologies used in this approach.

* [Google: Understanding how structured data works](https://developers.google.com/search/docs/advanced/structured-data/intro-structured-data)
* [Google Dataset Search By the Numbers](https://arxiv.org/abs/2006.06894) 
* [Google Dataset Search: Building a search engine for datasets in an open Web ecosystem](https://research.google/pubs/pub47845/)
* [W3C SPARQL](https://www.w3.org/TR/sparql11-query/)
* [SHACL](https://www.w3.org/TR/shacl/)
* [Triplestores](https://en.wikipedia.org/wiki/Triplestore)
<!-- End: indexing/qstart.md -->


---

<!-- Begin: indexing/cliDocker/index.md -->

# Gleaner CLI Docker

## About

This is a new approach for quick starts with Gleaner.  It is a script that exposes
a containerized version of Gleaner as a CLI interface.

You can use the -init flag to pull down all the support files you need including
the Docker Compose file for setting up the object store, a triplestore and 
the support for headless indexing.  

## Prerequisites

You need Docker installed.  Later, to work with the results and load them into a
triplestore, you will also need an S3 compatible client.  We will use the Minio
client, mc, for this.  

## Steps

Download the script gleanerDocker.sh from https://github.com/earthcubearchitecture-project418/gleaner/tree/master/docs/cliDocker You may need to make it run-able with 

```bash
curl -O https://raw.githubusercontent.com/earthcubearchitecture-project418/gleaner/master/docs/cliDocker/gleanerDocker.sh

chmod 755 gleanerDocker.sh
```

Next you can run the script with the -init flag to pull down all the support files you need.

```bash
./gleanerDocker.sh -init
```

This will also download the needed docker image and the support files. 
Your directory should look like this now:

```bash
fils@ubuntu:~/clidocker# ls -lt
total 1356
-rw-r--r-- 1 fils fils    1281 Aug 15 14:07 gleaner-IS.yml
-rw-r--r-- 1 fils fils     290 Aug 15 14:07 setenvIS.sh
-rw-r--r-- 1 fils fils    1266 Aug 15 14:07 demo.yaml
-rw-r--r-- 1 fils fils 1371350 Aug 15 14:07 schemaorg-current-https.jsonld
-rwxr-xr-x 1 fils fils    1852 Aug 15 14:06 gleanerDocker.sh
```

Let's see if we can setup our support infrastructure for Gleaner.  The 
file gleaner-IS.yml is a docker compose file that will set up the object store,
and a triplestore.

To do this we need to set up a few environment variables.  To do this we can 
leverage the setenvIS.sh script.  This script will set up the environment we need.
Note you can also use a .env file or other approaches.  You can references 
the [Environment variables in Compose](https://docs.docker.com/compose/environment-variables/) documentation.  

```bash
root@ubuntu:~/clidocker# source setenvIS.sh 
root@ubuntu:~/clidocker# docker-compose -f gleaner-IS.yml up -d
Creating network "clidocker_traefik_default" with the default driver
Creating clidocker_triplestore_1 ... done
Creating clidocker_s3system_1    ... done
Creating clidocker_headless_1    ... done
```

Note:  In a fresh run all the images will be pulled down.  This may take a while.

In the end, you should be able to see these images running:

```bash
root@ubuntu:~/clidocker# docker ps
CONTAINER ID        IMAGE                            COMMAND                  CREATED              STATUS              PORTS                                              NAMES
a26f7c945479        nawer/blazegraph                 "docker-entrypoint.s…"   About a minute ago   Up About a minute   0.0.0.0:9999->9999/tcp                             clidocker_triplestore_1
f3a4197c42be        minio/minio:latest               "/usr/bin/docker-ent…"   About a minute ago   Up About a minute   0.0.0.0:9000->9000/tcp, 0.0.0.0:54321->54321/tcp   clidocker_s3system_1
062f029462b1        chromedp/headless-shell:latest   "/headless-shell/hea…"   About a minute ago   Up About a minute   0.0.0.0:9222->9222/tcp  
```

At this point we should be able to do a run.  During the init process a 
working config file was downloaded.   

> Note:  This config file will change...  it's pointing to an OIH partner 
> and I will not do that for the release.  I have a demo site I will use.  

Next we need to setup our object for Gleaner.  Gleaner itself can do this 
task so we will use 

```bash
root@ubuntu:~/clidocker# ./gleanerDocker.sh -setup -cfg demo
main.go:35: EarthCube Gleaner
main.go:110: Setting up buckets
check.go:58: Gleaner Bucket gleaner not found, generating
main.go:117: Buckets generated.  Object store should be ready for runs
```

> Note:  Here is where we go off the rails.  The config file uses 0.0.0.0 as the 
> location and this is not working.   You need to edit the config file with the 
> "real" IP of the host machine.  In may case is this 192.168.122.77.  This is 
> obviously still a local network IP but it does work.  I am still investigating 
> this issue.

We can now do a run with the example template file.  

> Note:  Best to delete the "sitegraph" node, I will do that soon.  It should 
> work, but is currently slow and gives little feedback

If everything goes well, you should see something like the following:

```bash
root@ubuntu:~/clidocker# ./gleanerDocker.sh -cfg demo
main.go:35: EarthCube Gleaner
main.go:122: Validating access to object store
check.go:39: Validated access to object store: gleaner.
org.go:156: Building organization graph (nq)
org.go:163: {samplesearth  https://samples.earth/sitemap.xml false https://www.re3data.org/repository/samplesearth Samples Earth (DEMO Site) https://samples.earth}
main.go:154: Sitegraph(s) processed
summoner.go:16: Summoner start time: 2021-08-15 14:34:08.907152656 +0000 UTC m=+0.067250623 
resources.go:74: samplesearth : 202
 100% |██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| (202/202, 20 it/s)        
summoner.go:34: Summoner end time: 2021-08-15 14:34:20.36804137 +0000 UTC m=+11.528139340 
summoner.go:35: Summoner run time: 0.191015 
webfeed.go:37: 1758
millers.go:26: Miller start time: 2021-08-15 14:34:20.368063453 +0000 UTC m=+11.528161421 
millers.go:40: Adding bucket to milling list: summoned/samplesearth
millers.go:51: Adding bucket to prov building list: prov/samplesearth
 100% |█████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| (202/202, 236 it/s)        
graphng.go:77: Assembling result graph for prefix: summoned/samplesearth to: milled/samplesearth
graphng.go:78: Result graph will be at: results/runX/samplesearth_graph.nq
pipecopy.go:16: Start pipe reader / writer sequence
graphng.go:84: Pipe copy for graph done
millers.go:80: Miller end time: 2021-08-15 14:34:21.84702814 +0000 UTC m=+13.007126109 
millers.go:81: Miller run time: 0.024649 

```

## Working with results

If all has gone well, at this point you have downloaded the JSON-LD documents into Minio or 
some other object store.Next we will install a client that we can use to work with these objects.

Note, there is a web interface exposed on the port mapped in the Docker compose file.
In the case of these demo that is 9000.  You can access it at
http://localhost:9000/ with the credentials set in the environment variable file.  

However, to work with these objects it would be better to use a command line tool, like mc.
The Minio Client, can be installed
following their [Minio Client Quickstate Guide](https://docs.min.io/docs/minio-client-quickstart-guide.html).
Be sure to place it somewhere where it can be seen from the command line, ie, make sure it
is in your PATH variable. 

If you are on Linux this might look something like:

```
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
./mc --help
```

There is also a [Minio Client Docker image](https://hub.docker.com/r/minio/minio-client/) 
that you can use as well but it will be more difficult to use with the following scripts due
to container isolation. 

To man an entry in the mc config use:

```
mc alias set oih  http://localhost:9000 worldsbestaccesskey worldsbestsecretkey
```

We should now be able to list our object store.  We have set it up using the alias _oih_.

```
user@ubuntu:~/clidocker# mc ls oih
[2021-08-15 14:31:20 UTC]     0B gleaner/
user@ubuntu:~/clidocker# mc ls oih/gleaner
[2021-08-19 13:36:04 UTC]     0B milled/
[2021-08-19 13:36:04 UTC]     0B orgs/
[2021-08-19 13:36:04 UTC]     0B prov/
[2021-08-19 13:36:04 UTC]     0B results/
[2021-08-19 13:36:04 UTC]     0B summoned/
```

You can explore mc and see how to copy and work with the object store.  

## Loading to the triplestore

As part of our Docker compose file we also spun up a triplestore.  Let's use that now.  


Now Download the minio2blaze.sh script.

```bash
curl -O https://raw.githubusercontent.com/earthcubearchitecture-project418/gleaner/master/scripts/minio2blaze.sh
chmod 755 minio2blaze.sh 
```

The content we need to load into the triplestore needs to be in RDF for Blazegraph.  We also need
to tell the triplestore how we have encoded that RDF.   If look in the object store at

```
mc ls oih/gleaner/milled
[2021-08-19 13:26:52 UTC]     0B samplesearth/
```

We should see a bucket that is holding the RDF data converted from the JSON-LD.  Let's use this
in our test.   We can pass this path to the minio2blaze.sh script.  This script will go looking 
for the mc command we installed above, so be sure it is in a PATH location that script can see.  

```
./minio2blaze.sh oih/gleaner/milled/samplesearth
...   lots of results removed 
```

If all has gone well, we should have RDF in the triplestore.  We started our triplestore as part of
the docker-compose.yml file.  You can visit the triplestore at http://localhost:9999/blazegraph/#splash

Note, you may have to try other addresses other than _localhost_ if your networking is a bit different with
Docker.  For me, I had to use a real local IP address for my network, you might also try _0.0.0.0_.

Hopefully you will see something like the following.

![Blazegrah](indexing/cliDocker/images/blaze.png)

We loaded into the default _kb_ namespace, so we should be good there.  We can see that is listed 
as the active namespace at the _Current Namespace: kb_ report.  

Let's try a simple SPARQL query.  Click on the _Query_ tab to get to the query user interfaced. We
can use something like:

```
select * 
where 
{ 
  ?s ?p ?o
}
LIMIT 10
```

A very simple SPARQL to give us the first 10 results from the triplestore.  If all has gone well, 
we should see something like:

![Blazegrah](indexing/cliDocker/images/simplequery.png)

You can explore more about SPARQL and the wide range of queries you can do with it
at the W3C [SPARQL 1.1 Query Language](https://www.w3.org/TR/sparql11-query/) reference. 

## Conclusion

We have attempted here to give a quick introduction to the use of Gleaner in a Docker 
environment.  This is a very simple example, but it should give you an idea of the approach
used.  This approach can then be combined with other approaches documented to establish a 
more production oriented implementation.  Most of this documentation will be located
at the [Gleaner.io GitHub repository](https://github.com/gleanerio) and [Gleaner](https://github.com/gleanerio/gleaner) repository.

> Note: The plan is to merge the Gleaner.io GitHub repository into the first. 
<!-- End: indexing/cliDocker/index.md -->


---

<!-- Begin: indexing/indexingservices.md -->

# Indexing Services

Gleaner can not run alone and relies on a couple of Open Container Initiative (OCI) containers to support it.  For this document, we will assume you are using Docker but this will work with Podman or other OCI compliant orchestration environments.   These Gleaner Indexing Services are necessary to use Gleaner.   The exception to this would be if you are using a 3rd party objects store like AWS S3 or Wasabi.

* Object Store \
   An S3 compliant object store supporting S3 APIs including S3Select.  For open source this is best satisfied with the Minio Object Store.  For commercial cloud AWS S3 or hosted Ceph services will work.  
* Headless Chrome (technically optional) \
  This is only needed where you expect the sources you index to use Javascript to include the JSON-LD in the pages.  If you know your sources do not use this publishing pattern and rather include the JSON-LD in the static page, then you don't need this container running.  


IS represent the minimum required services to support Gleaner.  With IS you have an object
store in the form of [Minio](https://min.io/) and a headless chrome server in the form of 
[chromedp/headless-shell](https://hub.docker.com/r/chromedp/headless-shell).  

As shown in the figure below, and support the basic harvesting of resources with Gleaner
and loading the JSON-LD objects into Minio.

It does not result in these objects ending up in a graph / triplestore.   You would use
this option if you intend to work on the JSON-LD objects yourself.  Perhaps loading 
them into a alternative graphdb like Janus or working on them with python tooling. 


```{figure} ./images/gleaner1.png
---
name: gleaner-IS
---
Basic Gleaner Indexing Service Activity Workflow
```



Gleaner Indexing Services (IS) Environment Variables
The Docker Compose file used to launch the Gleaner IS has a set of configurable elements that can be set and passed to the orchestration system with environment variables.  

These can be set manually or through the command line.  A simple script to set the variables could look like:

```bash
#!/bin/bash

# domains 
export GLEANER_ADMIN_DOMAIN=admin.local.dev
export GLEANER_OSS_DOMAIN=oss.local.dev
export GLEANER_GRAPH_DOMAIN=graph.local.dev
export GLEANER_WEB_DOMAIN=web.local.dev
export GLEANER_WEB2_DOMAIN=web2.local.dev

# Object store keys
export MINIO_ACCESS_KEY=worldsbestaccesskey
export MINIO_SECRET_KEY=worldsbestsecretkey

# local data volumes
export GLEANER_BASE=/tmp/gleaner/
export GLEANER_TRAEFIK=${GLEANER_BASE}/config
export GLEANER_OBJECTS=${GLEANER_BASE}/datavol/s3
export GLEANER_GRAPH=${GLEANER_BASE}/datavol/graph
```

The actual services can be deployed via a Docker Compose file (also works with Podman).  An example of that file and details about it follow.  

-- Break down the compose files here  link to them
<!-- End: indexing/indexingservices.md -->


---

<!-- Begin: indexing/dataservices.md -->

# Data Services

The typical functional goal of this work is the development and use of a Graph that can be accessed via a triplestore (Graph Database).  To do that we need a set of additional containers to support this and expose these services on the web through a single domain with https support.  

* Object Store \
An S3 compliant object store supporting S3 APIs including S3Select.  For open source this is best satisfied with the Minio Object Store.  For commercial cloud AWS S3 or hosted Ceph services will work.  
* Graph Database
* Web Router (technically optional)



## Gleaner Data Services (DS)

If you wish to work with a triplestore and wish to use the default app used by OIH
you can use the compose file that sets up the Gleaner Data Services environment.  

This adds the Blazegraph triplestore to the configuration along with the object store. 

The details of the OIH data services are found in the
 [Data Services](indexing/dataservices.md) section.

```{figure} ./images/gleaner2.png
---
name: gleaner-DS
---
Gleaner Data Service Activity Workflow
```

Typically, a user would wish to run the full Gleaner DS stack which supports
both the indexing process and the serving of the resulting data warehouse and graph 
database capacity.  

Combined, these would then look like the following where the indexing and
data services shared a common object store.  

```{figure} ./images/gleaner3.png
---
name: gleaner-ISDS
---
Gleaner Indexing and Data Service Combined
```

### Object store pattern

Within in the object store the following digital object pattern is used.  
This is based on the work of the RDA Digital Fabric working group.  

```{figure} ./images/do.png
---
name: gleaner-do
---
Gleaner Digital Object Pattern
```





At this point the graph and data warehouse (object store) can be exposed to the net for use by clients such as jupyter notebooks or direct client calls to the S3 object APIs and SPARQL endpoint.

Gleaner Data Services (DS) Environment Variables
The Docker Compose file used to launch the Gleaner DS has a set of configurable elements that can be set and passed to the orchestration system with environment variables.  

These can be set manually or through the command line.  A simple script to set the variables could look like:

-- Environment Var settings script

The actual services can be deployed via a Docker Compose file (also works with Podman).  An example of that file and details about it follow.  

Let's take a look at this.

```{literalinclude} ./docs/setenv.sh
:linenos:
```


-- Break down the compose file here

```{literalinclude} ./docs/gleaner-DS-NoRouter.yml
:linenos:
```



NOTE:  DS also needs the object -> graph sync (via Nabu)
NOTE:  Should also add in (here or to the side) the ELT local Data Lake to Data Warehouse path (ala CSDCO VaultWalker)


![](publishing/images/do.png)
<!-- End: indexing/dataservices.md -->


---

<!-- Begin: indexing/graphpub.md -->

# Graph First Approach

## About

During the early adopters meetings and in discussion with others an alternative publication pattern came up.  This is the pattern where it is not possible to update the web resources with the metadata content.  This may be due to access or technical issues.  Regardless, what was possible was to generate the metadata in bulk locally and make the resulting document available.

This approach is not ideal since it is a non-standard pattern and makes the data and information more obscure to other users.  However, it is one the OIH architecture can adapt to and is preferable to the option of excluding those partners in this activity.  

As such, we are making some changes to allow for this pattern.  This means documenting the published graph structure based on the existing thematic patterns and some updates in the indexing workflow to obtain and integrate these graphs into the OIH graph.  

 ```{warning}
 Anti-pattern:
 Using the approach here is not in alignment with 
 Google guidance nor with W3C patterns for structured
 data on the web.  
 
 It is documented here for edge cases
 where this is the minimum viable approach.  The hope is it 
 could act as a gateway to a more standards aligned implementation later.
```

## Graph Only

There are cases where it is only possible to generate the graph
based on the metadata.  Access to the HTML pages is either difficult or the process of inserting the 
data into the pages is not supportable.  

For this case the goal is to create a simple graph in JSON-LD.  To do this we need a collection 
approach that is valid for a range of Things.  

For this it is proposed to use ItemList which can be used on a list of type Thing, ie anything 
type in the Schema.org vocabulary.  

This would define a ListItem with item of any type.  Below is an example for a CreativeWork (map)
and a Course.  Once you are in a "item" any of the details from the other thematic type descriptions 
can be used.  


```JSON
{
  "@context": "https://schema.org/",
  "@type": ["ItemList", "CreativeWork"],
  "@id": "https://example.org/id/graph/X",
  "name": "Resource collection for site X",
  "author": "Creator of the list",
  "itemListOrder": "https://schema.org/ItemListUnordered",
  "numberOfItems": 2,
  "itemListElement": [
    {
      "@type": "ListItem",
      "item": {
           "@id": "ID_for_this_metadata_record1",
           "@type": "Map",
            "@id": "https://example.org/id/XYZ",
            "name": "Name or title of the document",
            "description": "Description of the map to aid in searching",
            "url":  "https://www.sample-data-repository.org/creativework/map.pdf"
      }
    },
    {
      "@type": "ListItem",
      "item": {
           "@id": "ID_for_this_metadata_record2",
            "@type": "Course",
            "courseCode": "F300",
            "name": "Physics",
            "provider": {
                "@type": "CollegeOrUniversity",
                "name": "University of Bristol",
                "url": {
                    "@id": "/provider/324/university-of-bristol"
                }
            }
        }
    }
  ]
}
```

In the case of schema:Dataset one might use schema:DataCatlogue for the following approach.  However, 
since OIH is addressing a wide range of types a more generic collection of Things or CreativeWorks 
approach is needed.

## Item Catalogue Page

It's not hard to generate a simple HTMl page based on the structured metadata file.  This doesn't 
alter the content of the graph, just builds an automated HTMl page around it.

## Publishing and referencing

## Testing

Since we are now dealing with a graph that is pulled as a complete entity there are a few thoughts.

1. How do ensure a connection between a record in the list and a resolvable URL?  Do we need
to:
    1. ensure each record has a IRI it is subject of
    2. in the case where IRI is or can be URL, do a validation of at least a 200 on it
2. How do we publish this?
   1. entry in robots.txt (might be able due to reasons above?)
   2. published and provided to OIH
3. Need guidance on format and structure
<!-- End: indexing/graphpub.md -->


---

<!-- Begin: indexing/prov/index.md -->
<!-- Title from ToC: Indexing Activity Prov -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---
# Prov

## About

This is the start of some discussion on issues around prov tracking in OIH.
This may take two paths.  One would be the prov tracking indexers might do
and the other prov that providers would encode to provide specific prov
the community requests.

## Gleaner Prov

The Gleaner application generates a prov graph of the activity of accessing 
and indexing provider resources.  The main goal of this prov is to connect
an indexed URL to the digital object stored in the object store.  This 
digital object should be the JSON-LD data graph presented by the provider. 

By contrast, the authoritative reference in the various profiles will connect
the the data graph ID, or in the absence of that the data graph URL or the 
referenced resources URL by gleaner, to another reference.  This may be 
an organization ID or a PID of the connected resource. 



```{literalinclude} ./graphs/gleaner.json
:linenos:
```

```{code-cell}
:tags: [hide-input]

import json
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.extras.external_graph_libs import rdflib_to_networkx_graph
from pyld import jsonld
import graphviz
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/indexing/prov/graphs/gleaner.json") as dgraph:
    doc = json.load(dgraph)

frame = {
  "@context": {"@vocab": "https://schema.org/",
  "prov": "http://www.w3.org/ns/prov#"},
  "@explicit": "false",
  "@type":     "prov:Activity",
   "prov:generated": {},
   "prov:endedAtTime": {},
   "prov:used": {}
}


context = {
  "@vocab": "https://schema.org/",
  "prov": "http://www.w3.org/ns/prov#"
}

compacted = jsonld.compact(doc, context)

framed = jsonld.frame(compacted, frame)
jd = json.dumps(framed, indent=4)
print(jd)


```


## Nano Prov

This is a basic nanoprov example. Note, this is a draft and
the ID connections and examples have not been made yet.  


```{literalinclude} ./graphs/nanoprov.json
:linenos:
```

```{code-cell}
:tags: [hide-input]

import json
from pyld import jsonld
import os, sys

currentdir = os.path.dirname(os.path.abspath(''))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)
from lib import jbutils

with open("../../../odis-in/dataGraphs/indexing/prov/graphs/nanoprov.json") as dgraph:
    doc = json.load(dgraph)

context = {
    "@vocab": "https://schema.org/",
}

compacted = jsonld.compact(doc, context)
jbutils.show_graph(compacted)

```



## Refs

[Nanopubs Guidance](https://nanopub.org/guidelines/working_draft/)
<!-- End: indexing/prov/index.md -->


---

<!-- Begin: indexing/alternatives.md -->

# Alternatives

## Options

While [Gleaner](https://gleaner.io/) will be used during initial OIH development it is not
the only or required approach.   The web architecture foundation means there are many other tools that
can be used and might be leveraged in a production environment including:

* [Extrunct](https://github.com/scrapinghub/extruct)
* [BioSchemas Tools](https://bioschemas.org/software)
* [LDSpider](https://github.com/ldspider/ldspider)
* [StormCrawler](https://github.com/DigitalPebble/storm-crawler)
* [Squirrel](https://dice-group.github.io/squirrel.github.io/overview.html)
* [Nutch (Apache)](http://nutch.apache.org/)
* [Laundromat](https://github.com/LOD-Laundromat/LOD-Laundromat)
* [DataArchiver](https://github.com/websi96/datasetarchiver)
* [OD Archiver](https://archiver.ai.wu.ac.at/)

These different tools may better fit into the workflow and available
skill sets for a group.
<!-- End: indexing/alternatives.md -->


---


# Part: Tooling



---

<!-- Begin: tooling/index.md -->

# Tooling

## About

The tooling section is a collection of tools, scripts, notebooks and other software that could 
be of use to the various personas of Ocean InfoHub

### OpenRefine

In this section you will find some details around
the Open Refine project and how to use it to 
generate JSON-LD documents. 

### Notebooks

In this section you will find some Jupyter Notebooks
that demonstrate working with JSON-LD in various
ways.  These can be copied and used locally to
explore or implement workflows.

## On-line tooling

[Schema.org Validator](https://validator.schema.org/)

[json-ld playgroud](https://json-ld.org/playground/)

[SHACL Playground](https://shacl.org/playground/)

[json-lint](https://jsonlint.com/)

[f-uji](https://www.fairsfair.eu/f-uji-automated-fair-data-assessment-tool)

## Dev

[json-ld](https://json-ld.org)

[f-uji dev](https://github.com/pangaea-data-publisher/fuji)

[jq](https://stedolan.github.io/jq/)

[jello (python)](https://github.com/kellyjonbrazil/jello) and
[Practical JSON at the command line using jello](https://blog.kellybrazil.com/2021/06/24/practical-json-at-the-command-line-using-jello/amp/)

[Python Extruct](https://github.com/scrapinghub/extruct)
<!-- End: tooling/index.md -->


---

<!-- Begin: tooling/ckan.md -->

# Installing a CKAN Catalogue and connecting to ODIS

![CKAN logo](tooling/images/ckan-logo.png)

## Background

The following document explains how to set up a full metadata catalogue software 
architecture, with settings enabled to connect the catalogue to ODIS.

The initial steps are for [CKAN](https://ckan.org/), and specifically on 
Windows.  You will have a choice to install CKAN through [Docker](https://www.docker.com/), 
which is recommended, or to install CKAN (and its dependencies) manually, 
which is much more difficult.

## Intended Audience

The intended audience of these steps is for a technical person to follow, as
the steps require familiarity with running commands at the commandline, and 
executing various scripts.

## Windows Versions Supported

The following steps were created on Windows Server 2022, but should work on 
Windows 11 or 10.  You will be required to have full Administrator access on 
your server.

## Option 1: Install CKAN through Docker (recommended)

We will follow the [Docker Compose steps for CKAN](https://github.com/ckan/ckan-docker/blob/master/README.md).

### Install WSL

To install Docker, we must install the WSL (Windows Subsystem for Linux),
as follows:
  - follow https://learn.microsoft.com/en-us/windows/wsl/install
  - open CMD window and execute:
    - set the version of WSL to 2
      ```
      wsl --set-default-version 2
      ```
    - see list of all Linux distribution names
      ```
      wsl --list --online
      ```
    - now install Ubuntu
      ```
      wsl --install --distribution "Ubuntu-24.04"
      ```
      
      ![wsl install1](tooling/images/wsl-install1.png)
      
  - reboot machine
  - you should see a progress bar for installing Ubuntu
  - when asked to create a new user, enter:
    ```
      username: odis
      password: yourpassword
    ```
    ```{caution}
    The WSL user has a lot of power (they have sudo/super-user permissions); 
    it is strongly recommended that users change `yourpassword` to a secure 
    and unique password for this account and keep hold of it in a password 
    manager. That way if someone manages to hack CKAN and gain remote code 
    execution capabilities, it won't be so easy for them to gain super-user 
    control.
    ```
  - to run: goto Start menu, choose "WSL"
    - CMD window should open with an `odis@` prompt
  - to check the Ubuntu version, execute: 
    ```
    lsb_release -a
    ```
    which should return:
    ```
        Distributor ID: Ubuntu
        Description:    Ubuntu 24.04 LTS
        Release:        24.04
        Codename:       noble
    ```
    
    ![wsl install2](tooling/images/wsl-install2.png)
    
### Install Docker Engine

We will follow the steps [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/).

- assuming you are still at the `odis@` prompt, but if not:
  - goto Start menu, choose "WSL"
  - CMD window should open with an `odis@` prompt
- execute the following, to update your Ubuntu packages
  ```
  sudo apt update
  sudo apt upgrade
  ```
- execute the following, to remove conflicking packages
  ```
  for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do sudo apt-get remove $pkg; done
  ```
- execute the following, to setup Docker's `apt` repository
  ```
  # Add Docker's official GPG key:
  sudo apt-get update
  sudo apt-get install ca-certificates curl
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc

  # Add the repository to Apt sources:
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update
  ```
- now install the Docker packages by executing:
  ```
  sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  ```
  if successful, the response should contain the message `Hello from Docker!`.
  
  ![docker install1](tooling/images/docker-install1.png)
  
  you can also try a `docker version` command
  
  ![docker install2](tooling/images/docker-install2.png)
  
### Clone the ckan-docker repository locally

- assuming you are still at the `odis@` prompt, but if not:
  - goto Start menu, choose "WSL"
  - CMD window should open with an `odis@` prompt
- execute the following, to clone the `ckan-docker` repo locally
  ```
  git clone https://github.com/ckan/ckan-docker.git ckan-docker-git-master
  ```

  ![git install1](tooling/images/git-install1.png)
  
### Install (build and run) CKAN plus dependencies

- execute `cd ckan-docker-git-master`
- make a copy the the `.env` file for our needs
  ```
  cp .env.example .env
  ```
- you can optionally change the .env values for your needs, such as
  for the admin user/password
  ```
  #use vi to open the .env file
  vi .env
  #to make your changes, first press your "i" key (for INSERT mode), and
    #then edit the desired lines
  #then save with the command
  :wq
  ```
  
  ![env install1](tooling/images/env-install1.png)
  
- build the Docker images
  ```
  docker compose -f docker-compose.yml build
  ```
  you should see a response that states `Service ckan: Built`
  
  ![build install1](tooling/images/build-install1.png)
  
- start the Docker containers
  ```
  docker compose up -d
  ```
  you should see a response that states that 6 containers are `Healthy`
  
  ![compose install1](tooling/images/compose-install1.png)
  
- check status of containers by executing:
  ```
  docker ps
  ```
  
  ![compose install2](tooling/images/compose-install2.png)
  
### Goto CKAN's landing page

Now you are ready to open your CKAN instance in your web browser.

- in FireFox or Chrome, goto: https://localhost:8443/

  ![ckan wsl install1](tooling/images/ckan-wsl-install1.png)
  
### Install Portainer (Recommended) to manage containers

Portainer offers a user-friendly interface to manage the CKAN containers.
We will follow the [Portainer installation steps](https://docs.portainer.io/start/install-ce/server/docker/wsl) 
for WSL.

#### Setup Portainer Server

- assuming you are still at the `odis@` prompt, but if not:
  - goto Start menu, choose "WSL"
  - CMD window should open with an `odis@` prompt
- execute the following, to create the volume that Portainer Server 
  will use to store its database:
  ```
  docker volume create portainer_data
  ```
- then download and install the Portainer Server container:
  ```
  docker run -d -p 8000:8000 -p 9443:9443 --name portainer --restart=always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer-ce:2.21.4
  ```
- Check that the Portainer Server container has started by executing:
  ```
  docker ps
  ```
  
  ![portainer install1](tooling/images/portainer-install1.png)
  
  You should see a `portainer` line with the `Status` reporting `Up for xxx minutes`
  
#### Login to the Portainer Server

- you can now login using your web browser at https://localhost:9443
  - if you receive a message of `Your Portainer instance timed out for security purposes`,
    this occurs when you do not login within 5 minutes of performing the initial 
    setup.  You can execute the following (which will give you another 5 minutes 
    to complete the initial setup):
    ```
    docker stop portainer
    docker start portainer
    ```
- you should now see a page where you can create a user.  Be sure to create a unique 
  password and then click `Create user`.  You may wish to disable the `Allow collection
  of anonymous statistics`.
  
  ![portainer install2](tooling/images/portainer-install2.png)
  
- you should now see a `Welcome to Portainer` page, and then you can click the `Get
  Started` button, to start using Portainer.
  
  ![portainer install3](tooling/images/portainer-install3.png)
  
#### Manage your containers with Portainer
  
- in the left panel, click on `Containers` to then see a list of your CKAN containers, 
  and then interact with them if need be (stop/start/restart etc.).
  
  ![portainer install4](tooling/images/portainer-install4.png)
  
### Install DCAT extension for JSON-LD Support

We will follow the Docker compose [README](https://github.com/ckan/ckan-docker/blob/master/README.md) for CKAN, 
as well as the [ckanext-dcat](https://extensions.ckan.org/extension/dcat/#structured-data-and-google-dataset-search-indexing) 
extension notes.

#### Edit the Dockerfile to install the ckanext-dcat extension

- assuming you are still at the `odis@` prompt, but if not:
  - goto Start menu, choose "WSL"
  - CMD window should open with an `odis@` prompt
- execute `cd ckan-docker-git-master`
- now use `vi` to add in the required section for the ckanext-dcat plugin into
  the `Dockerfile` :
  ```
  #use vi to open the Dockerfile
  vi ckan/Dockerfile
  #to make your changes, first press your "i" key (for INSERT mode), and
    #then edit the desired lines
  #then save with the command
  :wq
  ```
- around line#6, paste the following into the `Dockerfile`:
  ```
  ### prevent permissions errors when installing ckanext-dcat extension
  USER root

  ### DCAT ###
  RUN  pip3 install -e 'git+https://github.com/ckan/ckanext-dcat.git@v2.1.0#egg=ckanext-dcat'  && \
       pip3 install -r https://raw.githubusercontent.com/ckan/ckanext-dcat/v2.1.0/requirements.txt
  ```
- save the file
  
#### Edit the .env file to load the Extensions

Inside the `ckan-docker-git-master` directory, use `vi` to edit the `.env` file
to add the `dcat` and `structured_data` plugins, as follows:

- open the .env file:

  ```
  vi .env
  ```
- around line#69, change the `CKAN__PLUGINS` line to add the 2 extensions, such as:

  ```
  CKAN__PLUGINS="image_view text_view datatables_view datastore datapusher envvars dcat structured_data"
  ```
  
- save the file
  
#### Rebuild the containers

- build the Docker images
  ```
  docker compose -f docker-compose.yml build
  ```
  you should see a line mentioning the `RUN pip3 install -e` command that 
  we defined in the Dockerfile.
  
  ![dcat install1](tooling/images/dcat-install1.png)
  
- start the Docker containers
  ```
  docker compose up -d
  ```
  
#### Check the status

We can use the CKAN API to check if the new plugins were loaded successfully.

- using the [Firefox](https://www.mozilla.org/en-CA/firefox/new/) browser (which
  displays the JSON results nicely), goto: https://localhost:8443/api/action/status_show
  
- you should see a list of extensions that include both `dcat` and 
  `structured_data`, such as:
  
  ![build install2](tooling/images/dcat-install2.png)

#### Connect to the CKAN container through commandline

You will need to connect to the CKAN container through the commandline, which
can be done through the following steps:

- you will need to get the exact name of the CKAN container, which is easiest
to see through Portainer.

  ![ckan connect1](tooling/images/ckan-connect1.png)
  
  You can see above that the container name is `ckan-docker-git-master-ckan-1`.
  
- assuming you are still at the `odis@` prompt, but if not:
  - goto Start menu, choose "WSL"
  - CMD window should open with an `odis@` prompt
- execute the following, to connect to the CKAN container (replace "ckan-docker-git-master-ckan-1" with your container name) :
  ```
  docker exec -it ckan-docker-git-master-ckan-1 /bin/bash -c "export TERM=xterm; exec bash"
  ```
  
  Your prompt should change to something like `ckan@af2e2e3ac57f`.  If you then
  execute `pwd` you can see that you are in the `/srv/app/` directory, on the CKAN
  container.
  
  ![ckan connect2](tooling/images/ckan-connect2.png)
  
#### Install VI on the CKAN container

If you get a `command not found` error when trying to open a file with `vi` 
on the ckan container, you will have to first connect as root, and then install 
`vim`, as follows:

- execute the following, to connect to the CKAN container as root (replace "ckan-docker-git-master-ckan-1" with your container name) :
  ```
  docker exec -u root -it ckan-docker-git-master-ckan-1 /bin/bash
  ```
  
- now update your local packages:
  ```
  apt-get update
  ```
  
- finally install `vim`:
  ```
  apt-get install vim
  ```
  
Then retry your `vi `command.
  
#### Modify the CKAN template

Once connected to the CKAN container (see previous step), you can edit
the `read_base.html` Jinja2 template files, to add a JSON-LD block,
as follows:

- now use `vi` to edit the `read_base.html` file:
  ```
  vi src/ckan/ckan/templates/package/read_base.html
  ```
- in the `{% block head_extras -%}` section, around line#13, paste 
  the following:
  ```
  {% block structured_data %}
    <script type="application/ld+json">
  
    </script>
  {% endblock %}
  ```
  
- save the file, and `exit` the container

- back on your host machine, restart the CKAN container
  ```
  docker restart ckan-docker-git-master-ckan-1
  ```
  
- if you have added a Dataset, now if you right-click on the dataset's 
  main page (that url would be something like https://localhost:8443/dataset/point-test )
  you should see a `<script type="application/ld+json">` section inside
  the page source (which is the embedded JSON-LD, that is required by ODIS),
  similar to the following snippet:
  ```json
    {
        "@context": {
            "brick": "https://brickschema.org/schema/Brick#",
            "csvw": "http://www.w3.org/ns/csvw#",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcam": "http://purl.org/dc/dcam/",
            "dcat": "http://www.w3.org/ns/dcat#",
            "dcmitype": "http://purl.org/dc/dcmitype/",
            "dcterms": "http://purl.org/dc/terms/",
            "doap": "http://usefulinc.com/ns/doap#",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "geo": "http://www.opengis.net/ont/geosparql#",
            "odrl": "http://www.w3.org/ns/odrl/2/",
            "org": "http://www.w3.org/ns/org#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "prof": "http://www.w3.org/ns/dx/prof/",
            "prov": "http://www.w3.org/ns/prov#",
            "qb": "http://purl.org/linked-data/cube#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "schema": "http://schema.org/",
            "sh": "http://www.w3.org/ns/shacl#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "sosa": "http://www.w3.org/ns/sosa/",
            "ssn": "http://www.w3.org/ns/ssn/",
            "time": "http://www.w3.org/2006/time#",
            "vann": "http://purl.org/vocab/vann/",
            "void": "http://rdfs.org/ns/void#",
            "wgs": "https://www.w3.org/2003/01/geo/wgs84_pos#",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "@graph": [
            {
                "@id": "https://localhost:8443/dataset/2ac53087-e1b1-4301-9c85-6461f81cf595",
                "@type": "schema:Dataset",
                "schema:creator": {
                    "@id": "https://localhost:8443/organization/e37afbc0-4270-4e26-ac15-036590485814"
                },
                "schema:dateModified": "2025-01-17T19:20:38.929522",
                "schema:datePublished": "2025-01-17T19:20:10.193510",
                "schema:distribution": {
                    "@id": "https://localhost:8443/dataset/2ac53087-e1b1-4301-9c85-6461f81cf595/resource/883a935f-02bf-4d96-9a40-02e8566ddbed"
                },
                "schema:includedInDataCatalog": {
                    "@id": "_:N327f3587332f414ca7f4844b454cffe9"
                },
                "schema:license": "http://www.opendefinition.org/licenses/cc-by-sa",
                "schema:name": "Point test",
                "schema:publisher": {
                    "@id": "https://localhost:8443/organization/e37afbc0-4270-4e26-ac15-036590485814"
                },
                "schema:url": "https://localhost:8443/dataset/point-test"
            },
            {
                "@id": "_:N327f3587332f414ca7f4844b454cffe9",
                "@type": "schema:DataCatalog",
                "schema:description": "",
                "schema:name": "CKAN",
                "schema:url": "https://localhost:8443"
            },
            {
                "@id": "https://localhost:8443/organization/e37afbc0-4270-4e26-ac15-036590485814",
                "@type": "schema:Organization",
                "schema:contactPoint": [
                    {
                        "@id": "_:N8f3eab00d6a7479d889d86e1cdba9894"
                    },
                    {
                        "@id": "_:N55713fa9e8ff489aa8ea185298b1344e"
                    }
                ],
                "schema:name": "OIH"
            },
            {
                "@id": "_:N8f3eab00d6a7479d889d86e1cdba9894",
                "@type": "schema:ContactPoint",
                "schema:contactType": "customer service",
                "schema:url": "https://localhost:8443"
            },
            {
                "@id": "_:N55713fa9e8ff489aa8ea185298b1344e",
                "@type": "schema:ContactPoint",
                "schema:contactType": "customer service",
                "schema:url": "https://localhost:8443"
            },
            {
                "@id": "https://localhost:8443/dataset/2ac53087-e1b1-4301-9c85-6461f81cf595/resource/883a935f-02bf-4d96-9a40-02e8566ddbed",
                "@type": "schema:DataDownload",
                "schema:contentSize": 57,
                "schema:encodingFormat": "JSON",
                "schema:name": "point.json",
                "schema:url": "https://localhost:8443/dataset/2ac53087-e1b1-4301-9c85-6461f81cf595/resource/883a935f-02bf-4d96-9a40-02e8566ddbed/download/point.json"
            }
        ]
    }  
  ```
  
### Generate a sitemap for your CKAN instance

A sitemap is required to allow ODIS to locate and harvest your 
CKAN catalogue.  We will implement the [ckanext-sitemap](https://github.com/datopian/ckanext-sitemap) 
extension, as follows.

#### Edit the Dockerfile to install the ckanext-sitemap extension

- assuming you are still at the `odis@` prompt, but if not:
  - goto Start menu, choose "WSL"
  - CMD window should open with an `odis@` prompt
- execute `cd ckan-docker-git-master`
- now use `vi` to add in the required section for the ckanext-dcat plugin into
  the `Dockerfile` :
  ```
  #use vi to open the Dockerfile
  vi ckan/Dockerfile
  #to make your changes, first press your "i" key (for INSERT mode), and
    #then edit the desired lines
  #then save with the command
  :wq
  ```
- around line#6 (after the DCAT section) paste the following into the `Dockerfile`:
  ```
  ### SITEMAP ###
  RUN  pip3 install -e 'git+https://github.com/datopian/ckanext-sitemap.git@master#egg=ckanext-sitemap'  && \
       pip3 install -r https://raw.githubusercontent.com/datopian/ckanext-sitemap/refs/heads/master/requirements.txt
  ```
- save the file
  
#### Edit the .env file to load the Extension

Inside the `ckan-docker-git-master` directory, use `vi` to edit the `.env` file
to add the `dcat` and `structured_data` plugins, as follows:

- open the .env file:

  ```
  vi .env
  ```
- around line#69, change the `CKAN__PLUGINS` line to add the `sitemap` extension, such as:

  ```
  CKAN__PLUGINS="image_view text_view datatables_view datastore datapusher envvars dcat structured_data sitemap"
  ```
  
- save the file
  
#### Rebuild the containers

- build the Docker images
  ```
  docker compose -f docker-compose.yml build
  ```
  
- start the Docker containers
  ```
  docker compose up -d
  ```
  
#### Check the status

We can use the CKAN API to check if the new plugin was loaded successfully.

- using the [Firefox](https://www.mozilla.org/en-CA/firefox/new/) browser (which
  displays the JSON results nicely), goto: https://localhost:8443/api/action/status_show
  
- you should see a list of extensions that includes `sitemap`, such as:
  
  ![sitemap install1](tooling/images/sitemap-install1.png)
  
#### Connect to the CKAN container and Generate the sitemap

The sitemap extension requires us to run a command on the CKAN container to 
generate the sitemap, so we must connect to the container, as follows:

```{note}
As there could be a permissions issue when generating (and writing) the sitemap 
to the folder, we will connect as `root`.
```

- execute the following, to connect to the CKAN container (replace "ckan-docker-git-master-ckan-1" with your container name) :
  ```
  docker exec -u root -it ckan-docker-git-master-ckan-1 /bin/bash -c "export TERM=xterm; exec bash"
  ```
  
- in that default `/srv/app/` directory, we can run the command to generate the 
  sitemap:
  ```
  ckan ckanext-sitemap generate
  ```
  
  ![sitemap install2](tooling/images/sitemap-install2.png)

- the sitemap will be created in the following folder:
  ```
  /srv/app/src/ckanext-sitemap/ckanext/sitemap/public
  ```
  
- we need to modify the permissions of the folder where the sitemap was generated
  (especially for when it will be auto-generated later), by executing the
  following commands:
  ```
  chown -R ckan:ckan-sys /srv/app/src/ckanext-sitemap/ckanext/sitemap/public/
  chmod -R 775 /srv/app/src/ckanext-sitemap/ckanext/sitemap/public/
  ```    

#### View the sitemap

The sitemap will be visible in your browser now, at the root of your
instance, such as: https://localhost:8443/sitemap_index.xml

```{tip}
You can learn more about sitemaps in the [Publishing section](https://book.odis.org/publishing/publishing.html#sitemap-xml) 
of the ODIS Book.
```

- note that the extension has generated a sitemap index (usually a list of 
  individual sitemaps), so you can copy the `<loc>` url and open it in a new tab, 
  to view the actual sitemap, such as https://localhost:8443/sitemap-0.xml
  
- you should now see a list of `<loc>` values for your catalogue, including your
  test dataset record, such as:
  
  ![sitemap install3](tooling/images/sitemap-install3.png)
  
#### Configure the sitemap extension

There are several environment variables that can be set in the `ckan.ini` file,
such as how often the sitemap is auto-generated.  See the full list of possible
settings [here](https://github.com/datopian/ckanext-sitemap?tab=readme-ov-file#configuration).

At the minimum, you should likely set the variable `autorenew` to `true`, 
as follows:

- on the `CKAN` container, edit the `ckan.ini` file
  ```
  vi /srv/app/ckan.ini
  ```
  
- insert the following at the bottom of the file:
  ```
  ckanext.sitemap.autorenew = True
  ```
  
- now `exit` the CKAN container, and restart it, such as:
  ```
  docker restart ckan-docker-git-master-ckan-1
  ```
  
- now your sitemap will be regenerated, if the sitemap link is visited and
  the sitemap is older than 8 hours.
  
#### Create an entry in the ODIS Catalogue and point to sitemap

ODIS will use your entry in the [ODIS Catalogue](https://catalogue.odis.org/) 
("ODISCat") to find and harvest your sitemap.  Be sure to go through the quick 
steps in the [Getting Started with ODIS](https://book.odis.org/gettingStarted.html) 
section of the ODIS Book, to make sure that your ODISCat entry is created properly.

### Docker Troubleshooting

#### Check Logs

- you can check logs through the commandline, passing the name of the container,
  such as:
  ```
  docker logs ckan-docker-git-master-ckan-1
  ``` 
- alternatively you can use Portainer to check the logs of a container, just 
  click on the little file icon beside the container name, such as:
  
  ![logs](tooling/images/logs.png)
  
#### Restart container

- you can restart a container through the commandline, passing the name of the 
  container, such as:
  ```
  docker restart ckan-docker-git-master-ckan-1
  ``` 
- alternatively you can use Portainer to restart container, just 
  select the container on the left, and then click the `Restart` button above, 
  such as:
  
  ![restart](tooling/images/restart.png)
  
#### Remove all containers

Sometimes you might want to start over, so you can execute the following to 
delete all Docker containers and cache.

```{caution}
This will remove all existing containers, even those that are running.
```

- remove all containers:
  ```
  sudo docker rm -f $(sudo docker ps -a -q)
  ``` 
- remove cache:
  ```
  docker system prune -a
  ```
  
## Option 2: Install CKAN & dependencies manually

### Install PostgreSQL

PostgreSQL is a popular Open Source database, that will store tables leveraged by
CKAN.  It also has a very strong spatial engine, PostGIS.  We will now install both 
PostgreSQL and PostGIS, as follows:

- goto https://www.postgresql.org/download/windows/
- near the top, click on "Download the installer certified by EDB"
- click the latest for "Windows x86-64"
- double-click the installer file
- leave default install directory as-is (C:/Program Files/PostgreSQL/17/)

  ![PG install1](tooling/images/pg-install1.png)
  
- leave default components as-is

  ![PG install2](tooling/images/pg-install2.png)
  
- leave data directory as-is (C:/Program Files/PostgreSQL/17/data/)
- for superuser password, use "postgres"
  ![PG install3](tooling/images/pg-install3.png)
- leave port as-s (5432)

  ![PG install4](tooling/images/pg-install4.png)
  
- leave locale as-is
- install
- make sure "Stack Builder" is selected and then click "Finish"

  ![PG install5](tooling/images/pg-install5.png)
  
- in the "Stack Builder" window, select your installation in the dropdown 
  ("PostgreSQL 17 on port 5432") and then click "Next"
- expand "Spatial Extensions" and click the checkbox for "PostGIS x.x Bundle for PostgreSQL"

  ![PG install6](tooling/images/pg-install6.png)
  
- leave download directory as-is, click "Next"
- wait for the PostGIS installer to download
- click "Next" to begin PostGIS install
- click "I Agree" to the PostGIS license
- leave components as-is
- leave destination folder as-is
- click "Finish" to end the installation

  ![PG install8](tooling/images/pg-install8.png)

### Install Python

CKAN 2.11 (the latest release as of writing this document) supports Python versions 
3.9 to 3.12. This document will explain how to install Python 3.12, as follows:

```{note}
If you have an existing Python installation, you may attempt at using it, but
leveraging a Python virtual environment (venv) is recommended, which is explained
later in this document.
```

- create a new folder "Python" at the root of your C:/ drive, so you have a path of
  `C:/Python`
- download 3.12.7 "Windows installer (64-bit)" from https://www.python.org/downloads/windows/
- double-click the file "python-3.12.7-amd64.exe" to install
- choose "Customize installation" & check the checkbox for "add python.exe to PATH"

  ![Python install1](tooling/images/python-install1.png)
  
- leave "Optional Features" as-is
- for "Advanced Options", click on the "Browse" button, to select the install location,
  and choose the `C:/Python` folder
  
  ![Python install2](tooling/images/python-install2.png)
  
- click the "Install" button
- test with a CMD command
  - in the Windows search bar, type "CMD" and press <enter> on your keyboard
  - make sure you right-click on the icon and select "Run as Administrator"
  
    ![CMD as administrator](tooling/images/cmd-admin1.png)
    
  - at the command prompt, type: 
    ```bash
    python --version
    ```
    
    ![Python install3](tooling/images/python-install3.png)

### Install Git

We will use git to "checkout" (which means to get locally) the latest changes in 
software that is required for CKAN (as often the released code contains errors, that 
are fixed in the software's GitHub repository).  We will also be using git through 
the commandline.

```{tip}
After installing, will use the commandline for git, but you will also see a "Git GUI" 
option in the Start Menu, that you may prefer for a more visual experience.  There 
are also other visual tools that you can install instead, such as 
[GitHub Desktop](https://github.com/apps/desktop).
```
- goto https://git-scm.com/downloads/win and select "Click here to download" the 
  64-bit version of Git for Windows
- run the installer
- select "Checkout as-is, commit as-is"

  ![Git install1](tooling/images/git-windows1.png)
  
- select "Use Windows' default console window"

  ![Git install2](tooling/images/git-windows2.png)
  
- select "Fast-forward or merge" for 'git pull'

  ![Git install3](tooling/images/git-windows3.png)
  
- default credential manager (no changes)

  ![Git install4](tooling/images/git-windows4.png)
  
- select "Enable file system caching"
- test by opening a CMD window and executing: git --version

  ![Git install6](tooling/images/git-windows6.png)

### Create a working directory

Using Windows File Explorer, create a new folder named "working" at the 
`C:/` drive root, so you have the existing path `C:/working`

![File Explorer](tooling/images/working-folder.png)

### Create virtual environment in Python

We will use a `venv` virtual environment in Python, to make sure that 
the installation does not conflict with others on your server.  Open 
a CMD window, and execute the following to create a new `ckan-venv` environment:
```bash
cd C:\working
python -m venv ckan-venv
C:\working\ckan-venv\Scripts\activate
```
You should now see a prompt that looks like the following:

![venv](tooling/images/python-venv.png)

You can also execute `deactivate` to exit that `ckan-venv` virtual environment, 
and then execute `C:\working\ckan-venv\Scripts\activate` to reactivate.

### Upgrade pip

Open a CMD window, and make sure that your `ckan-venv` is activated, and then 
upgrade pip as follows:
```bash
python -m pip install --upgrade pip
```

### Checkout the CKAN source code and build CKAN

We will use git to get the latest source code direct from the CKAN
repository on GitHub, and then build CKAN inside the `ckan-venv` virtual 
environment.  Open a CMD window, and execute:
```bash
cd C:\working
C:\working\ckan-venv\Scripts\activate
git clone https://github.com/ckan/ckan.git ckan-git-master
cd ckan-git-master
python -m pip install --upgrade -r requirements.txt
python -m pip install python-magic-bin
python -m pip install -e .
```

![CKAN install1](tooling/images/ckan-install1.png)

You can now try to a test, to see the usage, such as:

![CKAN install2](tooling/images/ckan-install2.png)

### Add PostgreSQL utils to PATH

We will need to run various PostgreSQL tools from the commandline, so we need 
to make sure that they are found on the `PATH` environment variable on your
server.  To set the system PATH, execute the following:

- in the Windows search bar, searcg for "env" and choose "Edit the system environment variables"
- click on the bottom "Environment variables" button

  ![PG env1](tooling/images/pg-env1.png)
  
- select `Path` in the lower "System variables" section and click the "Edit..."
  button
  
  ![PG env2](tooling/images/pg-env2.png)
  
- click "New" and then "Browse" to C:/Program Files/PostgreSQL/xx/bin/"

  ![PG env3](tooling/images/pg-env3.png)
  
- click "OK"
- close your CMD window, and re-open it
- test by executing: `psql --version`

  ![PG env4](tooling/images/pg-env4.png)

### Create the ckan database

We will now create a user profile in `ckanuser` PostgreSQL.  Open a CMD window 
and execute:

```bash
createuser -U postgres -p 5432 -s -D -r -P ckanuser
```
then enter the following responses:
```bash
enter password for new role: odis
enter it again: odis
password: postgres
```

We will now create a new database `ckandb` in PostgreSQL.  In your CMD window
execute:

```bash
createdb -U postgres -p 5432 -O ckanuser ckandb -E utf-8
```
For the password enter `postgres`

### Install the PostGIS extension in ckandb

You likely will need spatial tables inside the `ckandb` database, so it 
is recommended to enable the PostGIS extension, by executing in your 
CMD window as follows:

```bash
psql -U ckanuser -p 5432 -d ckandb
```
For the password enter `odis`

You should now be at a prompt like `ckandb=>`

Then execute to list all tables: `\d <enter>`
You should see a response as `Did not find any relations`

Next execute:
```bash
CREATE EXTENSION postgis;  <enter>
CREATE EXTENSION postgis_topology;  <enter>
ALTER DATABASE ckandb SET client_min_messages TO WARNING;  <enter>
```
Again execute to list all tables (you should see more tables now) : `\d <enter>`

![PG table install](tooling/images/postgis-table-install.png)

to quit, execute: `\q <enter>`

### Generate config file for CKAN

We will run the built `ckan` tool to generate a config file for CKAN.  Open a 
CMD window and execute:

```bash
cd C:\working
C:\working\ckan-venv\Scripts\activate
mkdir ckan-site
cd ckan-site
ckan generate config ckan.ini
```

Now open in Notepad++: `C:\working\ckan-site\ckan.ini`
and set the following:

```
  line# 73:
    sqlalchemy.url = postgresql://ckanuser:odis@localhost/ckandb

  line# 78:
    ckan.site_url = http://localhost:5000

  line# 139:
    ckan.site_id = default
    
  line# 195
    extra_template_paths = C:\working\ckan-git-master\ckan\templates
    
  line# 202:
    ckan.storage_path = C:\working\ckan-site\data  
```
Using Windows File Explorer, then create a new `data` folder inside 
`C:\working\ckan-site`

### Install Java JRE

Several tools for CKAN require that we install Java, as follows:

- download "Open JDK 21.x" from https://learn.microsoft.com/en-ca/java/openjdk/download
```{tip}
   JDK 21 is recommended for latest Solr through GitHub
```
- use MSI installer for x64 platform
- run installer (use all defaults)
- test: open a new CMD window and execute: `java --version`

  ![OpenJDK install1](tooling/images/openjdk-install1.png) 
  
- check your system Environment Variables list to make sure JAVA_HOME is set
    - set it to: 
        `C:\Program Files\Microsoft\jdk-17.0.13.11-hotspot`
        
      ![OpenJDK install2](tooling/images/openjdk-install2.png)

### Install Strawberry Perl

- download: https://strawberryperl.com/
- use MSI installer
- leave defaults as-is
- test in new CMD window, executing: `perl --version`

### Install Solr

CKAN leverages Solr for its fast indexing/searches.  To install Solr
execute the following in a CMD window:

```bash
cd C:\working
C:\working\ckan-venv\Scripts\activate  
git clone https://github.com/apache/solr.git solr-git-main
cd solr-git-main
gradlew dev
cd C:\working\solr-git-main\solr\packaging\build\dev
```

![Solr install1](tooling/images/solr-install1.png)

- Test Solr by executing: `bin\solr.cmd --help`
    
- Now we must start Solr in "standalone mode"
```bash
  bin\solr.cmd start --user-managed -p 8983
```

![Solr install2](tooling/images/solr-install2.png)

  In your web browser goto: http://localhost:8983/solr
  
![Solr install3](tooling/images/solr-install3.png)

- Now check Solr status with `bin\solr.cmd status`

```
        Solr process 2360 running on port 8983
        {
          "solr_home":"C:\\working\\solr-git-main\\solr\\packaging\\build\\dev\\server\\solr",
          "version":"10.0.0-SNAPSHOT bc0c226c8fe9c475e5e723355f729fd39ceaf30f [snapshot build, details omitted]",
          "startTime":"Sat Nov 09 16:01:17 AST 2024",
          "uptime":"0 days, 0 hours, 13 minutes, 19 seconds",
          "memory":"115.4 MB (%22.5) of 512 MB"}
```
- now create a new `ckan` Solr core
```
bin\solr.cmd create -c ckan
```
which should return: `Created new core 'ckan'`
     
- now stop Solr
```
bin\solr.cmd stop -p 8983
```
- copy schema.xml from `C:\working\ckan-git-master\ckan\config\solr`
  to `C:\working\solr-git-main\solr\packaging\build\dev\server\solr\ckan\conf`               
- delete the file `managed-schema.xml` in `C:\working\solr-git-main\solr\packaging\build\dev\server\solr\ckan\conf`

- now start Solr
```
bin\solr.cmd start --user-managed -p 8983
```
- in your web browser, check the `ckan` core
  - http://localhost:8983/solr/#/ckan/core-overview
  
![Solr install4](tooling/images/solr-install4.png)

- you can also check the status of the core at the commandline, by executing:

  ```
  curl -X GET http://localhost:8983/api/cores/ckan
  ```
- which should give a response such as:
  
  ```json
        {
          "responseHeader":{
            "status":0,
            "QTime":4
          },
          "initFailures":{ },
          "status":{
            "ckan":{
              "name":"ckan",
              "instanceDir":"C:\\working\\solr-git-main\\solr\\packaging\\build\\dev\\server\\solr\\ckan",
              "dataDir":"C:\\working\\solr-git-main\\solr\\packaging\\build\\dev\\server\\solr\\ckan\\data\\",
              "config":"solrconfig.xml",
              "schema":"managed-schema.xml",
              "startTime":"2024-11-09T20:33:09.309Z",
              "uptime":253492,
              "index":{
                "numDocs":0,
                "maxDoc":0,
                "deletedDocs":0,
                "version":2,
                "segmentCount":0,
                "current":true,
                "hasDeletions":false,
                "directory":"org.apache.lucene.store.NRTCachingDirectory:NRTCachingDirectory(MMapDirectory@C:\\working\\solr-git-main\\solr\\packaging\\build\\dev\\server\\solr\\ckan\\data\\index lockFactory=org.apache.lucene.store.NativeFSLockFactory@17a1916f; maxCacheMB=48.0 maxMergeSizeMB=4.0)",
                "segmentsFile":"segments_1",
                "segmentsFileSizeInBytes":69,
                "userData":{ },
                "sizeInBytes":69,
                "size":"69 bytes"
              }
            }
          }
        }
  ```

### Install Redis

To install Redis (required for CKAN), we must install the WSL (Windows Subsystem for Linux),
as follows:
  - follow https://learn.microsoft.com/en-us/windows/wsl/install
  - open CMD window and execute:
    - see list of all Linux distribution names
      ```
      wsl --list --online
      ```
    - now install Ubuntu
      ```
      wsl --install --enable-wsl2 --distribution "Ubuntu-24.04 LTS"
      ```
      
      ![redis install1](tooling/images/redis-install1.png)
      
  - reboot machine
  - you should see a progress bar for installing Ubuntu
  - when asked to create a new user, enter:
    ```
    username: odis
    password: yourpassword
    ```
    ```{caution}
    The WSL user has a lot of power (they have sudo/super-user permissions); 
    it is strongly recommended that users change `yourpassword` to a secure 
    and unique password for this account and keep hold of it in a password 
    manager. That way if someone manages to hack CKAN and gain remote code 
    execution capabilities, it won't be so easy for them to gain super-user 
    control.
    ```
  - to run: goto Start menu, choose "WSL"
    - CMD window should open with an `odis@` prompt
  - to check the Ubuntu version, execute:
    ```
    lsb_release -a
    ```
    which should return:
    ```
        Distributor ID: Ubuntu
        Description:    Ubuntu 24.04 LTS
        Release:        24.04
        Codename:       noble
    ```
    
    ![redis install2](tooling/images/redis-install2.png) 
    
   - install the redis package
     - (follow steps at https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/install-redis-on-windows/
       ```
       curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
       echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
       sudo apt-get update
       sudo apt-get upgrade
       sudo apt-get install redis
       ```
     - if error "Failed to take /etc/passwd lock: Invalid argument", execute:
       ```
       sudo mv /var/lib/dpkg/info /var/lib/dpkg/info_silent
       sudo mkdir /var/lib/dpkg/info
       sudo apt-get update
       sudo apt-get -f install
       sudo mv /var/lib/dpkg/info/* /var/lib/dpkg/info_silent
       sudo rm -rf /var/lib/dpkg/info
       sudo mv /var/lib/dpkg/info_silent /var/lib/dpkg/info
       sudo apt-get update
       sudo apt-get upgrade
       sudo apt-get install redis
       ```
     - start the redis server
       ```
       sudo service redis-server start
       ```
     - test it by running: 
       ```
       redis-cli
       ```
       - which should bring you to a prompt of `127.0.0.1:6379>`, so then type
         `ping <enter>`
         - the response should be `PONG` if successful
           ```
             127.0.0.1:6379>
             127.0.0.1:6379>ping
             PONG
           ```
           
           ![redis install3](tooling/images/redis-install3.png)     
  
### Create the CKAN database tables

- open new CMD window, and execute:
```
C:\working\ckan-venv\Scripts\activate
cd C:\working\ckan-site
ckan -c ckan.ini db init
```
- you should see a green message: "Upgrading DB: SUCCESS"

  ![CKAN install tables1](tooling/images/ckan-install-tables1.png)
  
- test with psql command:
  ```
  psql -U ckanuser -p 5432 -d ckandb -c "\d"
  ```
  for password enter `odis`
  
- you should see 32 rows of tables

  ![CKAN install tables2](tooling/images/ckan-install-tables2.png)

### Add CKAN user

We will create an initial user `admin` for CKAN, with full
`sysadmin` powers, to manage the catalogue.  Open a CMD window and 
execute:

```  
cd C:/working/ckan-site
C:\working\ckan-venv\Scripts\activate
ckan -c ckan.ini user add admin email=info@gatewaygeomatics.com
```
for password enter `odisckan`

![CKAN home](tooling/images/ckan-create-user.png)

- then promote the "admin" user to sysadmin
  ```
  ckan -c C:/working/ckan-site/ckan.ini sysadmin add admin
  ```
- you should see a message of "Added admin as sysadmin"

### Run CKAN

We can use the internal "development server" to serve CKAN, as follows:

```
C:\working\ckan-venv\Scripts\activate
ckan -c C:/working/ckan-site/ckan.ini run
```
- should see:
  ```
    2024-11-10 12:11:15,815 INFO  [ckan.cli.server] Running CKAN on http://localhost:5000
    2024-11-10 12:11:18,107 INFO  [ckan.cli] Using configuration file C:\working\ckan-site\ckan.ini
  ```
- in your browser, goto: http://localhost:5000/

![CKAN home](tooling/images/ckan-initial-home.png)
<!-- End: tooling/ckan.md -->


---


# Part: Validation



---

<!-- Begin: validation/index.md -->

# Validation

## About

This section contains some initial work on developing some validation
approaches for OIH.  The focus initially is not on validating approaches with
the full publishing guidance.  Rather the focuses is on the the "info hub" as a
search application and develops validation to support that.

### Well Formed JSON-LD 

[SDO Validator](https://validator.schema.org/)

[Structured data Linter](http://linter.structured-data.org/)

[JSON-LD Playground](https://json-ld.org/playground/)


### Shape Validation

Initial approach:

* Develop a base SHACL document that assess a data graph based on elements needed to support search
* [SHACL](https://www.w3.org/TR/shacl/)
* Leverage [SHACL Playground](https://shacl.org/playground/)
* RDFShape at [https://rdfshape.weso.es/](https://rdfshape.weso.es/) and [https://rdfshape.herokuapp.com/](https://rdfshape.herokuapp.com/) 
  
To support this will need an initial data graph to work with.  The type is not
important.  All types will need to satisfy the search needs.

Examples of these needs include:

* Have an @id
* Have a name
* Have a description
* Have a Distribution and contentURL
* Reference authority
<!-- End: validation/index.md -->


---


# Part: Interfaces



---

<!-- Begin: users/index.md -->

# Users

## About

The reference client is available at
 [search.oceaninfohub.org](https://search.oceaninfohub.org).  
 

 ![](users/images/oceans.png)


## Using OIH search in Chrome

It is possible to set Ocean InfoHub as a search shortcut in Chrome.
To do this go to the _Manage Search ..._ section of your settings. 

There you will see a button "Add" in the _Site Search_ section.  

 ![](users/images/managesearch.png)

You can make an entry like: __https://search.oceaninfohub.org/results/?search_text=%s&page=0__

The shortcut, here _oih_ can be used in the address bar to quickly invoke this search.

Simple type: _oih_ or whatever you set the shortcut to and then hit the tab key.  The address bar will convert to a search mode where you can type your search and hit return.  

 ![](users/images/saveOIH.png)
<!-- End: users/index.md -->


---

<!-- Begin: users/query.ipynb -->

# SPARQL

## Introduction

This notebook will go over some concepts for querying the graph that is generated by the Ocean InfoHub.

The product of the publishing and indexing process is a graph.  This graph follows the W3C Resource Description
Framework (RDF).   RDF is a data model that can be represented in various text encodings.  Among these
is the JSON-LD format we have been using in the publishing process.  

Not all graph libraries and databases support JSON-LD yet, so as part of the aggregation process one step 
is to simply translate this format into a format that is supported by the graph database.   Typically we 
use something n-triples or turtle for this.  There are many tools for translating RDF from one format to another. 

We can load the graphs into a graph database and this was documented in the Aggregation section, so we will not
revisit it here.    In this notebook, we will load the graph into a local graph database in the Python library
that also supports the same query language our graph databases use.  This will make the demonstration easier and 
allow you to download and run this notebook on your own machine if you wish.  The query language we will use 
is SPARQL.  

## SPARQL

SPARQL (SPARQL Protocol and RDF Query Language) is the query language that is used to query RDF graphs.  It 
is a W3C recommendation documented at [SPARQL 1.1 Query Language](https://www.w3.org/TR/sparql11-query/).  

## Load a Graph

For this demonstration we will be using Python to load the graph and do our queries.  However, there are many 
languages and libraries for working with graphs and SPARQL.   Also, you can often query a graph using web UIs 
infront of your graph database or even with simple direct HTTP requests.  Examples of some of these can be
found in other sections of the OIH documentation.  

```python
import rdflib

g = rdflib.Graph()
g.parse("../tooling/notebooks/data/oceanexperts_graph.ttl", format="ttl")
```

```text
<Graph identifier=N9656cde6c1054a4ba02f9bbcd09d17a8 (<class 'rdflib.graph.Graph'>)>
```

# Let's define our first query

This is a simple query that will return all the triples in the graph.   Recall an RDF graph is make of triples defined by a subject, predicate and object.  You can review RDF at the W3C RDF Primer (https://www.w3.org/TR/rdf11-concepts/).  SPARQL allows us to do a type of pattern matching on the graph by defining a pattern we a relooking for.  

Here we define ```?s ?p ?o``` as the pattern we are looking for.  The ```?``` is a variable that can be used to match any value.  In this case, we are looking for all the triples in the graph.  We have used s, p and o to as simple names for our subject, predicate, object elements of the RDF triple.  

Since this would match ALL the values in the graph, which would be a lot, we have added a LIMIT option to reduce the number of resutls returned.

You could also try these queries at: [https://oceans.collaborium.io/sparql.html](https://oceans.collaborium.io/sparql.html)

```python
s1 = """
    SELECT ?s ?p ?o
    WHERE {
        ?s ?p ?o .
    }
    LIMIT 3
"""
```

# Run the query

We will run this query, and print out the results

```python
from icecream import ic

for row in g.query(s1):
    ic(row.asdict())
```

```text
ic| row.asdict(): {'o': rdflib.term.Literal('2014-06-02'),
                   'p': rdflib.term.URIRef('https://schema.org/startDate'),
                   's': rdflib.term.BNode('n0dfe00a0174f48a7b9fb702b5f5b4ecdb236')}
ic| row.asdict(): {'o': rdflib.term.Literal(' Copenhagen Denmark '),
                   'p': rdflib.term.URIRef('https://schema.org/address'),
                   's': rdflib.term.BNode('n0dfe00a0174f48a7b9fb702b5f5b4ecdb496')}
ic| row.asdict(): {'o': rdflib.term.Literal('Introduction to Ocean Data Management for Students of the Environment Group II'),
                   'p': rdflib.term.URIRef('https://schema.org/name'),
                   's': rdflib.term.BNode('n0dfe00a0174f48a7b9fb702b5f5b4ecdb1745')}
```

# Nicer formatting

We can do a bit of formatting to see our results in a nicer way.  

```python
for row in g.query(s1):
    s = row["s"].n3()
    p = row["p"].n3()
    o = row["o"].n3()

    ic(s, p, o)
```

```text
ic| s: '_:n0dfe00a0174f48a7b9fb702b5f5b4ecdb236'
    p: '<https://schema.org/startDate>'
    o: '"2014-06-02"'
ic| s: '_:n0dfe00a0174f48a7b9fb702b5f5b4ecdb496'
    p: '<https://schema.org/address>'
    o: '" Copenhagen Denmark "'
ic| s: '_:n0dfe00a0174f48a7b9fb702b5f5b4ecdb1745'
    p: '<https://schema.org/name>'
    o: ('"Introduction to Ocean Data Management for Students of the Environment Group '
        'II"')
```

# KGLab

As mentioned, this intro is based on the nice work done by KGLab (https://derwen.ai/docs/kgl/) both in their library and documentation.  We wll import kglab here and take advantage of some of their nice features.  In particular some nice functioons to load our graph and query it with results into a Dataframe. 

```python
import kglab

namespaces = {
    "schema":  "https://schema.org/",
    }

kg = kglab.KnowledgeGraph(
    name = "Demonstration Graph",
    base_uri = "https://oceaninfohub.org/id/",
    namespaces = namespaces,
    )

kg.load_rdf("../tooling/notebooks/data/oceanexperts_graph.ttl")
```

```text
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/__init__.py:177: UserWarning: Code: dateTimeStamp is not defined in namespace XSD
  from . import DatatypeHandling, Closure
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: dateTimeStamp is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: length is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: maxExclusive is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: maxInclusive is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: maxLength is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: minExclusive is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: minInclusive is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: minLength is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/RDFSClosure.py:40: UserWarning: Code: pattern is not defined in namespace XSD
  from owlrl.AxiomaticTriples import RDFS_Axiomatic_Triples, RDFS_D_Axiomatic_Triples
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/OWLRL.py:53: UserWarning: Code: dateTimeStamp is not defined in namespace XSD
  from .XsdDatatypes import OWL_RL_Datatypes, OWL_Datatype_Subsumptions
/home/fils/.conda/envs/kglab/lib/python3.8/site-packages/owlrl/OWLRLExtras.py:64: UserWarning: Code: dateTimeStamp is not defined in namespace XSD
  from .RestrictedDatatype import extract_faceted_datatypes

<kglab.kglab.KnowledgeGraph at 0x7f470860bf40>
```

# PREFIX

Let's do another query.  We will use the PREFIX keyword to define a prefix for the namespace.  This is a way to leverage namespace in our query.  Note the use of schema:name vs the <https://schema.org/location>.  The latter is a URI and the former is a prefix.  The prefix is defined in the PREFIX keyword.   The schema:name is the name of the property that we are querying, the prefix can expand it to a URI.  The <https://schema.org/location> is the URI of the property directly, without use of a prefix.   Both work, the prefix can simply make life easier for you and also help avoid hard to find typos where you may miss-type a URI.  

Let's do a query to see all the location names in our group for training.  

```python
s2 = """
PREFIX schema: <https://schema.org/>
SELECT DISTINCT ?locname
  WHERE {
      ?s rdf:type <https://schema.org/Course> .
      ?s  <https://schema.org/location> ?location .
      ?location schema:name ?locname .
  }
  """
```

```python
import pandas as pd
pd.set_option("max_rows", None)

df = kg.query_as_df(s2)
df.head(5)
```

```text
                                      locname
0                                  Lima Peru 
1                              Qingdao China 
2                                     Russia 
3   Playa del Secreto Puerto Morelos, Mexico 
4         University of Ghent  Ghent Belgium 
```

# Location Counts

The above is nice, but it doesn't tell us much about the number of events in each location. We can modify our query to do this.  We can leverage the COUNT and GROUP BY capacity of SPARQL to do this.  We can then add in ORDER BY to sort the results.

```python
s3 = """
SELECT DISTINCT ?locname (COUNT(?locname) AS ?count)
  WHERE {
      ?s rdf:type <https://schema.org/Course> .
      ?s  <https://schema.org/location> ?location .
      ?location <https://schema.org/name> ?locname .
  }
  GROUP BY ?locname
  ORDER BY DESC(?count)
  """
```

```python
import pandas as pd
pd.set_option("max_rows", None)

df = kg.query_as_df(s3)
df.head(5)
```

```text
                                             locname  count
0   UNESCO/IOC Project Office for IODE Wandelaark...     28
1                                            Russia      27
2   UNESCO/IOC Project Office for IODE Wandelaark...     22
3             Wandelaarkaai 7 8400 Oostende Belgium      13
4                                           Belgium      10
```

# FILTER

Graphs are great for showing relations between objects but our approaches to searching or selecting data can often leverage pattern matching on text strings.  We do have some tools in SPARQL for this in the form of FILTER.  We can use regex pattern in the FILTER to match text.  Let's use this to find all the locations with "Peru" in the name.

In the following we will do a simple FILTER with a regular expression, but you can also do things like:

``` 
SELECT DISTINCT ?s 
  WHERE {
      ?s rdf:type <https://schema.org/Course> .
      FILTER NOT EXISTS { ?s  <https://schema.org/hasCourseInstance> ?instance . }  
  }
```

which in a SPARQL query would require that a hasCourseInstance property is not defined for the Course.  That is, Courses that have had no instances made yet.  

```python
s4 = """
SELECT DISTINCT ?locname (COUNT(?locname) AS ?count)
  WHERE {
      ?s rdf:type <https://schema.org/Course> .
      ?s  <https://schema.org/location> ?location .
      ?location <https://schema.org/name> ?locname .
      FILTER regex(?locname, ".Peru.", "i") .
  }
  GROUP BY ?locname
  """
```

```python
import pandas as pd
pd.set_option("max_rows", None)

df4 = kg.query_as_df(s4)
df4.head(5)
```

```text
                                             locname  count
0                                         Lima Peru       1
1   Dirección Hidrografía y Navegación de la Arma...      1
2                     Hotel Palmetto Lima Perú Peru       1
```

# PERU

So we see we have three entries in our graph that have Peru in the name.  This is where connecting our group to a shared concept of what Peru is like the WikiData entry for Peru at https://www.wikidata.org/wiki/Q419 would help.  That's a topic for another day.   

# Dates

Let's look at the dates that are available in the graph. 

```python
s5 = """
SELECT DISTINCT ?sdate (COUNT(?sdate) AS ?count)
  WHERE {
      ?s rdf:type <https://schema.org/Course> .
      ?s  <https://schema.org/hasCourseInstance> ?instance .
      ?instance  <https://schema.org/startDate> ?sdate .
  }
  GROUP BY ?sdate
  """
```

```python
import pandas as pd
pd.set_option("max_rows", None)

df4 = kg.query_as_df(s5)
df4.head(5) # show some results
```

```text
        sdate  count
0  2020-06-08      1
1  2011-05-03      1
2  2012-07-16      1
3  2007-07-12      1
4  2019-04-02      1
```

# A bit of Pandas

Here we will mix in a bit of Pandas to convert our dates to Pandas dates, group and plot.  This is not 
SPARQL but rather just some post processing in Pandas.  It does still give us an idea of some of the
information we can extract from our graph.

Also, when the graph is composed of multiple source we can still conduct the same search across 
a shared concept like https://schema.org/Course with CourseInstance connected to a date via startDate.  

This shared approach by Ocean InfoHub is developed to support the shared data and integration 
goals among the participants. 

```python
df4['count'] = df4["count"].astype(int) # convert count c to int
df4pd = df4.to_pandas()  # convert cudf dataframe to pandas dataframe
df4pd['sdate'] = pd.to_datetime(df4pd['sdate'], format='%Y-%m-%d')  # convert date to datetime
courseByYear = df4pd.groupby(pd.Grouper(key='sdate', freq='Y')).size() # group by year
ax = courseByYear.plot.bar(rot=80, stacked=True, figsize=(15, 5)) # plot
```

```text
<Figure size 1080x360 with 1 Axes>
```

# More on Query

Here we have gone through an introdcution to the SPARQL query language and how to use it to query our graph.  
We can look at the SPARQL we use on the larger Ocean Infohub graph.  

# References

This is a just a quick overview of the SPARQL language.  You can find a large amount of information online.


* https://derwen.ai/docs/kgl/ex4_0/ 
* https://www.stardog.com/tutorials/getting-started-1/ 
* https://www.dataversity.net/introduction-to-sparql/ 
* https://www.slideshare.net/olafhartig/an-introduction-to-sparql 
<!-- End: users/query.ipynb -->


---

<!-- Begin: users/sparql.md -->

---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
execution:
  allow_errors: true
---


# OIH SPARQL

## About

This page will hold some information about the SPARQL queries we use and 
how they connect with some of the profile guidance in this document.    We will
show how this relates to and depends on the Gleaner prov as well as the 
Authoritative Reference elements of the patterns.  It is expected that the Gleaner 
prov will be present, though this can be made optional in case other 
indexing systems are used that do not provide this prov shape.    The SPARQL will 
be looking for both Gleaner prov and the Authroitative Reference elements. 

This will be different for different patterns.  For example, it might 
relate to the publisher provider elements for Creativeworks, but to 
the identity element for People and Organizations. 


```{literalinclude} ./graphs/basic.rq
:linenos:
:emphasize-lines: 12-14, 18-21, 23-28, 30-32
```

## Lines 12-14

It should be noted that the above SPARQL is not standards compliant.  It leverages some 
vender specific syntax that is not part of the SPARQL standard.  This is not uncommon 
as groups will often add their own syntax to offer additional functionality.

A common one is what is seen here where a full text index is leveraged to allow for more complex
and faster searches than can be done with FILTER regex.  These three lines will
only work in the current OIH triplestore (Blazegraph).   Other triplestores like Jena
and other do similar built in function extensions.  

## Lines 18-21

These line demonstrate the use of the OPTIONAL keyword.  These triples are not required
to be present in a resource.  If they are, they will be returned.  

## Lines 23-28

These lines are standard SPARQL but are searching across triples not from the provider 
graphs.  Rather, they are looking at triples generated by the OIH indexing program
used, Gleaner.   

Note, that Gleaner is not a dependency of this project and other 
indexing approaches and software could be used.  As pointed out in the documentation, 
this approach is based on structured data on the web and web architecture approaches.
So, any indexing system following those approaches can be used.

These triples are used to track the indexing event and the sources indexed.  It provides
some additional provenance to the information collected, but does not change or even 
extend what the providers are publishing.  

As such, these statements could be removed and all that would be lost of indexing
activity information.  

## Lines 30-32

These lines represent three specific SPARQL parameters.  

First is the ORDER BY directive.  This is used to order the results by one of the 
returned variables.  In this case we are using the ?score variable which comes from
the vendor specific syntax noted in lines 11-13.  This score is the ranking score
for a resource search against the full text index.  However, this could be any 
variable coming from standards compliant SPARQL calls too.   Sorting can be done 
on alphanumeric values in ascending (ASC) or descending (DESC) order. 

The  LIMIT is used to limit the number of results returned.  We follow this with, 
OFFSET which is used to skip the first n results.  These two are useful for pagination when 
combined with the ORDER BY directive.
<!-- End: users/sparql.md -->


---

<!-- Begin: users/apis.md -->

# APIs

## About

The Ocean InfoHub graph is accessible through several approaches.  
The graph is implemented in RDF and expressed through a standards compliant triplestore.

This triplestore exposes a SPARQL endpoint that can be queried using the [SPARQL 1.1 Query Language](http://www.w3.org/TR/rdf-sparql-query/).
To do this you can visit a web based query interface as discussed in other sections of this document.

It is also possible to access this service following RESTful principles.  

## SPARQL HTTP Protocol

One approach to this RESTful approach is to use the
[SPARQL 1.1 Graph Store HTTP Protocol](https://www.w3.org/TR/2013/REC-sparql11-http-rdf-update-20130321/).
This is a simple HTTP protocol that allows you to query the graph using SPARQL and obtain the results in JSON.

The OIH triplestore exposes the graph following this pattern for queries.

### Examples

```bash
curl -X POST https://graph.collaborium.io/blazegraph/namespace/aquadocs/sparql --data-urlencode 'query=SELECT * { ?s ?p ?o } LIMIT 1' -H 'Accept:application/sparql-results+json'
```

If run this from the command line we will get something like the following.  

```bash
✗ curl -X POST https://graph.collaborium.io/blazegraph/namespace/aquadocs/sparql --data-urlencode 'query=SELECT * { ?s ?p ?o } LIMIT 1' -H 'Accept:application/sparql-results+json'

{
  "head" : {
    "vars" : [ "s", "p", "o" ]
  },
  "results" : {
    "bindings" : [ {
      "s" : {
        "type" : "uri",
        "value" : "https://hdl.handle.net/1834/10030"
      },
      "p" : {
        "type" : "uri",
        "value" : "https://schema.org/propertyID"
      },
      "o" : {
        "type" : "literal",
        "value" : "https://hdl.handle.net/"
      }
    } ]
  }
}                                   
```

While this is unlikely how you will want to interact with the graph, 
it desmonstrates the HTTP based access API that can be used in tools, notebooks
or other applications.

This is the same basic approach the used in the web client.  There the 
axios library (https://axios-http.com/) is used with a code snippet like:

```javascript

 axios.get(url.toString())
      .then(function (response) {
        // handle success
        console.log(response);
        const el = document.querySelector('#container2');
        render(showresults(response), el);
      })
      .catch(function (error) {
        // handle error
        console.log(error);
      })
      .then(function () {
        // always executed
      });

```
<!-- End: users/apis.md -->


---


# Part: Appendix



---

<!-- Begin: appendix/index.md -->

# Appendix

## About

A collection of items related to the OIH development.  Mostly related
to examples around representing concepts in the graph such as
date and time, language etc.

As these develop they may be moved into other sections of the book.
<!-- End: appendix/index.md -->


---

<!-- Begin: appendix/annoyances.md -->

# Known Issues

## About

This document will collect some of the various issues we have encounter in publishing
the JSON-LD documents.  

### control characters in URL string for sitemap or in the JSON-LD documents

Make sure there are no control characters such as new line, carriage returns, 
tabs or others in the document.  These can be problematic both for processing and
display.  

### context is a map (changed from 1.0)

Be sure to use a context style like:

```
    "@context": {
        "@vocab": "https://schema.org/"
    },
```

The context section must be a map starting in JSON-LD 1.1

### data graphs need @id

Be sure to include an @id in your graph that points to the identifier or the 
web address of the resource providing the metadata.  This is not the material the
metadata is about, but rather the metadata record itself.

### string literals must be valid

The string literals must be sure to not have quotation marks or other invalid
characters without escaping or encoding them.  
<!-- End: appendix/annoyances.md -->


---

<!-- Begin: appendix/references.md -->

# References

A broad collection of references.  

## General

  [Science on Schema](https://github.com/ESIPFed/science-on-schema.org//)

  [BioSchemas](https://bioschemas.org/liveDeploys)

  [Ocean Best Practices on Schema](https://github.com/adamml/ocean-best-practices-on-schema)

  [PID policy for European Open Science Cloud](https://op.europa.eu/en/publication-detail/-/publication/35c5ca10-1417-11eb-b57e-01aa75ed71a1/language-en)

  [DCAT Schema.org mappings](https://www.w3.org/2015/spatial/wiki/ISO_19115_-_DCAT_-_Schema.org_mapping)

  [DCAT US Data.gov reference](https://resources.data.gov/resources/dcat-us/)

  [FAIR Semantics](https://zenodo.org/record/3707985#.X7Jq2-RKjrV)


## Developer References

[Schema.org releases](https://schema.org/docs/releases.html)

[Schema.org RDF graph (turtle format)](https://github.com/schemaorg/schemaorg/blob/main/data/schema.ttl )

[JSON-LD Playground](https://json-ld.org/playground/)

[Google Developers Search Gruid](https://developers.google.com/search/docs/guides/search-gallery)

[Google Developers Fact Check](https://developers.google.com/search/docs/data-types/factcheck )

[Structured Data Testing Tool](https://search.google.com/structured-data/testing-tool)

[Rich Results Testing Tool](https://search.google.com/test/rich-results )

[JSON-LD](https://github.com/digitalbazaar/jsonld.js/ )

[Ruby JSON-LD](https://github.com/ruby-rdf/json-ld )

[schema.org Java](https://github.com/google/schemaorg-java )

[Perl classes for schema.org markup](https://metacpan.org/source/RRWO/SemanticWeb-Schema-v8.0.0/README.md )

## Content Management and Web Server support

[Drupal Support](https://www.drupal.org/project/schema_metatag  )

[Wordpress Claim Review](https://wordpress.org/plugins/claim-review-schema/ )

## Organizations

[Google Open Source](https://opensource.google/ )

[DataCommons](https://datacommons.org/ )  & [DataCommons REST](https://docs.datacommons.org/api/rest/query.html )


## Indexers

[Gleaner](https://gleaner.io/)
[BMUSE](https://github.com/HW-SWeL/BMUSE)  

## Graph tools

[Wikipedia SPARQL implementation list](https://en.wikipedia.org/wiki/List_of_SPARQL_implementations)

[RDFlib](https://rdflib.readthedocs.io/en/stable/ )


[Any23](https://any23.apache.org/ )

[rdfjs](https://github.com/rdfjs )

[shemaram](https://github.com/google/schemarama )

[validatingrdf](https://book.validatingrdf.com/ )

[Structured Data Linter](http://linter.structured-data.org/)

## Blogs and Press Releases

[Yandex: What is Scheme.org](https://yandex.com/support/webmaster/schema-org/what-is-schema-org.html )

[Bing: Fact Check Label](https://blogs.bing.com/Webmaster-Blog/September-2017/Bing-adds-Fact-Check-label-in-SERP-to-support-the-ClaimReview-markup )

[Bing: Contextual Awareness](https://docs.microsoft.com/en-us/previous-versions/bing/contextual-awareness/dn632191(v=msdn.10) )

[Facebook: Marketing API](https://developers.facebook.com/docs/marketing-api/catalog/guides/)

[Facebook: fact checking](https://about.fb.com/news/2018/06/increasing-our-efforts-to-fight-false-news/)

[Amazon: Alex skills](https://developer.amazon.com/en-US/docs/alexa/custom-skills/built-in-intent-library.html )

[Google Developers mail invoice](https://developers.google.com/gmail/markup/reference/invoice )

## Not Categorized Yet


[Lighthouse Plugins](https://github.com/GoogleChrome/lighthouse/blob/master/docs/plugins.md)

[Lighthouse](https://github.com/GoogleChrome/lighthouse)

[Science on Schema](https://github.com/ESIPFed/science-on-schema.org//)

[BioSchemas](https://bioschemas.org/)

[CodeMeta](https://codemeta.github.io/)

[Linter Structured Data](http://linter.structured-data.org/)

[JSON-LD Playground](https://json-ld.org/playground/)

[JSON-LD.org](https://json-ld.org)

[SHACL playground](https://shacl.org/playground/)

[Google Structured Data testing tool](https://search.google.com/structured-data/testing-tool) (

[Google Dataset for  developers](https://developers.google.com/search/docs/data-types/dataset)

[Press  article](https://www.schemaapp.com/toolssay-goodbye-to-googles-structured-data-testing-tool-and-hello-to-the-alternatives/)

[Rich results](https://search.google.com/test/rich-results)

[SchemaApp.com](https://www.schemaapp.com/solutions/)

[Yandex](https://webmaster.yandex.com/tools/microtest/)

[Schema dev](https://test.schema.dev/)

[Chromeextension](https://chrome.google.com/webstore/detail/ryte-structured-data-help/ndodccbbcdpcmabmiocobdnfiaaimgnk?hl=en)

[Google Rich Results](https://search.google.com/test/rich-results)

[Datashapes](https://datashapes.org/)

[ACL Web Alexa Meaning Representation Language](https://www.aclweb.org/anthology/N18-3022.pdf )

[hash.aio Volcano schema](https://hash.ai/schemas/Volcano )

[Yoast Structured Data Guide](https://yoast.com/structured-data-schema-ultimate-guide/)

[Schema App](https://www.schemaapp.com/ )

[Springer: Scigraph](https://researchdata.springernature.com/posts/45943-sn-scigraph-latest-release-patents-clinical-trials-and-many-new-features )

[iPhylo Biodiversity KG](https://iphylo.blogspot.com/2018/08/ozymandias-biodiversity-knowledge-graph.html)

[ozymandias](https://ozymandias-demo.herokuapp.com/ )


 [RDA group meeting notes](https://docs.google.com/document/d/18CyQ2WsOxG_0zzzteubJyPveZzr8KPH4iuvoKVxRo3o/edit)

  [RDA Plenary meeting](https://www.rd-alliance.org/moving-toward-fair-semantics-2)
<!-- End: appendix/references.md -->


---

<!-- Begin: appendix/registries.md -->

# Registries

## Documents and Datasets

[DOI](https://www.doi.org/)
> A not-for-profit membership organization that is the governance and management body for the federation of Registration Agencies providing Digital Object Identifier (DOI) services and registration, and is the registration authority for the ISO standard (ISO 26324) for the DOI system. The DOI system provides a technical and social infrastructure for the registration and use of persistent interoperable identifiers, called DOIs, for use on digital networks.

[Datacite](https://datacite.org/)
> Locate, identify, and cite research data with the leading global provider of DOIs for research data.

Archival Resource Key or ARK: [](https://en.wikipedia.org/wiki/Archival_Resource_Key) and 
[N2T ARKs](https://n2t.net/e/ark_ids.html) and [Names to Thinkgs](https://n2t.net/)

## People

[Orcid](https://orcid.org/)  

> ORCID’s mission is to enable transparent and trustworthy connections between researchers, their contributions, and their affiliations by providing a unique, persistent identifier for individuals to use as they engage in research, scholarship, and innovation activities.

## Organizations
[re3data](https://www.re3data.org/) 
> A registry of research data repositories 

[ROR](https://ror.org/)
> ROR is a community-led project to develop an open, sustainable, usable, and unique identifier for every research organization in the world.

[Grid](https://grid.ac/)
> GRID is a free and openly available global database of research-related organisations, cataloging research-related organisations and providing each with a unique and persistent identifier. With GRID you have over 99,609 carefully curated records at hand, enabling you to identify and distinguish research-related institutions worldwide.

## Physical Samples

[IGSN](https://www.igsn.org/) 

> The objective of the IGSN e.V. is to implement and promote standard methods for identifying, citing, and locating physical samples with confidence by operating an international IGSN registration service.
<!-- End: appendix/registries.md -->


---

<!-- Begin: appendix/vocabularies.md -->

# Controlled Vocabularies

## About

See also:  [ODIS-ARCH Vocabularies](https://github.com/iodepo/odis-arch/blob/master/docs/vocabularies.md)

A list of possible controlled vocabularies to use in the schema.org documents.
Many such resources can be found by searching at [BARTOC.org](https://bartoc.org/)
or the [UNESCO Thesaurus](http://vocabularies.unesco.org/browser/thesaurus/en/).

Note, at present this is an exploration and there is not yet a recommendation
for use in OIH.  

## List

[Essential Climate Variables](https://public.wmo.int/en/programmes/global-climate-observing-system/essential-climate-variables)

[Vocabulary based on DFG'S Classification of Subject Area, Review Board, Research Area and Scientific Discipline (2016 - 2019)](https://figshare.com/articles/dataset/Vocabulary_of_Scientific_Disciplines/3406594/2)

[Nature Subjects Ontology](http://registry.it.csiro.au/def/keyword/nature/subjects)
<!-- End: appendix/vocabularies.md -->

